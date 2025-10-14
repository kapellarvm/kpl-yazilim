"""
DİM-DB Hata Kodları ve Mesajları
DİM-DB entegrasyon dökümanı v1.9'a uygun hata kodları
"""

from enum import IntEnum
from typing import Dict

class AcceptPackageResultCodes(IntEnum):
    """AcceptPackageResult için hata kodları"""
    BASARILI = 0
    VIDEO_INTERFERANSI = 1
    CESITLI_RED = 2
    GENIS_PROFIL_UYGUN_DEGIL = 3
    METAL_DEDEKTORU_REDDI = 4
    TANIMA_HATASI = 5
    GIRISTE_COK_YAKIN = 6
    COK_HIZLI = 7
    VIDEO_SONUNA_ULASILDI = 8
    COK_AGIR = 9
    ARKA_ODA_REDDI = 10
    SUPHELI_YATIRMA = 11
    CAP_UYGUN_DEGIL = 12
    YUKSEKLIK_UYGUN_DEGIL = 13
    HACIM_UYGUN_DEGIL = 14
    SEKIL_UYGUN_DEGIL = 15
    UST_ILK_ALGILANDI = 16
    EL_ALGILANDI = 17
    DIGER = 99

# Hata kodları ve açıklamaları
HATA_KODLARI: Dict[int, str] = {
    AcceptPackageResultCodes.BASARILI: "Başarılı",
    AcceptPackageResultCodes.VIDEO_INTERFERANSI: "Video İnterferansı",
    AcceptPackageResultCodes.CESITLI_RED: "Çeşitli Red",
    AcceptPackageResultCodes.GENIS_PROFIL_UYGUN_DEGIL: "Geniş profil uygun değil",
    AcceptPackageResultCodes.METAL_DEDEKTORU_REDDI: "Metal dedektörü reddi",
    AcceptPackageResultCodes.TANIMA_HATASI: "Tanıma Hatası",
    AcceptPackageResultCodes.GIRISTE_COK_YAKIN: "Girişte Çok Yakın",
    AcceptPackageResultCodes.COK_HIZLI: "Çok Hızlı",
    AcceptPackageResultCodes.VIDEO_SONUNA_ULASILDI: "Video Sonuna Ulaşıldı",
    AcceptPackageResultCodes.COK_AGIR: "Çok Ağır",
    AcceptPackageResultCodes.ARKA_ODA_REDDI: "Arka Oda Reddi",
    AcceptPackageResultCodes.SUPHELI_YATIRMA: "Şüpheli Yatırma",
    AcceptPackageResultCodes.CAP_UYGUN_DEGIL: "Çap uygun değil",
    AcceptPackageResultCodes.YUKSEKLIK_UYGUN_DEGIL: "Yükseklik uygun değil",
    AcceptPackageResultCodes.HACIM_UYGUN_DEGIL: "Hacim uygun değil",
    AcceptPackageResultCodes.SEKIL_UYGUN_DEGIL: "Şekil uygun değil",
    AcceptPackageResultCodes.UST_ILK_ALGILANDI: "Üst İlk Algılandı",
    AcceptPackageResultCodes.EL_ALGILANDI: "El Algılandı",
    AcceptPackageResultCodes.DIGER: "Diğer"
}

# Mevcut sistem hatalarını yeni hata kodlarına map etme
MEVCUT_HATA_MAP: Dict[str, int] = {
    "Ürün veritabanında yok": AcceptPackageResultCodes.TANIMA_HATASI,
    "Ağırlık sınırları dışında": AcceptPackageResultCodes.COK_AGIR,
    "Genişlik sınırları dışında": AcceptPackageResultCodes.GENIS_PROFIL_UYGUN_DEGIL,
    "Uzunluk sınırları dışında": AcceptPackageResultCodes.YUKSEKLIK_UYGUN_DEGIL,
    "Materyal türü uyuşmuyor": AcceptPackageResultCodes.CESITLI_RED,
    "Barkod bilgisi olmadan ürün verisi geldi": AcceptPackageResultCodes.DIGER
}

def hata_kodu_al(sebep: str) -> int:
    """Sebep mesajına göre uygun hata kodunu döndürür"""
    return MEVCUT_HATA_MAP.get(sebep, AcceptPackageResultCodes.DIGER)

def hata_mesaji_al(hata_kodu: int) -> str:
    """Hata koduna göre açıklama mesajını döndürür"""
    return HATA_KODLARI.get(hata_kodu, "Bilinmeyen hata")

def basarili_mi(hata_kodu: int) -> bool:
    """Hata kodunun başarılı olup olmadığını kontrol eder"""
    return hata_kodu == AcceptPackageResultCodes.BASARILI
