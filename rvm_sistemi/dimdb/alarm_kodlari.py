"""
DİM DB Alarm Kodları

Bu modül RVM-DİM DB entegrasyon dokümanına uygun alarm kodlarını içerir.
Alarm kodları sistemdeki kritik durumları DİM DB'ye bildirmek için kullanılır.
"""

from enum import IntEnum


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
    AŞIRI_AGIRLIK = 302
    
    # Ağ/İletişim Hataları (400-499)
    DIMDB_BAGLANTI_HATASI = 400
    DIMDB_TIMEOUT = 401
    IMZA_DOGRULAMA_HATASI = 402
    
    # Güç/Enerji Hataları (500-599)
    GUC_KESINTISI = 500
    DUSUK_BATARYA = 501
    UPS_AKTIF = 502


# Alarm kodlarına karşılık gelen Türkçe açıklamalar
ALARM_MESAJLARI = {
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
    AlarmKodlari.AŞIRI_AGIRLIK: "Aşırı ağırlık tespit edildi",
    
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

