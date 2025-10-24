"""
DİM-DB Servisleri
DİM-DB entegrasyonu ve bildirim işlemleri
"""

import uuid
import time
import asyncio
from typing import Dict, Any

from ...dimdb import dimdb_istemcisi
from ...makine.senaryolar import oturum_var
from ...utils.logger import log_dimdb, log_error, log_success, log_warning
from ...utils.terminal import ok, warn, err, status


class DimdbServis:
    """DİM-DB işlemlerini yöneten servis sınıfı"""
    
    @staticmethod
    async def send_package_result(barcode: str, agirlik: float, materyal_turu: int, 
                                uzunluk: float, genislik: float, kabul_edildi: bool, 
                                sebep_kodu: int, sebep_mesaji: str) -> None:
        """Her ürün doğrulaması sonrası DİM-DB'ye paket sonucunu gönderir"""
        if not oturum_var.sistem.aktif_oturum["aktif"]:
            warn("DİM-DB", "Aktif oturum yok, paket sonucu gönderilmedi")
            log_warning("Aktif oturum yok, paket sonucu gönderilmedi")
            return
        
        try:
            # UUID'yi al
            paket_uuid = oturum_var.sistem.aktif_oturum["paket_uuid_map"].get(barcode, str(uuid.uuid4()))
            
            # Kabul edilen ürün sayılarını hesapla
            pet_sayisi = sum(1 for u in oturum_var.sistem.onaylanan_urunler if u.get('materyal_turu') == 1)
            cam_sayisi = sum(1 for u in oturum_var.sistem.onaylanan_urunler if u.get('materyal_turu') == 2)
            alu_sayisi = sum(1 for u in oturum_var.sistem.onaylanan_urunler if u.get('materyal_turu') == 3)
            
            result_payload = {
                "guid": str(uuid.uuid4()),
                "uuid": paket_uuid,
                "sessionId": oturum_var.sistem.aktif_oturum["sessionId"],
                "barcode": barcode,
                "measuredPackWeight": float(agirlik),
                "measuredPackHeight": float(uzunluk),
                "measuredPackWidth": float(genislik),
                "binId": materyal_turu if kabul_edildi else -1,
                "result": sebep_kodu,
                "resultMessage": sebep_mesaji,
                "acceptedPetCount": pet_sayisi,
                "acceptedGlassCount": cam_sayisi,
                "acceptedAluCount": alu_sayisi
            }
            
            await dimdb_istemcisi.send_accept_package_result(result_payload)
            ok("DİM-DB", f"Paket sonucu gönderildi: {barcode} - {'Kabul' if kabul_edildi else 'Red'}")
            log_success(f"Paket sonucu başarıyla gönderildi: {barcode} - {'Kabul' if kabul_edildi else 'Red'}")
            
        except Exception as e:
            err("DİM-DB", f"Paket sonucu gönderme hatası: {e}")
            import traceback
            err("DİM-DB", f"Hata detayı: {traceback.format_exc()}")
            log_error(f"Paket sonucu gönderme hatası: {e}")
            log_error(f"Hata detayı: {traceback.format_exc()}")

    @staticmethod
    def send_package_result_sync(barcode: str, agirlik: float, materyal_turu: int, 
                               uzunluk: float, genislik: float, kabul_edildi: bool, 
                               sebep_kodu: int, sebep_mesaji: str) -> None:
        """Thread-safe DİM-DB paket sonucu gönderimi"""
        try:
            # Yeni event loop oluştur ve çalıştır
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    DimdbServis.send_package_result(
                        barcode, agirlik, materyal_turu, uzunluk, genislik, 
                        kabul_edildi, sebep_kodu, sebep_mesaji
                    )
                )
            finally:
                loop.close()
        except Exception as e:
            err("DİM-DB SYNC", f"Hata: {e}")
            log_error(f"DİM-DB SYNC Hata: {e}")

    @staticmethod
    async def send_transaction_result() -> None:
        """Oturum sonlandığında DİM-DB'ye transaction result gönderir"""
        if not oturum_var.sistem.aktif_oturum["aktif"]:
            warn("DİM-DB", "Aktif oturum yok, transaction result gönderilmedi")
            log_warning("Aktif oturum yok, transaction result gönderilmedi")
            return
        
        try:
            # Kabul edilen ürünleri konteyner formatına dönüştür
            containers = {}
            for urun in oturum_var.sistem.onaylanan_urunler:
                barcode = urun["barkod"]
                if barcode not in containers:
                    containers[barcode] = {
                        "barcode": barcode,
                        "material": urun["materyal_turu"],
                        "count": 0,
                        "weight": 0
                    }
                containers[barcode]["count"] += 1
                containers[barcode]["weight"] += urun["agirlik"]
            
            transaction_payload = {
                "guid": str(uuid.uuid4()),
                "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "rvm": dimdb_istemcisi.RVM_ID,
                "id": oturum_var.sistem.aktif_oturum["sessionId"] + "-tx",
                "firstBottleTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "endTime": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "sessionId": oturum_var.sistem.aktif_oturum["sessionId"],
                "userId": oturum_var.sistem.aktif_oturum["userId"],
                "created": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                "containerCount": len(oturum_var.sistem.onaylanan_urunler),
                "containers": list(containers.values())
            }
            
            await dimdb_istemcisi.send_transaction_result(transaction_payload)
            ok("DİM-DB", f"Transaction result gönderildi: {oturum_var.sistem.aktif_oturum['sessionId']}")
            log_success(f"Transaction result başarıyla gönderildi: {oturum_var.sistem.aktif_oturum['sessionId']}")
            
            # Kullanıcı puan özeti
            pet_sayisi = sum(1 for u in oturum_var.sistem.onaylanan_urunler if u.get('materyal_turu') == 1)
            cam_sayisi = sum(1 for u in oturum_var.sistem.onaylanan_urunler if u.get('materyal_turu') == 2)
            alu_sayisi = sum(1 for u in oturum_var.sistem.onaylanan_urunler if u.get('materyal_turu') == 3)
            
            status("OTURUM PUAN ÖZETİ", f"Kullanıcı: {oturum_var.sistem.aktif_oturum['userId']} | PET: {pet_sayisi} | CAM: {cam_sayisi} | ALÜMİNYUM: {alu_sayisi}", level="info")
            log_dimdb(f"OTURUM PUAN ÖZETİ - Kullanıcı: {oturum_var.sistem.aktif_oturum['userId']} | PET: {pet_sayisi} puan | CAM: {cam_sayisi} puan | ALÜMİNYUM: {alu_sayisi} puan")
            
        except Exception as e:
            err("DİM-DB", f"Transaction result gönderme hatası: {e}")
            import traceback
            err("DİM-DB", f"Hata detayı: {traceback.format_exc()}")
            log_error(f"Transaction result gönderme hatası: {e}")
            log_error(f"Hata detayı: {traceback.format_exc()}")

    @staticmethod
    def dimdb_bildirim_gonder(barcode: str, agirlik: float, materyal_turu: int, 
                            uzunluk: float, genislik: float, kabul_edildi: bool, 
                            sebep_kodu: int, sebep_mesaji: str) -> None:
        """DİM-DB'ye bildirim gönderir"""
        try:
            DimdbServis.send_package_result_sync(
                barcode, agirlik, materyal_turu, uzunluk, genislik, 
                kabul_edildi, sebep_kodu, sebep_mesaji
            )
        except Exception as e:
            err("DİM-DB BİLDİRİM", f"Hata: {e}")
            log_error(f"DİM-DB BİLDİRİM Hata: {e}")
