# rvm_sistemi/makine/dogrulama.py

# Gerekli modülleri projenin diğer kısımlarından import ediyoruz
from ..veri_tabani import veritabani_yoneticisi

# Materyal ID'lerini anlamlı isimlere çevirmek için bir sözlük
# Bu, kodun okunabilirliğini artırır.
MATERIAL_MAP = {
    1: "PET",
    2: "Cam (Glass)",
    3: "Alüminyum (Alu)"
}

class DogrulamaServisi:
    """
    Gelen bir paketin kabul edilip edilmeyeceğine karar veren tüm
    doğrulama adımlarını yönetir.
    """
    def __init__(self):
        # Görüntü işleme veya sensör sınıfları burada başlatılabilir
        # self.goruntu_isleme = GoruntuIslemeServisi()
        print("Doğrulama servisi başlatıldı.")

    def paketi_dogrula(self, barcode: str) -> dict:
        """
        Verilen bir barkod için tüm doğrulama sürecini çalıştırır.
        
        Args:
            barcode (str): DİM-DB'den gelen ürün barkodu.
            
        Returns:
            dict: Doğrulama sonucunu içeren bir sözlük.
                  Örn: {'kabul_edildi': True, 'materyal_id': 1, 'sebep_kodu': 0}
        """
        print(f"--- Doğrulama Süreci Başladı: {barcode} ---")

        # 1. Adım: Barkod Veritabanı Kontrolü (Referans Alma)
        db_sonucu = veritabani_yoneticisi.barkodu_dogrula(barcode)
        
        if not db_sonucu:
            print("   -> Sonuç: RED. Barkod veritabanında bulunamadı.")
            return {"kabul_edildi": False, "materyal_id": -1, "sebep_kodu": 15} # 15: Şekil uygun değil (veya 99: Diğer)

        # Veritabanından gelen 'material' ID'sini alıyoruz.
        beklenen_materyal_id = db_sonucu['material']
        beklenen_materyal_adi = MATERIAL_MAP.get(beklenen_materyal_id, "Bilinmeyen")
        print(f"   -> Veritabanı Referansı: Bu ürün '{beklenen_materyal_adi}' olmalı (ID: {beklenen_materyal_id}).")


        # 2. Adım: Görüntü İşleme Kontrolü (Gelecekte Eklenecek)
        # print("   -> Görüntü İşleme: (Simülasyon)")
        # # Örnek senaryo: Görüntü işleme Cam (2) dedi, ama veritabanı PET (1) bekliyordu.
        # goruntu_tespiti_id = 2 
        # if goruntu_tespiti_id != beklenen_materyal_id:
        #     print(f"   -> Sonuç: RED. Görüntü doğrulama başarısız. Beklenen: '{beklenen_materyal_adi}', Tespit edilen: '{MATERIAL_MAP.get(goruntu_tespiti_id)}'")
        #     return {"kabul_edildi": False, "materyal_id": -1, "sebep_kodu": 15} # 15: Şekil uygun değil


        # 3. Adım: Ağırlık Sensörü Kontrolü (Gelecekte Eklenecek)
        # print("   -> Ağırlık Kontrolü: (Simülasyon)")
        # # Örnek senaryo: Ölçülen ağırlık, veritabanındaki aralığın dışında.
        # olculen_agirlik = 50.0 # gr
        # min_agirlik = db_sonucu.get('packMinWeight', 0) # Bu kolonların veritabanında olması gerekir.
        # max_agirlik = db_sonucu.get('packMaxWeight', 1000)
        # if not (min_agirlik <= olculen_agirlik <= max_agirlik):
        #      print(f"   -> Sonuç: RED. Ağırlık uyuşmuyor. Beklenen aralık: {min_agirlik}-{max_agirlik}gr, Ölçülen: {olculen_agirlik}gr")
        #      return {"kabul_edildi": False, "materyal_id": -1, "sebep_kodu": 9} # 9: Çok Ağır (veya Hafif)


        # Tüm adımlar başarılı (şimdilik sadece veritabanı kontrolü var)
        print("   -> Sonuç: KABUL EDİLDİ.")
        return {
            "kabul_edildi": True, 
            "materyal_id": beklenen_materyal_id,
            "sebep_kodu": 0
        }

