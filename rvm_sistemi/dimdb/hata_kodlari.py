"""
DİM-DB Hata Kodları ve Mesajları
DİM-DB entegrasyon dökümanı v1.9'a uygun hata kodları ve alarm kodları
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

# =============================================================================
# DİM-DB ALARM KODLARI
# =============================================================================

class AlarmKodlari(IntEnum):
    """
    RVM Alarm Kodları
    DİM DB'ye gönderilecek standart alarm kodları
    """
    
    # Genel Sistem Hataları (1-99)
    SISTEM_BASLAMA_HATASI = 1
    SISTEM_KAPANMA_HATASI = 2
    BILINMEYEN_HATA = 99
    
    # Donanım Hataları (100-199)
    MOTOR_BAGLANTI_HATASI = 100
    SENSOR_BAGLANTI_HATASI = 101
    KAMERA_BAGLANTI_HATASI = 102
    BARKOD_OKUYUCU_HATASI = 103
    KONVEYOR_HATASI = 104
    YONLENDIRICI_HATASI = 105
    KLAPE_HATASI = 106
    
    # Konteyner/Depolama Hataları (200-299)
    PET_KONTEYNERI_DOLU = 200
    CAM_KONTEYNERI_DOLU = 201
    METAL_KONTEYNERI_DOLU = 202
    TUM_KONTEYNERLER_DOLU = 203
    
    # Mekanik Hatalar (300-399)
    SIKISMA_TESPITI = 300
    KAPAK_ACIK = 301
    ASIRI_AGIRLIK = 302
    
    # Ağ/İletişim Hataları (400-499)
    DIMDB_BAGLANTI_HATASI = 400
    DIMDB_TIMEOUT = 401
    IMZA_DOGRULAMA_HATASI = 402
    
    # Güç/Enerji Hataları (500-599)
    GUC_KESINTISI = 500
    DUSUK_BATARYA = 501
    UPS_AKTIF = 502

# Alarm kodlarına karşılık gelen Türkçe açıklamalar
ALARM_MESAJLARI: Dict[int, str] = {
    AlarmKodlari.SISTEM_BASLAMA_HATASI: "Sistem başlatılamadı",
    AlarmKodlari.SISTEM_KAPANMA_HATASI: "Sistem düzgün kapatılamadı",
    AlarmKodlari.BILINMEYEN_HATA: "Bilinmeyen sistem hatası",
    
    AlarmKodlari.MOTOR_BAGLANTI_HATASI: "Motor kartı bağlantısı kesildi",
    AlarmKodlari.SENSOR_BAGLANTI_HATASI: "Sensör kartı bağlantısı kesildi",
    AlarmKodlari.KAMERA_BAGLANTI_HATASI: "Kamera bağlantısı kesildi",
    AlarmKodlari.BARKOD_OKUYUCU_HATASI: "Barkod okuyucu hatası",
    AlarmKodlari.KONVEYOR_HATASI: "Konveyör arızası",
    AlarmKodlari.YONLENDIRICI_HATASI: "Yönlendirici mekanizması arızası",
    AlarmKodlari.KLAPE_HATASI: "Klape mekanizması arızası",
    
    AlarmKodlari.PET_KONTEYNERI_DOLU: "PET konteyneri dolu",
    AlarmKodlari.CAM_KONTEYNERI_DOLU: "Cam konteyneri dolu",
    AlarmKodlari.METAL_KONTEYNERI_DOLU: "Metal konteyneri dolu",
    AlarmKodlari.TUM_KONTEYNERLER_DOLU: "Tüm konteynerler dolu",
    
    AlarmKodlari.SIKISMA_TESPITI: "Sistemde sıkışma tespit edildi",
    AlarmKodlari.KAPAK_ACIK: "Servis kapağı açık",
    AlarmKodlari.ASIRI_AGIRLIK: "Aşırı ağırlık tespit edildi",
    
    AlarmKodlari.DIMDB_BAGLANTI_HATASI: "DİM DB bağlantı hatası",
    AlarmKodlari.DIMDB_TIMEOUT: "DİM DB zaman aşımı",
    AlarmKodlari.IMZA_DOGRULAMA_HATASI: "İmza doğrulama hatası",
    
    AlarmKodlari.GUC_KESINTISI: "Güç kesintisi tespit edildi",
    AlarmKodlari.DUSUK_BATARYA: "UPS bataryası düşük",
    AlarmKodlari.UPS_AKTIF: "UPS aktif (elektrik kesintisi)",
}

def alarm_mesaji_al(alarm_kodu: int) -> str:
    """
    Alarm koduna karşılık gelen mesajı döndürür
    
    Args:
        alarm_kodu: Alarm kodu (int)
        
    Returns:
        str: Alarm mesajı
    """
    try:
        kod = AlarmKodlari(alarm_kodu)
        return ALARM_MESAJLARI.get(kod, f"Tanımsız alarm kodu: {alarm_kodu}")
    except ValueError:
        return f"Geçersiz alarm kodu: {alarm_kodu}"
