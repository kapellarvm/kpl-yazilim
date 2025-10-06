#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Kamera Servisi  
Ubuntu Server için Hikrobot MVS kamera kontrol servisi
"""

import sys
import numpy as np
import cv2
from ctypes import *
from .MvCameraControl_class import *

class KameraServisi:
    """Hikrobot MVS kamera kontrol sınıfı"""
    
    def __init__(self):
        """Kamera servisini başlat"""
        self.cam = None
        self.cihaz_listesi = None
        self.aktif_mi = False
        self.surekli_yakalama_aktif = False  # Sürekli yakalama durumu
        
    def baslat(self):
        """Kamerayı başlat ve ayarla"""
        try:
            print("🔄 [KAMERA] SDK başlatılıyor...")
            
            # SDK'yı başlat
            ret_init = MvCamera.MV_CC_Initialize()
            if ret_init != 0:
                raise Exception(f"SDK başlatma hatası! ret[0x{ret_init:x}]")
            
            # Cihaz listesini al
            self.cihaz_listesi = MV_CC_DEVICE_INFO_LIST()
            transport_katmani = (MV_GIGE_DEVICE | MV_USB_DEVICE | 
                               MV_GENTL_CAMERALINK_DEVICE | MV_GENTL_CXP_DEVICE | 
                               MV_GENTL_XOF_DEVICE)
            
            print("🔍 [KAMERA] Cihazlar aranıyor...")
            ret = MvCamera.MV_CC_EnumDevices(transport_katmani, self.cihaz_listesi)
            
            if ret != 0:
                raise Exception(f"Cihaz arama hatası! ret[0x{ret:x}]")
                
            if self.cihaz_listesi.nDeviceNum == 0:
                raise Exception("Hiç kamera bulunamadı! USB yetki kontrolü yapın: 'sudo python3'")
            
            print(f"✅ [KAMERA] {self.cihaz_listesi.nDeviceNum} adet kamera bulundu")
            
            # İlk kamerayı seç
            cihaz_bilgisi = cast(self.cihaz_listesi.pDeviceInfo[0], 
                               POINTER(MV_CC_DEVICE_INFO)).contents
            
            # Kamera handle'ı oluştur
            self.cam = MvCamera()
            ret = self.cam.MV_CC_CreateHandle(cihaz_bilgisi)
            if ret != 0:
                raise Exception(f"Handle oluşturma hatası! ret[0x{ret:x}]")
            
            # Kamerayı aç
            ret = self.cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
            if ret != 0:
                raise Exception(f"Kamera açma hatası! ret[0x{ret:x}]")
            
            # GigE kamera ise paket boyutunu optimize et
            if (cihaz_bilgisi.nTLayerType == MV_GIGE_DEVICE or 
                cihaz_bilgisi.nTLayerType == MV_GENTL_GIGE_DEVICE):
                optimal_paket_boyutu = self.cam.MV_CC_GetOptimalPacketSize()
                if int(optimal_paket_boyutu) > 0:
                    ret = self.cam.MV_CC_SetIntValue("GevSCPSPacketSize", optimal_paket_boyutu)
                    if ret != 0:
                        print(f"⚠️ [KAMERA] Paket boyutu ayarlama uyarısı! ret[0x{ret:x}]")
                else:
                    print(f"⚠️ [KAMERA] Optimal paket boyutu alınamadı! ret[0x{optimal_paket_boyutu:x}]")
            
            # Sürekli görüntü yakalamayı başlat (GSO sensörü için)
            self._surekli_yakalama_baslat()
            
            self.aktif_mi = True
            print("✅ [KAMERA] Başarıyla başlatıldı ve sürekli yakalama aktif")
            
        except Exception as e:
            print(f"❌ [KAMERA] Başlatma hatası: {e}")
            self.durdur()
            raise
    
    def _surekli_yakalama_baslat(self):
        """MV-CS040-10UC için ultra hızlı sürekli yakalamayı başlatır"""
        try:
            if not self.surekli_yakalama_aktif:
                # MV-CS040-10UC için minimal optimizasyonlar (parametre ayarları yapılmaz)
                try:
                    # Sadece buffer optimizasyonu (720x540 resolution için)
                    self.cam.MV_CC_SetIntValue("PayloadSize", 720*540*3)  # RGB için
                    # Burst frame count minimize
                    self.cam.MV_CC_SetIntValue("AcquisitionBurstFrameCount", 1)
                    print("🎯 [KAMERA] MV-CS040-10UC buffer optimizasyonu yapıldı")
                except:
                    print("⚠️ [KAMERA] Buffer optimizasyonu atlandı, devam ediliyor")
                
                ret = self.cam.MV_CC_StartGrabbing()
                if ret != 0:
                    raise Exception(f"Sürekli yakalama başlatma hatası! ret[0x{ret:x}]")
                self.surekli_yakalama_aktif = True
                print("🚀 [KAMERA] MV-CS040-10UC sürekli yakalama başlatıldı (manuel FPS korundu)")
        except Exception as e:
            print(f"❌ [KAMERA] Sürekli yakalama hatası: {e}")
            raise
    
    def fotograf_cek(self):
        """
        ULTRA HIZLI frame yakalama - GSO sensörü için maksimum optimize edilmiş
        Kamera sürekli çalışır, sadece son frame'i alır
        
        Returns:
            np.ndarray: BGR formatında görüntü verisi
        """
        if not self.aktif_mi or not self.cam or not self.surekli_yakalama_aktif:
            raise Exception("Kamera aktif değil veya sürekli yakalama başlatılmamış.")
        
        try:
            # Frame buffer'ı hazırla
            cikis_karesi = MV_FRAME_OUT()
            memset(byref(cikis_karesi), 0, sizeof(cikis_karesi))
            
            # MV-CS040-10UC için minimal timeout (1ms - en hızlı güvenli değer)
            # 540fps → 1.85ms frame interval, 1ms yeterli
            ret = self.cam.MV_CC_GetImageBuffer(cikis_karesi, 1)
            
            if cikis_karesi.pBufAddr and ret == 0:
                # Frame bilgilerini al
                genislik = cikis_karesi.stFrameInfo.nWidth
                yukseklik = cikis_karesi.stFrameInfo.nHeight
                kare_uzunlugu = cikis_karesi.stFrameInfo.nFrameLen
                
                # Buffer'ı numpy array'e çevir - HIZLI
                buffer = (c_ubyte * kare_uzunlugu).from_address(
                    addressof(cikis_karesi.pBufAddr.contents))
                buffer_np = np.frombuffer(buffer, dtype=np.uint8)
                
                # BGR formatına çevir - OPTIMIZED
                bgr_goruntusu = self._bgr_ye_cevir_hizli(buffer_np, cikis_karesi.stFrameInfo)
                
                # Buffer'ı serbest bırak - ANINDA
                self.cam.MV_CC_FreeImageBuffer(cikis_karesi)
                
                if bgr_goruntusu is not None:
                    return bgr_goruntusu
                else:
                    raise Exception("Desteklenmeyen pixel formatı")
                
            else:
                raise Exception(f"Frame alınamadı! ret[0x{ret:x}]")
                
        except Exception as e:
            print(f"❌ [KAMERA] Frame yakalama hatası: {e}")
            return None
    
    def _bgr_ye_cevir_hizli(self, buffer, kare_bilgisi):
        """
        MV-CS040-10UC için ULTRA HIZLI BGR dönüştürme
        Color kamera optimizasyonu - minimal işlem
        
        Args:
            buffer: Ham görüntü verisi
            kare_bilgisi: Frame bilgi yapısı
            
        Returns:
            np.ndarray: BGR formatında görüntü
        """
        pixel_formati = kare_bilgisi.enPixelType
        genislik = kare_bilgisi.nWidth
        yukseklik = kare_bilgisi.nHeight
        
        try:
            # MV-CS040-10UC Color kamera - en yaygın formatlar
            if pixel_formati == 0x02180021:  # BGR8 - Direkt kullan (HIZLI!)
                return np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik, 3))
                
            elif pixel_formati == 0x02180014:  # RGB8 - Tek dönüşüm
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik, 3))
                return cv2.cvtColor(goruntu, cv2.COLOR_RGB2BGR)
                
            # Bayer formatları (eğer kullanılıyorsa)
            elif pixel_formati == 0x01080009:  # BayerRG8
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik))
                return cv2.cvtColor(goruntu, cv2.COLOR_BAYER_BG2BGR)
                
            elif pixel_formati == 0x0108000B:  # BayerBG8  
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik))
                return cv2.cvtColor(goruntu, cv2.COLOR_BAYER_RG2BGR)
                
            elif pixel_formati == 0x01080008:  # BayerGR8
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik))
                return cv2.cvtColor(goruntu, cv2.COLOR_BAYER_GB2BGR)
                
            elif pixel_formati == 0x0108000A:  # BayerGB8
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik))
                return cv2.cvtColor(goruntu, cv2.COLOR_BAYER_GR2BGR)
                
            elif pixel_formati == 0x01080001:  # Mono8 (eğer varsa)
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik))
                return cv2.cvtColor(goruntu, cv2.COLOR_GRAY2BGR)
                
            else:
                # MV-CS040-10UC için varsayılan: BGR8 formatında dene
                return np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik, 3))
                
        except Exception as e:
            # Hızlı fallback - boyut bazlı tahmin
            try:
                total_pixels = len(buffer)
                expected_mono = genislik * yukseklik
                expected_color = genislik * yukseklik * 3
                
                if total_pixels == expected_color:
                    # Color format
                    return np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik, 3))
                elif total_pixels == expected_mono:
                    # Mono format
                    goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik))
                    return cv2.cvtColor(goruntu, cv2.COLOR_GRAY2BGR)
            except:
                pass
            return None

    def _bgr_ye_cevir(self, buffer, kare_bilgisi):
        """
        Ham kamera verisini BGR formatına çevirir
        
        Args:
            buffer: Ham görüntü verisi
            kare_bilgisi: Frame bilgi yapısı
            
        Returns:
            np.ndarray: BGR formatında görüntü
        """
        pixel_formati = kare_bilgisi.enPixelType
        genislik = kare_bilgisi.nWidth
        yukseklik = kare_bilgisi.nHeight
        
        try:
            print(f"🔍 [KAMERA] Pixel formatı: 0x{pixel_formati:x}")
            
            if pixel_formati == 0x01080001:  # Mono8
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik))
                return cv2.cvtColor(goruntu, cv2.COLOR_GRAY2BGR)
                
            elif pixel_formati == 0x02180014:  # RGB8
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik, 3))
                return cv2.cvtColor(goruntu, cv2.COLOR_RGB2BGR)
                
            elif pixel_formati == 0x02180021:  # BGR8
                return np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik, 3))
                
            elif pixel_formati == 0x01080009:  # BayerRG8 - En yaygın format
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik))
                return cv2.cvtColor(goruntu, cv2.COLOR_BAYER_BG2BGR)  # RG→BG dönüşümü!
                
            elif pixel_formati == 0x0108000B:  # BayerBG8  
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik))
                return cv2.cvtColor(goruntu, cv2.COLOR_BAYER_RG2BGR)
                
            elif pixel_formati == 0x01080008:  # BayerGR8
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik))
                return cv2.cvtColor(goruntu, cv2.COLOR_BAYER_GB2BGR)
                
            elif pixel_formati == 0x0108000A:  # BayerGB8
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik))
                return cv2.cvtColor(goruntu, cv2.COLOR_BAYER_GR2BGR)
                
            else:
                print(f"⚠️ [KAMERA] Desteklenmeyen pixel formatı: 0x{pixel_formati:x}")
                # Varsayılan olarak BayerRG8 formatında dene
                print("🔄 [KAMERA] Varsayılan BayerRG8 dönüşümü deneniyor...")
                goruntu = np.frombuffer(buffer, dtype=np.uint8).reshape((yukseklik, genislik))
                return cv2.cvtColor(goruntu, cv2.COLOR_BAYER_BG2BGR)
                
        except Exception as e:
            print(f"❌ [KAMERA] BGR çevirme hatası: {e}")
            return None
    
    def durdur(self):
        """Kamerayı kapat ve kaynakları temizle"""
        try:
            # Sürekli yakalamayı durdur
            if self.surekli_yakalama_aktif and self.cam:
                self.cam.MV_CC_StopGrabbing()
                self.surekli_yakalama_aktif = False
                print("🛑 [KAMERA] Sürekli yakalama durduruldu")
            
            if self.cam:
                self.cam.MV_CC_CloseDevice()
                self.cam.MV_CC_DestroyHandle()
                
            if self.aktif_mi:
                MvCamera.MV_CC_Finalize()
                
            self.aktif_mi = False
            print("✅ [KAMERA] Kapatıldı ve kaynaklar temizlendi")
            
        except Exception as e:
            print(f"⚠️ [KAMERA] Kapatma uyarısı: {e}")
    
    def __del__(self):
        """Destructor - otomatik temizlik"""
        self.durdur()