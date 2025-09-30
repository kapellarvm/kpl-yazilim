import sqlite3
import os

# Veritabanı dosyasının yolunu projenin ana dizini olarak ayarla
# Bu, betiğin nereden çalıştırıldığına bakılmaksızın dosyanın her zaman aynı yerde olmasını sağlar.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB_PATH = os.path.join(PROJECT_ROOT, "rvm_veritabani.db")

def init_db():
    """
    Veritabanını ve 'products' tablosunu oluşturur (eğer mevcut değilse).
    """
    try:
        print(f"Veritabanı kontrol ediliyor/oluşturuluyor: {DB_PATH}")
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
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
            conn.commit()
    except sqlite3.Error as e:
        print(f"Veritabanı hatası (init_db): {e}")
        raise

def urunleri_kaydet(products):
    """
    DİM-DB'den gelen ürün listesini veritabanına kaydeder.
    Kayıt işleminden önce mevcut tüm ürünleri siler.
    """
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # 1. Adım: Eski verileri temizle
            print("Eski ürün verileri temizleniyor...")
            cursor.execute("DELETE FROM products")
            
            # 2. Adım: Yeni ürün listesini ekle
            print(f"{len(products)} adet yeni ürün veritabanına kaydediliyor...")
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
            conn.commit()
            print("Ürünler başarıyla veritabanına kaydedildi.")
    except sqlite3.Error as e:
        print(f"Veritabanı hatası (urunleri_kaydet): {e}")
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

