#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Görüntü İşleme Servisi
Ubuntu Server için optimize edilmiş, asenkron görüntü işleme sistemi
Global Shutter kameralar için ultra hızlı işleme
"""

import time
import cv2
import os
import threading
import queue
from ultralytics import YOLO
from .kamera_servisi import KameraServisi
from .goruntu_sonuc_tipi import GoruntuSonuc, MalzemeTuru

# Thread lock ve queue
goruntu_lock = threading.Lock()
goruntu_queue = queue.Queue(maxsize=10)  # En fazla 10 görüntü bekleyebilir

class GoruntuIslemeServisi:
    """Ana görüntü işleme servisi sınıfı - Thread-safe asenkron işleme"""
    
    def __init__(self):
        """Servisi başlat"""
        print("🔄 [GÖRÜNTÜİŞ] Görüntü işleme servisi başlatılıyor...")
        
        # YOLO modelini yükle
        model_yolu = os.path.join(os.path.dirname(__file__), "b_s_y.pt")
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
        
        # Asenkron işleme için thread kontrolü
        self.islem_thread_aktif = False
        self.islem_thread = None
        self.sonuc_queue = queue.Queue(maxsize=5)
        
        # GSO sensörü için asenkron thread'i hemen başlat
        self._asenkron_isleme_baslat()
        
        # YOLO etiketlerini malzeme türlerine eşle
        self.etiket_eslemesi = {
            # PET türleri
            "bottle": MalzemeTuru.PET,
            "pet": MalzemeTuru.PET,
            "pet_bottle": MalzemeTuru.PET,
            "plastic_bottle": MalzemeTuru.PET,
            "plastik": MalzemeTuru.PET,
            "plastic": MalzemeTuru.PET,
            
            # Cam türleri
            "glass": MalzemeTuru.CAM,
            "glass_bottle": MalzemeTuru.CAM,
            "cam": MalzemeTuru.CAM,
            
            # Alüminyum türleri  
            "can": MalzemeTuru.ALUMINYUM,
            "aluminum": MalzemeTuru.ALUMINYUM,
            "aluminum_can": MalzemeTuru.ALUMINYUM,
            "metal_can": MalzemeTuru.ALUMINYUM,
            "alüminyum": MalzemeTuru.ALUMINYUM,
            "metal": MalzemeTuru.ALUMINYUM,
        }
        
        print("✅ [GÖRÜNTÜİŞ] Servisi başarıyla başlatıldı - kamera sürekli hazır")
    
    def goruntu_yakala_ve_isle(self) -> GoruntuSonuc:
        """
        GSO tetiklemesi için MAKSIMUM HIZLI görüntü yakalama
        Sensör sinyali geldiği anda anında fotoğraf çeker
        
        Returns:
            GoruntuSonuc: İşlenmiş görüntü sonucu
        """
        try:
            # ULTRA HIZLI görüntü yakala - minimal kod
            with goruntu_lock:
                kare = self.kamera.fotograf_cek()
            
            if kare is None:
                return self._hata_sonucu("kamera_hatasi")
            
            # HIZLI queue işlemi
            try:
                islem_id = int(time.time() * 1000000)  # Mikrosaniye
                goruntu_queue.put_nowait({
                    'id': islem_id,
                    'kare': kare,
                    'zaman': time.time()
                })
                
                # Sonucu HEMEN bekle (500ms max - daha hızlı)
                try:
                    sonuc_data = self.sonuc_queue.get(timeout=0.5)
                    return sonuc_data['sonuc']
                        
                except queue.Empty:
                    # Timeout: direkt senkron işle
                    return self._senkron_isle(kare)
                    
            except queue.Full:
                # Kuyruk dolu: direkt senkron işle
                return self._senkron_isle(kare)
                
        except Exception as e:
            return self._hata_sonucu("genel_hata")
    
    def _asenkron_isleme_baslat(self):
        """Asenkron YOLO işleme thread'ini başlatır"""
        if self.islem_thread_aktif:
            return
            
        self.islem_thread_aktif = True
        self.islem_thread = threading.Thread(
            target=self._asenkron_isleme_worker, 
            daemon=True,
            name="GoruntuIslemeThread"
        )
        self.islem_thread.start()
        print("🚀 [GÖRÜNTÜİŞ] Asenkron işleme thread'i başlatıldı")
    
    def _asenkron_isleme_worker(self):
        """Asenkron YOLO işleme worker thread'i"""
        print("🔄 [GÖRÜNTÜİŞ] İşleme worker başladı")
        
        while self.islem_thread_aktif:
            try:
                # Görüntü var mı kontrol et
                try:
                    goruntu_data = goruntu_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # YOLO ile işle
                baslangic = time.time()
                sonuc = self._yolo_isle(goruntu_data['kare'])
                isleme_suresi = (time.time() - baslangic) * 1000
                
                print(f"🧠 [GÖRÜNTÜİŞ] YOLO işleme süresi: {isleme_suresi:.1f}ms")
                
                # Sonucu geri gönder
                try:
                    self.sonuc_queue.put_nowait({
                        'id': goruntu_data['id'],
                        'sonuc': sonuc,
                        'sure': isleme_suresi
                    })
                except queue.Full:
                    print("⚠️ [GÖRÜNTÜİŞ] Sonuç kuyruğu dolu, eski sonuç atılıyor")
                    try:
                        self.sonuc_queue.get_nowait()  # Eski sonucu at
                        self.sonuc_queue.put_nowait({
                            'id': goruntu_data['id'],
                            'sonuc': sonuc,
                            'sure': isleme_suresi
                        })
                    except:
                        pass
                        
            except Exception as e:
                print(f"❌ [GÖRÜNTÜİŞ] Worker hatası: {e}")
                
        print("🛑 [GÖRÜNTÜİŞ] İşleme worker durdu")
    
    def _senkron_isle(self, kare) -> GoruntuSonuc:
        """Senkron YOLO işleme (fallback)"""
        print("🔄 [GÖRÜNTÜİŞ] Senkron işleme")
        return self._yolo_isle(kare)
    
    def _yolo_isle(self, kare) -> GoruntuSonuc:
        """YOLO ile görüntü işleme (asenkron/senkron ortak)"""
        try:
            # YOLO ile nesne tespiti
            sonuclar = self.model.predict(
                source=kare,
                device=self.cihaz,
                save=False,
                conf=0.75,  # Güven eşiği
                iou=0.5,    # IoU eşiği
                verbose=False,
                stream=False
            )
            
            # Tespit edilen nesneleri işle
            tespit_edilen_nesneler = []
            
            for sonuc in sonuclar:
                if sonuc.boxes is None:
                    continue
                    
                kutular = sonuc.boxes.xyxy.cpu().numpy().astype(int)
                siniflar = sonuc.boxes.cls.cpu().numpy().astype(int)
                guven_skorlari = sonuc.boxes.conf.cpu().numpy()
                
                for kutu, sinif_id, guven in zip(kutular, siniflar, guven_skorlari):
                    x1, y1, x2, y2 = kutu
                    etiket = self.model.names[sinif_id]
                    
                    # Boyutları mm'ye çevir
                    genislik_mm = (x2 - x1) * self.x_olcek
                    yukseklik_mm = (y2 - y1) * self.y_olcek
                    
                    # Malzeme türünü belirle
                    malzeme_turu = self._etiket_to_malzeme(etiket)
                    
                    tespit_edilen_nesneler.append({
                        "tur": malzeme_turu,
                        "guven": round(guven, 3),
                        "genislik_mm": round(genislik_mm, 2),
                        "yukseklik_mm": round(yukseklik_mm, 2),
                        "etiket": etiket
                    })
                    
                    print(f"📦 [TESPIT] {etiket} → {malzeme_turu.name} | "
                          f"Güven: {guven:.3f} | "
                          f"Boyut: {genislik_mm:.1f}x{yukseklik_mm:.1f}mm")
            
            # Sonuç döndür
            if not tespit_edilen_nesneler:
                print("❌ [GÖRÜNTÜİŞ] Hiç nesne tespit edilmedi")
                return GoruntuSonuc(
                    genislik_mm=0,
                    yukseklik_mm=0,
                    tur=MalzemeTuru.BILINMEYEN,
                    guven_skoru=0,
                    mesaj="nesne_yok"
                )
            
            # En yüksek güven skoruna sahip nesneyi al
            en_iyi_nesne = max(tespit_edilen_nesneler, key=lambda x: x["guven"])
            
            return GoruntuSonuc(
                genislik_mm=en_iyi_nesne["genislik_mm"],
                yukseklik_mm=en_iyi_nesne["yukseklik_mm"],
                tur=en_iyi_nesne["tur"],
                guven_skoru=en_iyi_nesne["guven"],
                mesaj="nesne_var"
            )
            
        except Exception as e:
            print(f"❌ [GÖRÜNTÜİŞ] YOLO hatası: {e}")
            return self._hata_sonucu("yolo_hatasi")
    
    def _hata_sonucu(self, hata_tipi: str) -> GoruntuSonuc:
        """Hata durumunda standart sonuç döndürür"""
        return GoruntuSonuc(
            genislik_mm=0,
            yukseklik_mm=0,
            tur=MalzemeTuru.BILINMEYEN,
            guven_skoru=0,
            mesaj=hata_tipi
        )
    
    def _etiket_to_malzeme(self, etiket: str) -> MalzemeTuru:
        """
        YOLO etiketini malzeme türüne çevirir
        
        Args:
            etiket: YOLO'dan gelen etiket
            
        Returns:
            MalzemeTuru: Eşleşen malzeme türü
        """
        etiket_kucuk = etiket.lower()
        malzeme = self.etiket_eslemesi.get(etiket_kucuk, MalzemeTuru.BILINMEYEN)
        
        if malzeme == MalzemeTuru.BILINMEYEN:
            print(f"⚠️ [GÖRÜNTÜİŞ] Bilinmeyen YOLO etiketi: {etiket}")
            
        return malzeme
    
    def servisi_kapat(self):
        """Servisi temiz şekilde kapat"""
        try:
            # Asenkron thread'i durdur
            if self.islem_thread_aktif:
                self.islem_thread_aktif = False
                if self.islem_thread and self.islem_thread.is_alive():
                    self.islem_thread.join(timeout=2.0)
                    
            # Kamerayı kapat
            if hasattr(self, 'kamera') and self.kamera:
                self.kamera.durdur()
                
            print("✅ [GÖRÜNTÜİŞ] Servis kapatıldı")
        except Exception as e:
            print(f"⚠️ [GÖRÜNTÜİŞ] Kapatma hatası: {e}")
    
    def __del__(self):
        """Destructor - otomatik temizlik"""
        self.servisi_kapat()