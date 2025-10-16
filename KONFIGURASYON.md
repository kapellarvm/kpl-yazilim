# RVM Konfigürasyon Yönetimi

Bu proje, her RVM için farklı konfigürasyon değerleri gerektirdiğinden, profesyonel bir konfigürasyon yönetim sistemi kullanmaktadır.

## Kurulum

### 1. Environment Variables Kullanımı (Önerilen)

1. `.env.example` dosyasını `.env` olarak kopyalayın:
```bash
cp .env.example .env
```

2. `.env` dosyasını düzenleyerek kendi RVM'nize özel değerleri girin:
```env
RVM_ID=KRVM00010725
RVM_SECRET_KEY=your_secret_key_here
RVM_BASE_URL=http://192.168.53.1:5432
```

### 2. Sistem Environment Variables Kullanımı

Alternatif olarak, sistem seviyesinde environment variables tanımlayabilirsiniz:

```bash
export RVM_ID="KRVM00010725"
export RVM_SECRET_KEY="your_secret_key_here"
export RVM_BASE_URL="http://192.168.53.1:5432"
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

## Farklı RVM'ler İçin

Her RVM için ayrı bir `.env` dosyası oluşturun:

### RVM 1 (.env)
```env
RVM_ID=KRVM00010725
RVM_SECRET_KEY=rvm1_secret_key
RVM_BASE_URL=http://192.168.53.1:5432
```

### RVM 2 (.env)
```env
RVM_ID=KRVM00010925
RVM_SECRET_KEY=rvm2_secret_key
RVM_BASE_URL=http://192.168.53.2:5432
```

## Sorun Giderme

Eğer konfigürasyon yüklenmiyorsa:

1. `.env` dosyasının proje kök dizininde olduğundan emin olun
2. Dosya izinlerini kontrol edin
3. Environment variables'ların doğru tanımlandığını kontrol edin

## Geliştirici Notları

Konfigürasyon sistemi `rvm_sistemi/dimdb/config.py` dosyasında tanımlıdır. 
Yeni konfigürasyon değerleri eklemek için:

1. `RVMConfig` sınıfına yeni değişken ekleyin
2. `.env.example` dosyasını güncelleyin
3. Gerekirse doğrulama mantığı ekleyin
