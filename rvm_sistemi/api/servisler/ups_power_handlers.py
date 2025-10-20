#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UPS Güç Kesintisi İşleyicileri
Güç kesintisi ve geri gelme durumlarında yapılacak işlemler
"""

import asyncio
import time
from ...utils.logger import log_system, log_error, log_warning, log_oturum
from ...utils.terminal import section, ok, warn, err, wait, step, status
from ...makine.senaryolar import oturum_var
from ...api.servisler.dimdb_servis import DimdbServis


async def handle_power_failure():
    """UPS güç kesintisi durumunda yapılacak işlemler"""
    section("⚡ ELEKTRİK KESİNTİSİ TESPİT EDİLDİ!", "UPS çalışıyor - Acil işlemler başlatılıyor")
    log_error("⚡ UPS GÜÇ KESİNTİSİ - Acil işlemler başlatılıyor")
    
    try:
        # 1. Uyarı göster
        try:
            from ...makine.senaryolar.uyari import uyari_goster
            uyari_goster(mesaj="Makinenin Elektiriği Kesildi !", sure=20)
            warn("ELEKTRİK KESİNTİSİ", "Uyarı gösterildi")
        except Exception as e:
            err("ELEKTRİK KESİNTİSİ", f"Uyarı gösterilemedi: {e}")
            log_error(f"UPS kesintisi: Uyarı gösterilemedi: {e}")
        
        # 2. Motorları iptal et - Doğru referans kullan
        try:
            from ...makine import kart_referanslari
            motor = kart_referanslari.motor_al()
            if motor:
                status("ELEKTRİK KESİNTİSİ", "Motorlar iptal ediliyor...", level="stop")
                motor.motorlari_iptal_et()
                ok("ELEKTRİK KESİNTİSİ", "Motorlar iptal edildi")
                log_system("UPS kesintisi: Motorlar iptal edildi")
            else:
                warn("ELEKTRİK KESİNTİSİ", "Motor kartı bulunamadı")
                log_warning("UPS kesintisi: Motor kartı bulunamadı")
        except Exception as e:
            err("ELEKTRİK KESİNTİSİ", f"Motor iptal etme hatası: {e}")
            log_error(f"UPS kesintisi: Motor iptal etme hatası: {e}")
        
        # 3. Aktif oturum var mı kontrol et
        if oturum_var.sistem.aktif_oturum["aktif"]:
            session_id = oturum_var.sistem.aktif_oturum["sessionId"]
            step("OTURUM", f"Aktif oturum sonlandırılıyor: {session_id}")
            log_oturum("UPS kesintisi: Aktif oturum sonlandırılıyor")
            
            # 4. SessionEnd isteği gönder
            try:
                step("DİM-DB", "sessionEnd isteği gönderiliyor")
                import requests
                session_end_data = {"sessionId": session_id}
                response = requests.post("http://localhost:4321/dimdb/sessionEnd", json=session_end_data, timeout=5)
                if response.status_code == 200:
                    ok("DİM-DB", "SessionEnd isteği başarıyla gönderildi")
                    log_oturum("UPS kesintisi: SessionEnd isteği gönderildi")
                else:
                    warn("DİM-DB", f"SessionEnd isteği başarısız: {response.status_code}")
                    log_warning(f"UPS kesintisi: SessionEnd isteği başarısız: {response.status_code}")
            except Exception as e:
                err("DİM-DB", f"SessionEnd isteği hatası: {e}")
                log_error(f"UPS kesintisi: SessionEnd isteği hatası: {e}")
            
            # 5. Transaction result gönder
            try:
                step("DİM-DB", "Transaction result gönderiliyor")
                await DimdbServis.send_transaction_result()
                ok("DİM-DB", "Transaction result başarıyla gönderildi")
                log_oturum("UPS kesintisi: Transaction result gönderildi")
            except Exception as e:
                err("DİM-DB", f"Transaction result gönderme hatası: {e}")
                log_error(f"UPS kesintisi: Transaction result gönderme hatası: {e}")
            
            # 6. Oturumu sonlandır
            oturum_var.sistem.aktif_oturum["aktif"] = False
            oturum_var.sistem.aktif_oturum["sessionId"] = ""
            oturum_var.sistem.aktif_oturum["userId"] = ""
            ok("OTURUM", "Oturum sonlandırıldı")
            log_oturum("UPS kesintisi: Oturum sonlandırıldı")
        else:
            status("OTURUM", "Aktif oturum yok", level="info")
        
        # 6. Konveyörde ürün var mı kontrol et ve geri döndür
        if hasattr(oturum_var.sistem, 'motor_ref') and oturum_var.sistem.motor_ref:
            try:
                # Konveyörde ürün var mı kontrol et (kabul edilen ürünler listesi)
                urun_var_mi = (len(oturum_var.sistem.kabul_edilen_urunler) > 0 or 
                              len(oturum_var.sistem.veri_senkronizasyon_listesi) > 0 or
                              oturum_var.sistem.giris_sensor_durum)
                
                if urun_var_mi:
                    step("KONVEYÖR", "Konveyörde ürün tespit edildi - geri döndürülüyor")
                    oturum_var.sistem.motor_ref.konveyor_geri()
                    ok("KONVEYÖR", "Konveyör geri döndürüldü")
                    log_system("UPS kesintisi: Konveyör geri döndürüldü (ürün vardı)")
                else:
                    status("KONVEYÖR", "Konveyörde ürün yok - geri döndürme atlandı", level="info")
                    log_system("UPS kesintisi: Konveyörde ürün yok - geri döndürme atlandı")
            except Exception as e:
                err("KONVEYÖR", f"Konveyör kontrol hatası: {e}")
                log_error(f"UPS kesintisi: Konveyör kontrol hatası: {e}")
        
        # 7. Sistem durumunu güncelle
        oturum_var.sistem.ups_kesintisi = True
        oturum_var.sistem.ups_kesinti_zamani = time.time()
        
        # 8. GSI mesajı gelene kadar bekleme durumuna geç
        oturum_var.sistem.gsi_bekleme_durumu = True
        wait("ELEKTRİK KESİNTİSİ", "GSI mesajı bekleniyor...")
        status("ELEKTRİK KESİNTİSİ", "Sistem UPS modunda - GSI gelene kadar bekliyor", level="info")
        log_system("UPS kesintisi: GSI mesajı bekleniyor")
        
        ok("ELEKTRİK KESİNTİSİ", "Tüm işlemler tamamlandı")
        log_system("✅ UPS güç kesintisi işlemleri tamamlandı")
        
    except Exception as e:
        err("ELEKTRİK KESİNTİSİ", f"İşlem hatası: {e}")
        log_error(f"UPS güç kesintisi işleme hatası: {e}")


async def handle_power_restored():
    """UPS güç geri geldiğinde yapılacak işlemler"""
    section("🔌 ELEKTRİK GERİ GELDİ!", "UPS normal çalışmaya döndü - Sistem normalleştiriliyor")
    log_system("🔌 UPS GÜÇ GERİ GELDİ - Sistem normalleştiriliyor")
    
    try:
        # 1. UPS kesintisi durumunu temizle
        oturum_var.sistem.ups_kesintisi = False
        oturum_var.sistem.ups_kesinti_zamani = None
        ok("ELEKTRİK GERİ", "UPS kesintisi durumu temizlendi")
        
        # 2. GSI bekleme durumunu temizle
        oturum_var.sistem.gsi_bekleme_durumu = False
        ok("ELEKTRİK GERİ", "GSI bekleme durumu temizlendi")
        
        # 3. Konveyörü durdur (GSI mesajı gelene kadar)
        if hasattr(oturum_var.sistem, 'motor_ref') and oturum_var.sistem.motor_ref:
            try:
                status("ELEKTRİK GERİ", "Konveyör durduruluyor (GSI bekleniyor)...", level="wait")
                oturum_var.sistem.motor_ref.konveyor_dur()
                ok("ELEKTRİK GERİ", "Konveyör durduruldu")
                log_system("UPS geri geldi: Konveyör durduruldu (GSI bekleniyor)")
            except Exception as e:
                err("ELEKTRİK GERİ", f"Konveyör durdurma hatası: {e}")
                log_error(f"UPS geri geldi: Konveyör durdurma hatası: {e}")
        
        # 4. Sistem durumunu sıfırla
        step("ELEKTRİK GERİ", "Sistem durumu sıfırlanıyor...")
        oturum_var.sistem.iade_lojik = False
        oturum_var.sistem.iade_lojik_onceki_durum = False
        oturum_var.sistem.barkod_lojik = False
        oturum_var.sistem.veri_senkronizasyon_listesi.clear()
        oturum_var.sistem.kabul_edilen_urunler.clear()
        oturum_var.sistem.onaylanan_urunler.clear()
        oturum_var.sistem.uzunluk_goruntu_isleme = None
        oturum_var.sistem.agirlik_kuyruk.clear()
        oturum_var.sistem.uzunluk_motor_verisi = None
        ok("ELEKTRİK GERİ", "Sistem durumu sıfırlandı")
        
        wait("ELEKTRİK GERİ", "GSI mesajı bekleniyor - Yeni oturum için hazır")
        ok("ELEKTRİK GERİ", "Tüm işlemler tamamlandı")
        log_system("✅ UPS güç geri gelme işlemleri tamamlandı")
        log_system("🔄 Sistem GSI mesajı bekliyor - Yeni oturum için hazır")
        
    except Exception as e:
        err("ELEKTRİK GERİ", f"İşlem hatası: {e}")
        log_error(f"UPS güç geri gelme işleme hatası: {e}")


def check_gsi_after_power_restore():
    """Güç geri geldikten sonra GSI mesajı kontrolü"""
    if (hasattr(oturum_var.sistem, 'gsi_lojik') and 
        oturum_var.sistem.gsi_lojik and 
        hasattr(oturum_var.sistem, 'ups_kesintisi') and 
        not oturum_var.sistem.ups_kesintisi):
        
        section("🔄 GSI MESAJI ALINDI!", "UPS kesintisi sonrası sistem normalleşiyor")
        ok("SİSTEM", "Sistem normal çalışmaya dönüyor")
        log_system("🔄 GSI mesajı alındı - UPS kesintisi sonrası sistem normalleşiyor")
        
        # GSI lojik durumunu temizle
        oturum_var.sistem.gsi_lojik = False
        
        # Sistem normal çalışmaya devam edebilir
        return True
    
    return False
