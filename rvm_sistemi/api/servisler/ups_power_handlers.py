#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UPS Güç Kesintisi İşleyicileri
Güç kesintisi ve geri gelme durumlarında yapılacak işlemler
"""

import asyncio
import time
from ...utils.logger import log_system, log_error, log_warning, log_oturum
from ...makine.senaryolar import oturum_var
from ...api.servisler.dimdb_servis import DimdbServis


async def handle_power_failure():
    """UPS güç kesintisi durumunda yapılacak işlemler"""
    print(f"\n{'='*60}")
    print(f"⚡ ELEKTRİK KESİNTİSİ TESPİT EDİLDİ!")
    print(f"🔌 UPS çalışıyor - Acil işlemler başlatılıyor")
    print(f"{'='*60}")
    log_error("⚡ UPS GÜÇ KESİNTİSİ - Acil işlemler başlatılıyor")
    
    try:
        # 1. Uyarı göster
        try:
            from ...makine.senaryolar.uyari import uyari_goster
            uyari_goster(mesaj="Makinenin Elektiriği Kesildi !", sure=20)
            print(f"⚠️  [ELEKTRİK KESİNTİSİ] Uyarı gösterildi")
        except Exception as e:
            print(f"❌ [ELEKTRİK KESİNTİSİ] Uyarı gösterilemedi: {e}")
            log_error(f"UPS kesintisi: Uyarı gösterilemedi: {e}")
        
        # 2. Motorları iptal et - Doğru referans kullan
        try:
            from ...makine import kart_referanslari
            motor = kart_referanslari.motor_al()
            if motor:
                print(f"🛑 [ELEKTRİK KESİNTİSİ] Motorlar iptal ediliyor...")
                motor.motorlari_iptal_et()
                print(f"✅ [ELEKTRİK KESİNTİSİ] Motorlar iptal edildi")
                log_system("UPS kesintisi: Motorlar iptal edildi")
            else:
                print(f"⚠️  [ELEKTRİK KESİNTİSİ] Motor kartı bulunamadı")
                log_warning("UPS kesintisi: Motor kartı bulunamadı")
        except Exception as e:
            print(f"❌ [ELEKTRİK KESİNTİSİ] Motor iptal etme hatası: {e}")
            log_error(f"UPS kesintisi: Motor iptal etme hatası: {e}")
        
        # 3. Aktif oturum var mı kontrol et
        if oturum_var.sistem.aktif_oturum["aktif"]:
            session_id = oturum_var.sistem.aktif_oturum["sessionId"]
            print(f"📋 [ELEKTRİK KESİNTİSİ] Aktif oturum sonlandırılıyor: {session_id}")
            log_oturum("UPS kesintisi: Aktif oturum sonlandırılıyor")
            
            # 4. SessionEnd isteği gönder
            try:
                print(f"📡 [ELEKTRİK KESİNTİSİ] DİM-DB'ye sessionEnd isteği gönderiliyor...")
                import requests
                session_end_data = {"sessionId": session_id}
                response = requests.post("http://localhost:4321/dimdb/sessionEnd", json=session_end_data, timeout=5)
                if response.status_code == 200:
                    print(f"✅ [ELEKTRİK KESİNTİSİ] SessionEnd isteği başarıyla gönderildi")
                    log_oturum("UPS kesintisi: SessionEnd isteği gönderildi")
                else:
                    print(f"⚠️  [ELEKTRİK KESİNTİSİ] SessionEnd isteği başarısız: {response.status_code}")
                    log_warning(f"UPS kesintisi: SessionEnd isteği başarısız: {response.status_code}")
            except Exception as e:
                print(f"❌ [ELEKTRİK KESİNTİSİ] SessionEnd isteği hatası: {e}")
                log_error(f"UPS kesintisi: SessionEnd isteği hatası: {e}")
            
            # 5. Transaction result gönder
            try:
                print(f"📡 [ELEKTRİK KESİNTİSİ] DİM-DB'ye transaction result gönderiliyor...")
                await DimdbServis.send_transaction_result()
                print(f"✅ [ELEKTRİK KESİNTİSİ] Transaction result başarıyla gönderildi")
                log_oturum("UPS kesintisi: Transaction result gönderildi")
            except Exception as e:
                print(f"❌ [ELEKTRİK KESİNTİSİ] Transaction result gönderme hatası: {e}")
                log_error(f"UPS kesintisi: Transaction result gönderme hatası: {e}")
            
            # 6. Oturumu sonlandır
            oturum_var.sistem.aktif_oturum["aktif"] = False
            oturum_var.sistem.aktif_oturum["sessionId"] = ""
            oturum_var.sistem.aktif_oturum["userId"] = ""
            print(f"🔒 [ELEKTRİK KESİNTİSİ] Oturum sonlandırıldı")
            log_oturum("UPS kesintisi: Oturum sonlandırıldı")
        else:
            print(f"ℹ️  [ELEKTRİK KESİNTİSİ] Aktif oturum yok")
        
        # 6. Konveyörde ürün var mı kontrol et ve geri döndür
        if hasattr(oturum_var.sistem, 'motor_ref') and oturum_var.sistem.motor_ref:
            try:
                # Konveyörde ürün var mı kontrol et (kabul edilen ürünler listesi)
                urun_var_mi = (len(oturum_var.sistem.kabul_edilen_urunler) > 0 or 
                              len(oturum_var.sistem.veri_senkronizasyon_listesi) > 0 or
                              oturum_var.sistem.giris_sensor_durum)
                
                if urun_var_mi:
                    print(f"📦 [ELEKTRİK KESİNTİSİ] Konveyörde ürün tespit edildi - geri döndürülüyor...")
                    oturum_var.sistem.motor_ref.konveyor_geri()
                    print(f"✅ [ELEKTRİK KESİNTİSİ] Konveyör geri döndürüldü")
                    log_system("UPS kesintisi: Konveyör geri döndürüldü (ürün vardı)")
                else:
                    print(f"ℹ️  [ELEKTRİK KESİNTİSİ] Konveyörde ürün yok - geri döndürme atlandı")
                    log_system("UPS kesintisi: Konveyörde ürün yok - geri döndürme atlandı")
            except Exception as e:
                print(f"❌ [ELEKTRİK KESİNTİSİ] Konveyör kontrol hatası: {e}")
                log_error(f"UPS kesintisi: Konveyör kontrol hatası: {e}")
        
        # 7. Sistem durumunu güncelle
        oturum_var.sistem.ups_kesintisi = True
        oturum_var.sistem.ups_kesinti_zamani = time.time()
        
        # 8. GSI mesajı gelene kadar bekleme durumuna geç
        oturum_var.sistem.gsi_bekleme_durumu = True
        print(f"⏳ [ELEKTRİK KESİNTİSİ] GSI mesajı bekleniyor...")
        print(f"🔄 [ELEKTRİK KESİNTİSİ] Sistem UPS modunda - GSI gelene kadar bekliyor")
        log_system("UPS kesintisi: GSI mesajı bekleniyor")
        
        print(f"✅ [ELEKTRİK KESİNTİSİ] Tüm işlemler tamamlandı")
        print(f"{'='*60}\n")
        log_system("✅ UPS güç kesintisi işlemleri tamamlandı")
        
    except Exception as e:
        print(f"❌ [ELEKTRİK KESİNTİSİ] İşlem hatası: {e}")
        log_error(f"UPS güç kesintisi işleme hatası: {e}")


async def handle_power_restored():
    """UPS güç geri geldiğinde yapılacak işlemler"""
    print(f"\n{'='*60}")
    print(f"🔌 ELEKTRİK GERİ GELDİ!")
    print(f"⚡ UPS normal çalışmaya döndü - Sistem normalleştiriliyor")
    print(f"{'='*60}")
    log_system("🔌 UPS GÜÇ GERİ GELDİ - Sistem normalleştiriliyor")
    
    try:
        # 1. UPS kesintisi durumunu temizle
        oturum_var.sistem.ups_kesintisi = False
        oturum_var.sistem.ups_kesinti_zamani = None
        print(f"✅ [ELEKTRİK GERİ] UPS kesintisi durumu temizlendi")
        
        # 2. GSI bekleme durumunu temizle
        oturum_var.sistem.gsi_bekleme_durumu = False
        print(f"✅ [ELEKTRİK GERİ] GSI bekleme durumu temizlendi")
        
        # 3. Konveyörü durdur (GSI mesajı gelene kadar)
        if hasattr(oturum_var.sistem, 'motor_ref') and oturum_var.sistem.motor_ref:
            try:
                print(f"⏸️  [ELEKTRİK GERİ] Konveyör durduruluyor (GSI bekleniyor)...")
                oturum_var.sistem.motor_ref.konveyor_dur()
                print(f"✅ [ELEKTRİK GERİ] Konveyör durduruldu")
                log_system("UPS geri geldi: Konveyör durduruldu (GSI bekleniyor)")
            except Exception as e:
                print(f"❌ [ELEKTRİK GERİ] Konveyör durdurma hatası: {e}")
                log_error(f"UPS geri geldi: Konveyör durdurma hatası: {e}")
        
        # 4. Sistem durumunu sıfırla
        print(f"🔄 [ELEKTRİK GERİ] Sistem durumu sıfırlanıyor...")
        oturum_var.sistem.iade_lojik = False
        oturum_var.sistem.iade_lojik_onceki_durum = False
        oturum_var.sistem.barkod_lojik = False
        oturum_var.sistem.veri_senkronizasyon_listesi.clear()
        oturum_var.sistem.kabul_edilen_urunler.clear()
        oturum_var.sistem.onaylanan_urunler.clear()
        oturum_var.sistem.uzunluk_goruntu_isleme = None
        oturum_var.sistem.agirlik_kuyruk.clear()
        oturum_var.sistem.uzunluk_motor_verisi = None
        print(f"✅ [ELEKTRİK GERİ] Sistem durumu sıfırlandı")
        
        print(f"⏳ [ELEKTRİK GERİ] GSI mesajı bekleniyor - Yeni oturum için hazır")
        print(f"✅ [ELEKTRİK GERİ] Tüm işlemler tamamlandı")
        print(f"{'='*60}\n")
        log_system("✅ UPS güç geri gelme işlemleri tamamlandı")
        log_system("🔄 Sistem GSI mesajı bekliyor - Yeni oturum için hazır")
        
    except Exception as e:
        print(f"❌ [ELEKTRİK GERİ] İşlem hatası: {e}")
        log_error(f"UPS güç geri gelme işleme hatası: {e}")


def check_gsi_after_power_restore():
    """Güç geri geldikten sonra GSI mesajı kontrolü"""
    if (hasattr(oturum_var.sistem, 'gsi_lojik') and 
        oturum_var.sistem.gsi_lojik and 
        hasattr(oturum_var.sistem, 'ups_kesintisi') and 
        not oturum_var.sistem.ups_kesintisi):
        
        print(f"\n{'='*60}")
        print(f"🔄 GSI MESAJI ALINDI!")
        print(f"⚡ UPS kesintisi sonrası sistem normalleşiyor")
        print(f"✅ Sistem normal çalışmaya dönüyor")
        print(f"{'='*60}\n")
        log_system("🔄 GSI mesajı alındı - UPS kesintisi sonrası sistem normalleşiyor")
        
        # GSI lojik durumunu temizle
        oturum_var.sistem.gsi_lojik = False
        
        # Sistem normal çalışmaya devam edebilir
        return True
    
    return False
