#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Görüntü İşleme Servisi
Ubuntu Server için optimize edilmiş, asenkron görüntü işleme sistemi.
Singleton yapısı ile tek bir kaynak üzerinden güvenli yönetim sağlar.
"""

import time
import cv2
import os
import threading
import queue
import uuid
from typing import Union
from ultralytics import YOLO
from pyzbar import pyzbar

# Bu import'ları kendi dosya yapınıza göre düzenleyin
from .kamera_servisi import KameraServisi
from .goruntu_sonuc_tipi import GoruntuSonuc, MalzemeTuru
# Türkçe isimlendirilmiş decorator import edildi.
from .tekil_nesne_yapici import Tekil


@Tekil
class GoruntuIslemeServisi:
    """
    Ana görüntü işleme servisi sınıfı - Thread-safe asenkron işleme.
    Singleton yapısı sayesinde uygulamada sadece tek bir nesnesi bulunur.
    """
    
    def __init__(self):
        """Servisi başlatır ve kaynakları (kamera, model, thread) hazırlar."""
        #print("🔄 [GÖRÜNTÜİŞ] Görüntü işleme servisi başlatılıyor...")
        
        # Özelliklere başlangıç değeri atayarak güvenliği artırıyoruz
        self.kamera = None
        self.islem_thread = None
        self.islem_thread_aktif = False

        # Sınıf içi kilit ve kuyruk yapıları (daha iyi kapsülleme)
        self.kamera_lock = threading.Lock()
        self.goruntu_queue = queue.Queue(maxsize=10)
        
        # Asenkron sonuçları güvenli bir şekilde almak için istek-cevap mekanizması
        self.bekleyen_istekler = {}
        self.istek_lock = threading.Lock()

        try:
            # YOLO modelini yükle
            model_yolu = os.path.join(os.path.dirname(__file__), "kpl04.pt")
            if not os.path.exists(model_yolu):
                raise FileNotFoundError(f"YOLO model dosyası bulunamadı: {model_yolu}")
            
            self.model = YOLO(model_yolu)
            self.cihaz = "cpu"
            
            # Kamerayı başlat
            self.kamera = KameraServisi()
            self.kamera.baslat()
            
            # Kalibrasyon değerleri (mm/pixel)
            self.x_olcek = 0.5510
            self.y_olcek = 0.5110
            
            # Asenkron işleme için worker thread'i başlat
            self._asenkron_isleme_baslat()
            
            self.etiket_eslemesi = {
                 "bottle": MalzemeTuru.PET, "pet": MalzemeTuru.PET, "pet_bottle": MalzemeTuru.PET,
                 "plastic_bottle": MalzemeTuru.PET, "plastik": MalzemeTuru.PET, "plastic": MalzemeTuru.PET,
                 "glass": MalzemeTuru.CAM, "glass_bottle": MalzemeTuru.CAM, "cam": MalzemeTuru.CAM,
                 "can": MalzemeTuru.ALUMINYUM, "aluminum": MalzemeTuru.ALUMINYUM, "aluminum_can": MalzemeTuru.ALUMINYUM,
                 "metal_can": MalzemeTuru.ALUMINYUM, "alüminyum": MalzemeTuru.ALUMINYUM, "metal": MalzemeTuru.ALUMINYUM,
            }
            
            print("✅ [GÖRÜNTÜİŞ] Servis başarıyla başlatıldı - kamera sürekli hazır")

        except Exception as e:
            print(f"❌ [GÖRÜNTÜİŞ] Başlatma sırasında kritik hata: {e}")
            self.servisi_kapat() # Hata durumunda kaynakları serbest bırak
            raise # Hatayı yukarı taşıyarak uygulamanın çökmesini sağla

    def goruntu_yakala_ve_isle(self, islem_tipi: str = "yolo") -> Union[GoruntuSonuc, str, None]:
        """
        Görüntü yakalar ve belirtilen işleme tipine göre (YOLO veya QR) işler.
        YOLO işlemleri asenkron olarak arka planda yürütülür ve sonuç beklenir.
        QR işlemleri hızlı olduğu için senkron olarak yapılır.
        """
        try:
            with self.kamera_lock:
                kare = self.kamera.fotograf_cek()
            
            if kare is None:
                return self._hata_sonucu("kamera_hatasi")
            
            if islem_tipi == "yolo":
                return self._yolo_istegi_gonder_ve_bekle(kare)
            
            elif islem_tipi == "qr":
                return self._qr_kodu_oku(kare)

        except Exception as e:
            print(f"❌ [GÖRÜNTÜİŞ] 'goruntu_yakala_ve_isle' hatası: {e}")
            return self._hata_sonucu("genel_hata")

    def _yolo_istegi_gonder_ve_bekle(self, kare) -> GoruntuSonuc:
        """YOLO işleme isteğini kuyruğa gönderir ve sonucun gelmesini bekler."""
        islem_id = str(uuid.uuid4())
        event = threading.Event()
        result_container = {} # Sonucu taşımak için

        with self.istek_lock:
            self.bekleyen_istekler[islem_id] = (event, result_container)
        
        try:
            self.goruntu_queue.put_nowait({'id': islem_id, 'kare': kare})
        except queue.Full:
            print("⚠️ [GÖRÜNTÜİŞ] İşlem kuyruğu dolu. İstek senkron olarak işleniyor.")
            # Fallback: Kuyruk doluysa, doğrudan işle ve bekleme.
            return self._yolo_isle(kare)

        # Sonucun gelmesini bekle (timeout ile)
        event_set = event.wait(timeout=1.0) # 1 saniye bekle

        # İsteği temizle
        with self.istek_lock:
            # `pop` kullanarak hem alıp hem siliyoruz
            _, result_container = self.bekleyen_istekler.pop(islem_id, (None, None))
        
        if event_set and result_container:
            return result_container.get('sonuc')
        else:
            print("⚠️ [GÖRÜNTÜİŞ] YOLO işleme zaman aşımına uğradı.")
            return self._hata_sonucu("zaman_asimi")

    def _qr_kodu_oku(self, kare) -> Union[str, None]:
        """Verilen görüntüdeki QR kodunu okur (senkron işlem)."""
        try:
            gri_kare = cv2.cvtColor(kare, cv2.COLOR_BGR2GRAY)
            qr_kodlar = pyzbar.decode(gri_kare)
            
            if not qr_kodlar:
                print("ℹ️ [QR KOD] Görüntüde QR kod tespit edilmedi.")
                return None
            
            qr_veri = qr_kodlar[0].data.decode('utf-8')
            print(f"✅ [QR KOD] QR kod başarıyla okundu: {qr_veri}")
            return qr_veri
        except Exception as e:
            print(f"❌ [QR KOD] QR okuma sırasında hata: {e}")
            return None

    def _asenkron_isleme_baslat(self):
        """Asenkron YOLO işleme için worker thread'ini başlatır."""
        if self.islem_thread_aktif:
            return
            
        self.islem_thread_aktif = True
        self.islem_thread = threading.Thread(
            target=self._asenkron_isleme_worker, 
            daemon=True,
            name="GoruntuIslemeThread"
        )
        self.islem_thread.start()
        #print("🚀 [GÖRÜNTÜİŞ] Asenkron işleme thread'i başlatıldı.")

    def _asenkron_isleme_worker(self):
        """Kuyruktan görüntüleri alıp YOLO ile işleyen worker döngüsü."""
        #print("👷 [WORKER] Görüntü işleme worker'ı başladı.")
        
        while self.islem_thread_aktif:
            try:
                goruntu_data = self.goruntu_queue.get(timeout=1.0)
                
                # Kapatma sinyali kontrolü
                if goruntu_data is None:
                    break

                islem_id = goruntu_data['id']
                baslangic = time.time()
                sonuc = self._yolo_isle(goruntu_data['kare'])
                isleme_suresi = (time.time() - baslangic) * 1000
                print(f"🧠 [WORKER] YOLO işleme süresi: {isleme_suresi:.1f}ms (ID: ...{islem_id[-6:]})")
                
                # Sonucu bekleyen thread'e bildir
                with self.istek_lock:
                    if islem_id in self.bekleyen_istekler:
                        event, result_container = self.bekleyen_istekler[islem_id]
                        result_container['sonuc'] = sonuc
                        event.set() # Bekleyen thread'i uyandır

            except queue.Empty:
                continue # Kuyruk boşsa döngüye devam et
            except Exception as e:
                print(f"❌ [WORKER] Worker thread'inde hata: {e}")
                
        print("🛑 [WORKER] Görüntü işleme worker'ı durdu.")

    def _yolo_isle(self, kare) -> GoruntuSonuc:
        """YOLO modelini kullanarak görüntüdeki nesneleri tespit eder."""
        try:
            sonuclar = self.model.predict(
                source=kare, device=self.cihaz, save=False, conf=0.75,
                iou=0.5, verbose=False, stream=False
            )
            
            tespit_edilen_nesneler = []
            if sonuclar and sonuclar[0].boxes:
                for kutu in sonuclar[0].boxes:
                    x1, y1, x2, y2 = map(int, kutu.xyxy[0])
                    guven = float(kutu.conf[0])
                    sinif_id = int(kutu.cls[0])
                    etiket = self.model.names[sinif_id]
                    
                    genislik_mm = (x2 - x1) * self.x_olcek
                    yukseklik_mm = (y2 - y1) * self.y_olcek
                    malzeme_turu = self.etiket_eslemesi.get(etiket.lower(), MalzemeTuru.BILINMEYEN)
                    
                    tespit_edilen_nesneler.append({
                        "tur": malzeme_turu, "guven": guven,
                        "genislik_mm": genislik_mm, "yukseklik_mm": yukseklik_mm,
                    })
            
            if not tespit_edilen_nesneler:
                return self._hata_sonucu("nesne_yok")
            
            en_iyi_nesne = max(tespit_edilen_nesneler, key=lambda x: x["guven"])
            return GoruntuSonuc(
                genislik_mm=round(en_iyi_nesne["genislik_mm"], 2),
                yukseklik_mm=round(en_iyi_nesne["yukseklik_mm"], 2),
                tur=en_iyi_nesne["tur"],
                guven_skoru=round(en_iyi_nesne["guven"], 3),
                mesaj="nesne_var"
            )
        except Exception as e:
            print(f"❌ [YOLO] YOLO işleme hatası: {e}")
            return self._hata_sonucu("yolo_hatasi")

    def _hata_sonucu(self, hata_tipi: str) -> GoruntuSonuc:
        """Hata durumları için standart bir GoruntuSonuc nesnesi döndürür."""
        if hata_tipi != "nesne_yok":
             print(f"⚠️ [GÖRÜNTÜİŞ] Hata sonucu oluşturuldu: {hata_tipi}")
        return GoruntuSonuc(
            genislik_mm=0, yukseklik_mm=0, tur=MalzemeTuru.BILINMEYEN,
            guven_skoru=0, mesaj=hata_tipi
        )

    def servisi_kapat(self):
        """Tüm kaynakları (thread, kamera) güvenli bir şekilde kapatır."""
        print("🛑 [GÖRÜNTÜİŞ] Servis kapatılıyor...")
        if self.islem_thread_aktif:
            self.islem_thread_aktif = False
            try:
                # Worker'ın beklemeden çıkması için sinyal gönder
                self.goruntu_queue.put(None)
            except Exception:
                pass # Kuyruk hatası önemli değil
            
            if self.islem_thread and self.islem_thread.is_alive():
                self.islem_thread.join(timeout=2.0)
        
        if self.kamera:
            self.kamera.durdur()
            
        print("✅ [GÖRÜNTÜİŞ] Servis başarıyla kapatıldı.")

    def __del__(self):
        """Nesne silinirken otomatik temizlik yapılmasını sağlar."""
        self.servisi_kapat()

