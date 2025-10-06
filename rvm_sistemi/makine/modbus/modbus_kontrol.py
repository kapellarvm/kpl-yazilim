#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GA500 Modbus Motor Kontrol Fonksiyonları
Ezici ve Kırıcı motor kontrolü için tüm fonksiyonlar
"""

import time
import threading
import logging
from .modbus_istemci import GA500ModbusClient

class MotorKontrol:
    """GA500 Motor Kontrol Sınıfı - Hibrit Sistem (Modbus okuma + Dijital sürme)"""
    
    def __init__(self, modbus_client=None, sensor_kart=None, logger=None):
        """
        Motor kontrol sınıfını başlat
        Args:
            modbus_client: GA500ModbusClient instance (durum okuma için)
            sensor_kart: SensorKart instance (motor sürme için)
            logger: Logger instance
        """
        self.client = modbus_client  # Modbus okuma için
        self.sensor_kart = sensor_kart  # Dijital motor sürme için
        
        if logger is None:
            logging.basicConfig(level=logging.INFO)
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        
        # Zamanlı çalıştırma için thread'ler ve timer'lar
        self.ezici_timer = None
        self.kirici_timer = None
        self.ezici_lock = threading.Lock()
        self.kirici_lock = threading.Lock()
        
        # Motor ID'leri
        self.EZICI_ID = 1
        self.KIRICI_ID = 2
        
        # Sıkışma koruması parametreleri - Motor tipine göre farklı limitler
        self.EZICI_SIKISMA_AKIM_LIMITI = 5.0   # Amper - Ezici için sıkışma tespit eşiği
        self.KIRICI_SIKISMA_AKIM_LIMITI = 7.0  # Amper - Kırıcı için sıkışma tespit eşiği
        self.SIKISMA_SURE_LIMITI = 2.0         # Saniye - bu süre boyunca yüksek akım
        self.KURTARMA_DENEY_SAYISI = 3         # Kaç defa kurtarma denemesi
        self.KURTARMA_GERI_SURE = 5.0          # Saniye - geri çalıştırma süresi
        self.KURTARMA_ILERI_SURE = 5.0         # Saniye - ileri çalıştırma süresi
        
        # Sıkışma izleme thread'leri
        self.ezici_sikisma_thread = None
        self.kirici_sikisma_thread = None
        self.sikisma_monitoring_active = False
        
        # Sıkışma durumu tracking
        self.ezici_sikisma_durumu = {
            'aktif': False,
            'basla_zamani': None,
            'son_akim': 0.0,
            'kurtarma_denemesi': 0,
            'kurtarma_asamasi': None  # None, 'geri', 'ileri'
        }
        
        self.kirici_sikisma_durumu = {
            'aktif': False,
            'basla_zamani': None,
            'son_akim': 0.0,
            'kurtarma_denemesi': 0,
            'kurtarma_asamasi': None  # None, 'geri', 'ileri'
        }
    
    def set_client(self, client):
        """Modbus client'i ayarla"""
        self.client = client
    
    def set_sensor_kart(self, sensor_kart):
        """Sensör kartını ayarla"""
        self.sensor_kart = sensor_kart
    
    def _check_client(self):
        """Client kontrolü (durum okuma için)"""
        if self.client is None:
            self.logger.warning("⚠️ Modbus client tanımlı değil - sadece dijital kontrol!")
            return False
        if not self.client.is_connected:
            self.logger.warning("⚠️ Modbus bağlantısı yok - sadece dijital kontrol!")
            return False
        return True
    
    def _check_sensor_kart(self):
        """Sensör kartı kontrolü (motor sürme için)"""
        if self.sensor_kart is None:
            self.logger.error("❌ Sensör kartı tanımlı değil!")
            return False
        if not self.sensor_kart.getir_saglik_durumu():
            self.logger.error("❌ Sensör kartı sağlıksız!")
            return False
        return True
    
    # ===========================================
    # SIKIŞMA KORUMA SİSTEMİ
    # ===========================================
    
    def start_sikisma_monitoring(self):
        """Sıkışma izleme sistemini başlat"""
        if self.sikisma_monitoring_active:
            self.logger.warning("⚠️ Sıkışma izleme zaten aktif")
            return
        
        if not self._check_client():
            self.logger.error("❌ Modbus client yok - sıkışma izleme başlatılamıyor")
            return
        
        self.sikisma_monitoring_active = True
        
        # Her iki motor için izleme thread'i başlat
        self.ezici_sikisma_thread = threading.Thread(
            target=self._sikisma_izleme_worker, 
            args=(self.EZICI_ID, "Ezici"),
            daemon=True
        )
        self.kirici_sikisma_thread = threading.Thread(
            target=self._sikisma_izleme_worker, 
            args=(self.KIRICI_ID, "Kırıcı"),
            daemon=True
        )
        
        self.ezici_sikisma_thread.start()
        self.kirici_sikisma_thread.start()
        
        self.logger.info("🛡️ Sıkışma koruması başlatıldı")
    
    def stop_sikisma_monitoring(self):
        """Sıkışma izleme sistemini durdur"""
        self.sikisma_monitoring_active = False
        
        if self.ezici_sikisma_thread and self.ezici_sikisma_thread.is_alive():
            self.ezici_sikisma_thread.join(timeout=2)
        
        if self.kirici_sikisma_thread and self.kirici_sikisma_thread.is_alive():
            self.kirici_sikisma_thread.join(timeout=2)
        
        self.logger.info("🛡️ Sıkışma koruması durduruldu")
    
    def _sikisma_izleme_worker(self, motor_id, motor_adi):
        """Sıkışma izleme worker thread'i"""
        sikisma_durumu = self.ezici_sikisma_durumu if motor_id == self.EZICI_ID else self.kirici_sikisma_durumu
        
        # Motor tipine göre akım limitini belirle
        akim_limiti = self.EZICI_SIKISMA_AKIM_LIMITI if motor_id == self.EZICI_ID else self.KIRICI_SIKISMA_AKIM_LIMITI
        
        while self.sikisma_monitoring_active:
            try:
                # Motor durumunu oku
                status = self.client.status_data.get(motor_id, {})
                if not status:
                    time.sleep(0.5)
                    continue
                
                # Akım değerini al
                current_data = status.get('output_current', {})
                current_value = current_data.get('value', 0.0)
                sikisma_durumu['son_akim'] = current_value
                
                # Motor çalışıyor mu kontrol et
                drive_status = status.get('drive_status', {}).get('raw', 0)
                is_running = (drive_status & 0x0001) != 0
                
                if is_running and current_value > akim_limiti:
                    # Yüksek akım tespit edildi
                    if not sikisma_durumu['aktif']:
                        # İlk defa yüksek akım
                        sikisma_durumu['aktif'] = True
                        sikisma_durumu['basla_zamani'] = time.time()
                        self.logger.warning(f"⚠️ {motor_adi}: Yüksek akım tespit edildi ({current_value:.1f}A > {akim_limiti}A)")
                    else:
                        # Yüksek akım devam ediyor
                        gecen_sure = time.time() - sikisma_durumu['basla_zamani']
                        if gecen_sure >= self.SIKISMA_SURE_LIMITI:
                            # Sıkışma confirmed!
                            self.logger.error(f"🚨 {motor_adi}: SIKIŞMA TESPİT EDİLDİ! ({current_value:.1f}A > {akim_limiti}A, {gecen_sure:.1f}s)")
                            self._sikisma_kurtarma_baslat(motor_id, motor_adi)
                            # Reset durumu
                            sikisma_durumu['aktif'] = False
                            sikisma_durumu['basla_zamani'] = None
                else:
                    # Normal akım
                    if sikisma_durumu['aktif']:
                        self.logger.info(f"✅ {motor_adi}: Akım normale döndü ({current_value:.1f}A < {akim_limiti}A)")
                        sikisma_durumu['aktif'] = False
                        sikisma_durumu['basla_zamani'] = None
                
                time.sleep(0.2)  # 200ms check interval
                
            except Exception as e:
                self.logger.error(f"❌ {motor_adi} sıkışma izleme hatası: {e}")
                time.sleep(1)
    
    def _sikisma_kurtarma_baslat(self, motor_id, motor_adi):
        """Sıkışma kurtarma senaryosunu başlat"""
        sikisma_durumu = self.ezici_sikisma_durumu if motor_id == self.EZICI_ID else self.kirici_sikisma_durumu
        
        if sikisma_durumu['kurtarma_denemesi'] >= self.KURTARMA_DENEY_SAYISI:
            self.logger.error(f"❌ {motor_adi}: SIKIŞMA GİDERİLEMEDİ - TEKNİK MÜDAHALE GEREKLİ!")
            self._motor_dur(motor_id, motor_adi)
            return False
        
        sikisma_durumu['kurtarma_denemesi'] += 1
        self.logger.info(f"🔧 {motor_adi}: Sıkışma kurtarma denemesi #{sikisma_durumu['kurtarma_denemesi']}")
        
        # Kurtarma thread'i başlat
        kurtarma_thread = threading.Thread(
            target=self._sikisma_kurtarma_worker,
            args=(motor_id, motor_adi),
            daemon=True
        )
        kurtarma_thread.start()
        
        return True
    
    def _sikisma_kurtarma_worker(self, motor_id, motor_adi):
        """Sıkışma kurtarma senaryosu worker"""
        sikisma_durumu = self.ezici_sikisma_durumu if motor_id == self.EZICI_ID else self.kirici_sikisma_durumu
        
        try:
            self.logger.info(f"🔧 {motor_adi}: Kurtarma senaryosu başlıyor...")
            
            # 1. Motoru durdur
            self._motor_dur(motor_id, motor_adi)
            time.sleep(1)
            
            # 2. Geri çalıştır
            sikisma_durumu['kurtarma_asamasi'] = 'geri'
            self.logger.info(f"◀️ {motor_adi}: {self.KURTARMA_GERI_SURE}s geri çalıştırma")
            self._motor_geri(motor_id, motor_adi)
            time.sleep(self.KURTARMA_GERI_SURE)
            
            # 3. Durdur
            self._motor_dur(motor_id, motor_adi)
            time.sleep(1)
            
            # 4. İleri çalıştır
            sikisma_durumu['kurtarma_asamasi'] = 'ileri'
            self.logger.info(f"▶️ {motor_adi}: {self.KURTARMA_ILERI_SURE}s ileri çalıştırma")
            self._motor_ileri(motor_id, motor_adi)
            time.sleep(self.KURTARMA_ILERI_SURE)
            
            # 5. Durdur
            self._motor_dur(motor_id, motor_adi)
            time.sleep(1)
            
            # 6. Tekrar geri
            self.logger.info(f"◀️ {motor_adi}: {self.KURTARMA_GERI_SURE}s ikinci geri çalıştırma")
            self._motor_geri(motor_id, motor_adi)
            time.sleep(self.KURTARMA_GERI_SURE)
            
            # 7. Durdur
            self._motor_dur(motor_id, motor_adi)
            time.sleep(1)
            
            # 8. Son ileri deneme
            self.logger.info(f"▶️ {motor_adi}: {self.KURTARMA_ILERI_SURE}s ikinci ileri çalıştırma")
            self._motor_ileri(motor_id, motor_adi)
            time.sleep(self.KURTARMA_ILERI_SURE)
            
            # 9. Final dur
            self._motor_dur(motor_id, motor_adi)
            
            sikisma_durumu['kurtarma_asamasi'] = None
            self.logger.info(f"✅ {motor_adi}: Kurtarma senaryosu tamamlandı")
            
        except Exception as e:
            self.logger.error(f"❌ {motor_adi} kurtarma senaryosu hatası: {e}")
            self._motor_dur(motor_id, motor_adi)
            sikisma_durumu['kurtarma_asamasi'] = None
    
    def _motor_dur(self, motor_id, motor_adi):
        """Motor durdur - iç fonksiyon"""
        if motor_id == self.EZICI_ID:
            self.ezici_dur()
        else:
            self.kirici_dur()
    
    def _motor_ileri(self, motor_id, motor_adi):
        """Motor ileri - iç fonksiyon"""
        if motor_id == self.EZICI_ID:
            self.ezici_ileri()
        else:
            self.kirici_ileri()
    
    def _motor_geri(self, motor_id, motor_adi):
        """Motor geri - iç fonksiyon"""
        if motor_id == self.EZICI_ID:
            self.ezici_geri()
        else:
            self.kirici_geri()
    
    def get_sikisma_durumu(self):
        """Sıkışma durumlarını raporla"""
        return {
            'ezici': {
                'id': self.EZICI_ID,
                'akim_limiti': self.EZICI_SIKISMA_AKIM_LIMITI,
                'sikisma_aktif': self.ezici_sikisma_durumu['aktif'],
                'son_akim': self.ezici_sikisma_durumu['son_akim'],
                'kurtarma_denemesi': self.ezici_sikisma_durumu['kurtarma_denemesi'],
                'kurtarma_asamasi': self.ezici_sikisma_durumu['kurtarma_asamasi']
            },
            'kirici': {
                'id': self.KIRICI_ID,
                'akim_limiti': self.KIRICI_SIKISMA_AKIM_LIMITI,
                'sikisma_aktif': self.kirici_sikisma_durumu['aktif'],
                'son_akim': self.kirici_sikisma_durumu['son_akim'],
                'kurtarma_denemesi': self.kirici_sikisma_durumu['kurtarma_denemesi'],
                'kurtarma_asamasi': self.kirici_sikisma_durumu['kurtarma_asamasi']
            },
            'monitoring_aktif': self.sikisma_monitoring_active
        }

    # ===========================================
    # EZİCİ MOTOR KONTROL FONKSİYONLARI
    # ===========================================
    
    def ezici_reset(self):
        """Ezici motoru resetle - Modbus üzerinden"""
        if not self._check_client():
            return False
        
        self.logger.info("🔄 Ezici Reset (Modbus)")
        return self.client.clear_fault(self.EZICI_ID)
    
    def ezici_ileri(self):
        """Ezici motoru ileri çalıştır - Dijital kontrol"""
        if not self._check_sensor_kart():
            return False
        
        self.logger.info("▶️ Ezici İleri (Dijital)")
        try:
            self.sensor_kart.ezici_ileri()
            return True
        except Exception as e:
            self.logger.error(f"❌ Ezici ileri hatası: {e}")
            return False
    
    def ezici_geri(self):
        """Ezici motoru geri çalıştır - Dijital kontrol"""
        if not self._check_sensor_kart():
            return False
        
        self.logger.info("◀️ Ezici Geri (Dijital)")
        try:
            self.sensor_kart.ezici_geri()
            return True
        except Exception as e:
            self.logger.error(f"❌ Ezici geri hatası: {e}")
            return False
    
    def ezici_dur(self):
        """Ezici motoru durdur - Dijital kontrol"""
        if not self._check_sensor_kart():
            return False
        
        self.logger.info("⏹️ Ezici Dur (Dijital)")
        
        # Zamanlı çalıştırma varsa iptal et
        with self.ezici_lock:
            if self.ezici_timer:
                self.ezici_timer.cancel()
                self.ezici_timer = None
        
        try:
            self.sensor_kart.ezici_dur()
            return True
        except Exception as e:
            self.logger.error(f"❌ Ezici dur hatası: {e}")
            return False
    
    def ezici_ileri_10sn(self):
        """Ezici motoru 10 saniye ileri çalıştır (yenilenebilir)"""
        if not self._check_client():
            return False
        
        with self.ezici_lock:
            # Önceki timer'ı iptal et
            if self.ezici_timer:
                self.ezici_timer.cancel()
                self.logger.info("⏱️ Ezici İleri timer yenilendi")
            
            # Motoru başlat
            if self.ezici_ileri():
                # 10 saniye sonra durdur
                self.ezici_timer = threading.Timer(10.0, self._ezici_otomatik_dur)
                self.ezici_timer.start()
                self.logger.info("⏱️ Ezici İleri 10 saniye timer başlatıldı")
                return True
            else:
                return False
    
    def ezici_geri_10sn(self):
        """Ezici motoru 10 saniye geri çalıştır (yenilenebilir)"""
        if not self._check_client():
            return False
        
        with self.ezici_lock:
            # Önceki timer'ı iptal et
            if self.ezici_timer:
                self.ezici_timer.cancel()
                self.logger.info("⏱️ Ezici Geri timer yenilendi")
            
            # Motoru başlat
            if self.ezici_geri():
                # 10 saniye sonra durdur
                self.ezici_timer = threading.Timer(10.0, self._ezici_otomatik_dur)
                self.ezici_timer.start()
                self.logger.info("⏱️ Ezici Geri 10 saniye timer başlatıldı")
                return True
            else:
                return False
    
    def _ezici_otomatik_dur(self):
        """Ezici için otomatik durdurma (internal) - Dijital kontrol"""
        self.logger.info("⏰ Ezici 10 saniye timer doldu - otomatik durdurma (Dijital)")
        if self.sensor_kart:
            self.sensor_kart.ezici_dur()
        with self.ezici_lock:
            self.ezici_timer = None
    
    # ===========================================
    # KIRICI MOTOR KONTROL FONKSİYONLARI
    # ===========================================
    
    def kirici_reset(self):
        """Kırıcı motoru resetle - Modbus üzerinden"""
        if not self._check_client():
            return False
        
        self.logger.info("🔄 Kırıcı Reset (Modbus)")
        return self.client.clear_fault(self.KIRICI_ID)
    
    def kirici_ileri(self):
        """Kırıcı motoru ileri çalıştır - Dijital kontrol"""
        if not self._check_sensor_kart():
            return False
        
        self.logger.info("▶️ Kırıcı İleri (Dijital)")
        try:
            self.sensor_kart.kirici_ileri()
            return True
        except Exception as e:
            self.logger.error(f"❌ Kırıcı ileri hatası: {e}")
            return False
    
    def kirici_geri(self):
        """Kırıcı motoru geri çalıştır - Dijital kontrol"""
        if not self._check_sensor_kart():
            return False
        
        self.logger.info("◀️ Kırıcı Geri (Dijital)")
        try:
            self.sensor_kart.kirici_geri()
            return True
        except Exception as e:
            self.logger.error(f"❌ Kırıcı geri hatası: {e}")
            return False
    
    def kirici_dur(self):
        """Kırıcı motoru durdur - Dijital kontrol"""
        if not self._check_sensor_kart():
            return False
        
        self.logger.info("⏹️ Kırıcı Dur (Dijital)")
        
        # Zamanlı çalıştırma varsa iptal et
        with self.kirici_lock:
            if self.kirici_timer:
                self.kirici_timer.cancel()
                self.kirici_timer = None
        
        try:
            self.sensor_kart.kirici_dur()
            return True
        except Exception as e:
            self.logger.error(f"❌ Kırıcı dur hatası: {e}")
            return False
    
    def kirici_ileri_10sn(self):
        """Kırıcı motoru 10 saniye ileri çalıştır (yenilenebilir)"""
        if not self._check_client():
            return False
        
        with self.kirici_lock:
            # Önceki timer'ı iptal et
            if self.kirici_timer:
                self.kirici_timer.cancel()
                self.logger.info("⏱️ Kırıcı İleri timer yenilendi")
            
            # Motoru başlat
            if self.kirici_ileri():
                # 10 saniye sonra durdur
                self.kirici_timer = threading.Timer(10.0, self._kirici_otomatik_dur)
                self.kirici_timer.start()
                self.logger.info("⏱️ Kırıcı İleri 10 saniye timer başlatıldı")
                return True
            else:
                return False
    
    def kirici_geri_10sn(self):
        """Kırıcı motoru 10 saniye geri çalıştır (yenilenebilir)"""
        if not self._check_client():
            return False
        
        with self.kirici_lock:
            # Önceki timer'ı iptal et
            if self.kirici_timer:
                self.kirici_timer.cancel()
                self.logger.info("⏱️ Kırıcı Geri timer yenilendi")
            
            # Motoru başlat
            if self.kirici_geri():
                # 10 saniye sonra durdur
                self.kirici_timer = threading.Timer(10.0, self._kirici_otomatik_dur)
                self.kirici_timer.start()
                self.logger.info("⏱️ Kırıcı Geri 10 saniye timer başlatıldı")
                return True
            else:
                return False
    
    def _kirici_otomatik_dur(self):
        """Kırıcı için otomatik durdurma (internal) - Dijital kontrol"""
        self.logger.info("⏰ Kırıcı 10 saniye timer doldu - otomatik durdurma (Dijital)")
        if self.sensor_kart:
            self.sensor_kart.kirici_dur()
        with self.kirici_lock:
            self.kirici_timer = None
    
    # ===========================================
    # GENEL KONTROL FONKSİYONLARI
    # ===========================================
    
    def tum_motorlar_dur(self):
        """Tüm motorları durdur - Dijital kontrol"""
        self.logger.info("🛑 Tüm Motorlar Dur (Dijital)")
        
        # Timer'ları iptal et
        with self.ezici_lock:
            if self.ezici_timer:
                self.ezici_timer.cancel()
                self.ezici_timer = None
        
        with self.kirici_lock:
            if self.kirici_timer:
                self.kirici_timer.cancel()
                self.kirici_timer = None
        
        # Motorları durdur - Dijital kontrol
        ezici_result = False
        kirici_result = False
        
        if self._check_sensor_kart():
            try:
                self.sensor_kart.ezici_dur()
                ezici_result = True
            except Exception as e:
                self.logger.error(f"❌ Ezici dur hatası: {e}")
            
            try:
                self.sensor_kart.kirici_dur()
                kirici_result = True
            except Exception as e:
                self.logger.error(f"❌ Kırıcı dur hatası: {e}")
        
        return ezici_result and kirici_result
    
    def tum_motorlar_reset(self):
        """Tüm motorları resetle - Modbus üzerinden"""
        self.logger.info("🔄 Tüm Motorlar Reset (Modbus)")
        
        ezici_result = False
        kirici_result = False
        
        if self._check_client():
            ezici_result = self.client.clear_fault(self.EZICI_ID)
            kirici_result = self.client.clear_fault(self.KIRICI_ID)
        
        return ezici_result and kirici_result
    
    def durum_raporu(self):
        """Motor durumlarını raporla"""
        if not self._check_client():
            return None
        
        ezici_status = self.client.status_data.get(self.EZICI_ID, {})
        kirici_status = self.client.status_data.get(self.KIRICI_ID, {})
        
        rapor = {
            'ezici': {
                'id': self.EZICI_ID,
                'timer_aktif': self.ezici_timer is not None,
                'status': ezici_status
            },
            'kirici': {
                'id': self.KIRICI_ID,
                'timer_aktif': self.kirici_timer is not None,
                'status': kirici_status
            }
        }
        
        return rapor
    
    def cleanup(self):
        """Temizlik işlemleri"""
        self.logger.info("🧹 Motor kontrol temizlik")
        
        # Sıkışma monitoring'i durdur
        self.stop_sikisma_monitoring()
        
        # Tüm timer'ları iptal et
        with self.ezici_lock:
            if self.ezici_timer:
                self.ezici_timer.cancel()
                self.ezici_timer = None
        
        with self.kirici_lock:
            if self.kirici_timer:
                self.kirici_timer.cancel()
                self.kirici_timer = None
        
        # Motorları durdur
        self.tum_motorlar_dur()


# ===========================================
# GLOBAL FONKSİYONLAR (Eski test kodu uyumluluğu için)
# ===========================================

# Global motor kontrol instance
_motor_kontrol = None

def init_motor_kontrol(modbus_client, sensor_kart=None, logger=None):
    """Motor kontrol sistemini başlat - Hibrit sistem"""
    global _motor_kontrol
    _motor_kontrol = MotorKontrol(modbus_client, sensor_kart, logger)
    return _motor_kontrol

def get_motor_kontrol():
    """Motor kontrol instance'ını al"""
    return _motor_kontrol

# Ezici fonksiyonları
def ezici_reset():
    return _motor_kontrol.ezici_reset() if _motor_kontrol else False

def ezici_ileri():
    return _motor_kontrol.ezici_ileri() if _motor_kontrol else False

def ezici_geri():
    return _motor_kontrol.ezici_geri() if _motor_kontrol else False

def ezici_dur():
    return _motor_kontrol.ezici_dur() if _motor_kontrol else False

def ezici_ileri_10sn():
    return _motor_kontrol.ezici_ileri_10sn() if _motor_kontrol else False

def ezici_geri_10sn():
    return _motor_kontrol.ezici_geri_10sn() if _motor_kontrol else False

# Kırıcı fonksiyonları
def kirici_reset():
    return _motor_kontrol.kirici_reset() if _motor_kontrol else False

def kirici_ileri():
    return _motor_kontrol.kirici_ileri() if _motor_kontrol else False

def kirici_geri():
    return _motor_kontrol.kirici_geri() if _motor_kontrol else False

def kirici_dur():
    return _motor_kontrol.kirici_dur() if _motor_kontrol else False

def kirici_ileri_10sn():
    return _motor_kontrol.kirici_ileri_10sn() if _motor_kontrol else False

def kirici_geri_10sn():
    return _motor_kontrol.kirici_geri_10sn() if _motor_kontrol else False

# Genel fonksiyonlar
def tum_motorlar_dur():
    return _motor_kontrol.tum_motorlar_dur() if _motor_kontrol else False

def tum_motorlar_reset():
    return _motor_kontrol.tum_motorlar_reset() if _motor_kontrol else False

# Sıkışma koruması fonksiyonları
def start_sikisma_monitoring():
    return _motor_kontrol.start_sikisma_monitoring() if _motor_kontrol else False

def stop_sikisma_monitoring():
    return _motor_kontrol.stop_sikisma_monitoring() if _motor_kontrol else False

def get_sikisma_durumu():
    return _motor_kontrol.get_sikisma_durumu() if _motor_kontrol else None