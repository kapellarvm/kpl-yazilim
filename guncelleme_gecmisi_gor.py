#!/usr/bin/env python3
"""
Ürün güncelleme geçmişini görüntüler
"""

from datetime import datetime
import argparse
import sys

from rvm_sistemi.veri_tabani import veritabani_yoneticisi

ICONS = {
    "success": "✅",
    "failure": "❌",
    "warning": "⚠️"
}

def format_timestamp(ts):
    if not ts:
        return "Yok"
    # Eğer already human-readable string varsa olduğu gibi dön
    if isinstance(ts, datetime):
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    # ISO format veya epoch
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        return datetime.fromisoformat(str(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)

def safe_call(fn, *args, default=None, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        print(f"{ICONS['warning']}  Hata: {fn.__name__} çağrılırken hata oluştu: {e}", file=sys.stderr)
        return default

def main():
    parser = argparse.ArgumentParser(description="Ürün güncelleme geçmişini görüntüler")
    parser.add_argument("--limit", "-n", type=int, default=20, help="Gösterilecek kayıt sayısı (varsayılan: 20)")
    parser.add_argument("--no-icons", action="store_true", help="Çıktıda ikonları gösterme")
    args = parser.parse_args()

    use_icons = not args.no_icons

    print("=" * 80)
    print("📊 ÜRÜN GÜNCELLEME GEÇMİŞİ")
    print("=" * 80)
    
    # İstatistikler
    print("\n📈 İSTATİSTİKLER:")
    print("-" * 80)
    istatistikler = safe_call(veritabani_yoneticisi.guncelleme_istatistikleri, default={})
    
    if istatistikler:
        print(f"  Toplam Güncelleme       : {istatistikler.get('toplam_guncelleme', 0)}")
        print(f"  Başarılı Güncelleme     : {istatistikler.get('basarili_guncelleme', 0)}")
        print(f"  Başarısız Güncelleme    : {istatistikler.get('basarisiz_guncelleme', 0)}")
        print(f"  Son Güncelleme Zamanı   : {format_timestamp(istatistikler.get('son_guncelleme_zamani'))}")
        print(f"  Mevcut Ürün Sayısı      : {istatistikler.get('mevcut_urun_sayisi', 0)}")
    else:
        print(f"  {ICONS['warning'] if use_icons else ''}  İstatistik bilgisi alınamadı")
    
    # Son güncelleme
    print("\n🕐 SON GÜNCELLEME:")
    print("-" * 80)
    son_guncelleme = safe_call(veritabani_yoneticisi.son_guncelleme_bilgisi, default=None)
    
    if son_guncelleme:
        print(f"  ID                      : {son_guncelleme.get('id')}")
        print(f"  Tarih/Saat              : {format_timestamp(son_guncelleme.get('update_timestamp'))}")
        print(f"  Ürün Sayısı             : {son_guncelleme.get('product_count')}")
        print(f"  Kaynak                  : {son_guncelleme.get('source')}")
        print(f"  Durum                   : {son_guncelleme.get('status')}")
        print(f"  Notlar                  : {son_guncelleme.get('notes')}")
    else:
        print(f"  {ICONS['warning'] if use_icons else ''}  Henüz güncelleme yapılmadı")
    
    # Tüm geçmiş (son N)
    print(f"\n📜 GÜNCELLEME GEÇMİŞİ (Son {args.limit}):")
    print("-" * 80)
    gecmis = safe_call(veritabani_yoneticisi.guncelleme_gecmisini_getir, args.limit, default=[])
    # Eğer veritabani fonksiyonu keyword arg alıyorsa, fallback:
    if gecmis is None:
        gecmis = safe_call(veritabani_yoneticisi.guncelleme_gecmisini_getir, limit=args.limit, default=[])
    
    if gecmis:
        header = f"{'ID':<5} {'Tarih/Saat':<19} {'Ürün':<6} {'Kaynak':<12} {'Durum':<10} {'Notlar'}"
        print(header)
        print("-" * 80)
        for kayit in gecmis:
            status = kayit.get('status') or ""
            icon = ICONS['success'] if status == 'success' else (ICONS['failure'] if status in ('failure', 'error') else '')
            icon_text = (icon + " ") if (use_icons and icon) else ""
            ts = format_timestamp(kayit.get('update_timestamp'))
            notes = (kayit.get('notes') or "")[:60]
            print(f"{str(kayit.get('id')):<5} {ts:<19} {str(kayit.get('product_count') or ''):<6} {str(kayit.get('source') or ''):<12} {icon_text}{status:<8} {notes}")
    else:
        print(f"  {ICONS['warning'] if use_icons else ''}  Henüz güncelleme geçmişi yok")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()#!/usr/bin/env python3
"""
Ürün güncelleme geçmişini görüntüler
"""

from rvm_sistemi.veri_tabani import veritabani_yoneticisi

def main():
    print("=" * 80)
    print("📊 ÜRÜN GÜNCELLEME GEÇMİŞİ")
    print("=" * 80)
    
    # İstatistikler
    print("\n📈 İSTATİSTİKLER:")
    print("-" * 80)
    istatistikler = veritabani_yoneticisi.guncelleme_istatistikleri()
    
    if istatistikler:
        print(f"  Toplam Güncelleme       : {istatistikler.get('toplam_guncelleme', 0)}")
        print(f"  Başarılı Güncelleme     : {istatistikler.get('basarili_guncelleme', 0)}")
        print(f"  Başarısız Güncelleme    : {istatistikler.get('basarisiz_guncelleme', 0)}")
        print(f"  Son Güncelleme Zamanı   : {istatistikler.get('son_guncelleme_zamani', 'Yok')}")
        print(f"  Mevcut Ürün Sayısı      : {istatistikler.get('mevcut_urun_sayisi', 0)}")
    else:
        print("  ⚠️  İstatistik bilgisi alınamadı")
    
    # Son güncelleme
    print("\n🕐 SON GÜNCELLEME:")
    print("-" * 80)
    son_guncelleme = veritabani_yoneticisi.son_guncelleme_bilgisi()
    
    if son_guncelleme:
        print(f"  ID                      : {son_guncelleme.get('id')}")
        print(f"  Tarih/Saat              : {son_guncelleme.get('update_timestamp')}")
        print(f"  Ürün Sayısı             : {son_guncelleme.get('product_count')}")
        print(f"  Kaynak                  : {son_guncelleme.get('source')}")
        print(f"  Durum                   : {son_guncelleme.get('status')}")
        print(f"  Notlar                  : {son_guncelleme.get('notes')}")
    else:
        print("  ⚠️  Henüz güncelleme yapılmadı")
    
    # Tüm geçmiş (son 20)
    print("\n📜 GÜNCELLEME GEÇMİŞİ (Son 20):")
    print("-" * 80)
    gecmis = veritabani_yoneticisi.guncelleme_gecmisini_getir(limit=20)
    
    if gecmis:
        print(f"{'ID':<5} {'Tarih/Saat':<20} {'Ürün':<8} {'Kaynak':<10} {'Durum':<10} {'Notlar'}")
        print("-" * 80)
        for kayit in gecmis:
            durum_icon = "✅" if kayit.get('status') == 'success' else "❌"
            print(f"{kayit.get('id'):<5} "
                  f"{kayit.get('update_timestamp'):<20} "
                  f"{kayit.get('product_count'):<8} "
                  f"{kayit.get('source'):<10} "
                  f"{durum_icon} {kayit.get('status'):<8} "
                  f"{kayit.get('notes', '')[:40]}")
    else:
        print("  ⚠️  Henüz güncelleme geçmişi yok")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()

