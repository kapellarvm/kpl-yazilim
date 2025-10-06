#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Görüntü Sonuç Tipleri
Görüntü işleme sonuçlarını temsil eden veri yapıları
"""

from dataclasses import dataclass
from typing import Optional
from enum import IntEnum

class MalzemeTuru(IntEnum):
    """Malzeme türü numaraları (DİM-DB standardına uygun)"""
    BILINMEYEN = 0
    PET = 1        # Plastik şişeler
    CAM = 2        # Cam şişeler  
    ALUMINYUM = 3  # Alüminyum kutular

    @classmethod
    def mesaj_al(cls, kod: int) -> str:
        """Malzeme türü için açıklama mesajı döndürür"""
        mesajlar = {
            cls.PET: "PET Plastik",
            cls.CAM: "Cam Şişe",
            cls.ALUMINYUM: "Alüminyum Kutu"
        }
        return mesajlar.get(cls(kod), "Bilinmeyen Malzeme")

@dataclass
class GoruntuSonuc:
    """
    Görüntü işleme sonucunu temsil eden veri sınıfı
    """
    tur: MalzemeTuru = MalzemeTuru.BILINMEYEN
    guven_skoru: float = 0.0
    genislik_mm: float = 0.0
    yukseklik_mm: float = 0.0
    mesaj: str = ""
    
    def __str__(self) -> str:
        """İnsan okunabilir string representation"""
        return (f"GoruntuSonuc(tur={self.tur.name}, "
                f"guven={self.guven_skoru:.3f}, "
                f"boyut={self.genislik_mm:.1f}x{self.yukseklik_mm:.1f}mm, "
                f"mesaj='{self.mesaj}')")
    
    def basarili_mi(self) -> bool:
        """Başarılı tespit olup olmadığını kontrol eder"""
        return self.tur != MalzemeTuru.BILINMEYEN and self.guven_skoru > 0
    
    def malzeme_adi(self) -> str:
        """Malzeme türünün açıklama adını döndürür"""
        return MalzemeTuru.mesaj_al(self.tur)