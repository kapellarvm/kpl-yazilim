# RVM Konfigürasyon Yönetimi

Bu proje, her RVM için farklı konfigürasyon değerleri gerektirdiğinden, otomatik konfigürasyon sistemi kullanmaktadır.

## 🚀 Otomatik Kurulum

Sistem ilk çalıştırıldığında otomatik olarak kurulum başlar:

```bash
python ana.py
```

### Kurulum Süreci

1. **Sistem Başlatma**: Program çalıştırıldığında otomatik kontrol
2. **RVM ID Girişi**: Terminal üzerinden RVM ID girişi
3. **Doğrulama**: Girilen ID'nin doğrulanması
4. **Konfigürasyon Oluşturma**: `.env` dosyasının otomatik oluşturulması
5. **Sistem Başlatma**: Konfigürasyon yüklendikten sonra sistem başlar

### Örnek Kurulum Çıktısı

```
============================================================
🚀 RVM KURULUM SİSTEMİ
============================================================

📋 KURULUM BAŞLATILIYOR
──────────────────────────────
Lütfen kurulum yapınız!
──────────────────────────────

🔑 RVM ID GİRİŞİ
────────────────────

💻 RVM ID kodunu giriniz: KRVM00012345

📝 Girdiğiniz kod: KRVM00012345
──────────────────────────────
✅ Doğru mu? (y/n): y
🎯 RVM ID onaylandı: KRVM00012345
──────────────────────────────

📋 KURULUM ÖZETİ
────────────────────

🏷️  RVM ID: KRVM00012345
🔐 SECRET KEY: testkpl
🌐 BASE URL: http://192.168.53.1:5432

──────────────────────────────
🚀 Kurulumu tamamlamak istiyor musunuz? (y/n): y
──────────────────────────────

⚙️  KURULUM YAPILIYOR
─────────────────────────

📁 .env dosyası oluşturuluyor...
🔧 Konfigürasyon ayarlanıyor...
💾 Değerler kaydediliyor...

============================================================
✅ KURULUM TAMAMLANDI!
============================================================

🎯 RVM ID: KRVM00012345
📁 Konfigürasyon dosyası: .env
🚀 Sistem başlatılıyor...

──────────────────────────────
🎉 Hoş geldiniz! RVM sistemi hazır.
──────────────────────────────
============================================================
```

## Konfigürasyon Değerleri

| Değişken | Açıklama | Örnek |
|----------|----------|-------|
| `RVM_ID` | RVM'nin benzersiz kimliği | `KRVM00010725` |
| `RVM_SECRET_KEY` | DİM-DB ile güvenli iletişim için anahtar | `testkpl` |
| `RVM_BASE_URL` | DİM-DB sunucusunun adresi | `http://192.168.53.1:5432` |

## Güvenlik

- `.env` dosyası `.gitignore`'da tanımlıdır ve Git'e commit edilmez
- Hassas bilgileri asla kod içinde sabit olarak yazmayın
- Her RVM için farklı `.env` dosyası kullanın

## 🔄 Farklı RVM'ler İçin

Her RVM için otomatik kurulum yapılır:

### RVM 1
```bash
# İlk çalıştırma
python ana.py
# RVM ID: KRVM00010725 girin
# Sistem otomatik .env oluşturur
```

### RVM 2  
```bash
# İlk çalıştırma
python ana.py
# RVM ID: KRVM00010925 girin
# Sistem otomatik .env oluşturur
```

### Mevcut Konfigürasyonu Değiştirme

Eğer RVM ID'yi değiştirmek istiyorsanız:

```bash
# .env dosyasını silin
rm .env

# Sistemi yeniden başlatın
python ana.py
# Yeni RVM ID girin
```

## 🔧 Sorun Giderme

### Konfigürasyon Yüklenmiyor

```bash
# .env dosyasını kontrol edin
ls -la .env

# Dosya yoksa sistemi yeniden başlatın
rm -f .env
python ana.py
```

### RVM ID Değiştirme

```bash
# Mevcut konfigürasyonu silin
rm .env

# Sistemi yeniden başlatın
python ana.py
# Yeni RVM ID girin
```

### Sistem Testi

```bash
# Konfigürasyon değerlerini kontrol edin
python -c "from rvm_sistemi.dimdb.config import config; print(f'RVM ID: {config.RVM_ID}')"
```

## 👨‍💻 Geliştirici Notları

Konfigürasyon sistemi `rvm_sistemi/dimdb/config.py` dosyasında tanımlıdır.

### Yeni Konfigürasyon Değeri Ekleme

1. `RVMConfig` sınıfına yeni değişken ekleyin
2. `_create_env_file()` metodunu güncelleyin
3. Gerekirse doğrulama mantığı ekleyin

### Örnek Ekleme

```python
# config.py içinde
self.NEW_CONFIG = os.getenv('RVM_NEW_CONFIG', 'default_value')

# _create_env_file() içinde
content = f"""# RVM Konfigürasyonu
RVM_ID={self.RVM_ID}
RVM_SECRET_KEY={self.SECRET_KEY}
RVM_BASE_URL={self.BASE_URL}
RVM_NEW_CONFIG={self.NEW_CONFIG}
"""
```
