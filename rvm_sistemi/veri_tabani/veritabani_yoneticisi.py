import sqlite3
import os
from datetime import datetime, timedelta

# Veritabanı dosyasının yolunu projenin ana dizini olarak ayarla
# Bu, betiğin nereden çalıştırıldığına bakılmaksızın dosyanın her zaman aynı yerde olmasını sağlar.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB_PATH = os.path.join(PROJECT_ROOT, "rvm_veritabani.db")

# Türkiye saati (sistem artık Türkiye saat diliminde)
def turkiye_saati():
    """Türkiye saatini döndürür (sistem artık Türkiye saat diliminde)"""
    return datetime.now()

def init_db():
    """
    Veritabanını ve 'products' tablosunu oluşturur (eğer mevcut değilse).
    """
    try:
        print(f"Veritabanı kontrol ediliyor/oluşturuluyor: {DB_PATH}")
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Products tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    barcode TEXT NOT NULL UNIQUE,
                    material INTEGER NOT NULL,
                    packMinWeight REAL,
                    packMaxWeight REAL,
                    packMinWidth REAL,
                    packMaxWidth REAL,
                    packMinHeight REAL,
                    packMaxHeight REAL
                )
            """)
            
            # Ürün güncelleme geçmişi tablosu
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS update_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_timestamp TEXT NOT NULL,
                    product_count INTEGER NOT NULL,
                    source TEXT DEFAULT 'DIM-DB',
                    status TEXT DEFAULT 'success',
                    notes TEXT
                )
            """)
            
            conn.commit()
            print("✅ Veritabanı tabloları hazır")
    except sqlite3.Error as e:
        print(f"Veritabanı hatası (init_db): {e}")
        raise

def urunleri_kaydet(products):
    """
    DİM-DB'den gelen ürün listesini veritabanına kaydeder.
    Kayıt işleminden önce mevcut tüm ürünleri siler.
    """
    update_timestamp = turkiye_saati().strftime('%Y-%m-%d %H:%M:%S')
    product_count = len(products)
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # 1. Adım: Eski ürün sayısını al
            cursor.execute("SELECT COUNT(*) FROM products")
            eski_urun_sayisi = cursor.fetchone()[0]
            
            # 2. Adım: Eski verileri temizle
            print(f"📦 Eski ürün verileri temizleniyor... (Mevcut: {eski_urun_sayisi})")
            cursor.execute("DELETE FROM products")
            
            # 3. Adım: Yeni ürün listesini ekle
            print(f"📥 {product_count} adet yeni ürün veritabanına kaydediliyor...")
            for product in products:
                cursor.execute("""
                    INSERT INTO products (barcode, material, packMinWeight, packMaxWeight, packMinWidth, packMaxWidth, packMinHeight, packMaxHeight)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    product.get('barcode'),
                    product.get('material'),
                    product.get('packMinWeight'),
                    product.get('packMaxWeight'),
                    product.get('packMinWidth'),
                    product.get('packMaxWidth'),
                    product.get('packMinHeight'),
                    product.get('packMaxHeight')
                ))
            
            # 4. Adım: Güncelleme geçmişini kaydet
            cursor.execute("""
                INSERT INTO update_history (update_timestamp, product_count, source, status, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (
                update_timestamp,
                product_count,
                'DIM-DB',
                'success',
                f'Eski ürün: {eski_urun_sayisi}, Yeni ürün: {product_count}'
            ))
            
            conn.commit()
            print(f"✅ Ürünler başarıyla veritabanına kaydedildi.")
            print(f"📊 Güncelleme Kaydı: {update_timestamp} - {product_count} ürün")
            
    except sqlite3.Error as e:
        # Hata durumunda da kaydet
        try:
            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO update_history (update_timestamp, product_count, source, status, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    update_timestamp,
                    0,
                    'DIM-DB',
                    'error',
                    f'Hata: {str(e)}'
                ))
                conn.commit()
        except:
            pass
        
        print(f"❌ Veritabanı hatası (urunleri_kaydet): {e}")
        raise

def barkodu_dogrula(barcode):
    """
    Verilen barkodun veritabanında olup olmadığını kontrol eder.
    Varsa ürün bilgilerini, yoksa None döner.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row  # Sonuçları sözlük gibi almayı sağlar
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE barcode = ?", (barcode,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Veritabanı hatası (barkodu_dogrula): {e}")
        return None

def urun_sayisini_getir():
    """Veritabanındaki toplam ürün sayısını döner."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM products")
            count = cursor.fetchone()[0]
            return count
    except sqlite3.Error as e:
        print(f"Veritabanı hatası (urun_sayisini_getir): {e}")
        return 0

def guncelleme_gecmisini_getir(limit=10):
    """
    Son N adet ürün güncelleme geçmişini döner.
    
    Args:
        limit (int): Getirilecek kayıt sayısı (varsayılan: 10)
        
    Returns:
        list: Güncelleme kayıtları listesi
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM update_history 
                ORDER BY id DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        print(f"Veritabanı hatası (guncelleme_gecmisini_getir): {e}")
        return []

def son_guncelleme_bilgisi():
    """
    En son yapılan ürün güncellemesinin bilgisini döner.
    
    Returns:
        dict: Son güncelleme bilgisi veya None
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM update_history 
                WHERE status = 'success'
                ORDER BY id DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error as e:
        print(f"Veritabanı hatası (son_guncelleme_bilgisi): {e}")
        return None

def guncelleme_istatistikleri():
    """
    Ürün güncellemeleri hakkında istatistik bilgisi döner.
    
    Returns:
        dict: İstatistik bilgileri
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Toplam güncelleme sayısı
            cursor.execute("SELECT COUNT(*) FROM update_history")
            toplam_guncelleme = cursor.fetchone()[0]
            
            # Başarılı güncelleme sayısı
            cursor.execute("SELECT COUNT(*) FROM update_history WHERE status = 'success'")
            basarili_guncelleme = cursor.fetchone()[0]
            
            # Başarısız güncelleme sayısı
            cursor.execute("SELECT COUNT(*) FROM update_history WHERE status = 'error'")
            basarisiz_guncelleme = cursor.fetchone()[0]
            
            # Son güncelleme zamanı
            cursor.execute("SELECT update_timestamp FROM update_history ORDER BY id DESC LIMIT 1")
            son_guncelleme = cursor.fetchone()
            son_guncelleme_zamani = son_guncelleme[0] if son_guncelleme else "Hiç güncelleme yapılmadı"
            
            return {
                "toplam_guncelleme": toplam_guncelleme,
                "basarili_guncelleme": basarili_guncelleme,
                "basarisiz_guncelleme": basarisiz_guncelleme,
                "son_guncelleme_zamani": son_guncelleme_zamani,
                "mevcut_urun_sayisi": urun_sayisini_getir()
            }
    except sqlite3.Error as e:
        print(f"Veritabanı hatası (guncelleme_istatistikleri): {e}")
        return {}

