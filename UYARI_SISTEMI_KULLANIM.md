# 🚨 Hızlı Uyarı Sistemi Kullanım Kılavuzu

## 📋 Genel Bakış

Hızlı uyarı sistemi, RVM sisteminde kullanıcılara hızlı ve etkili uyarılar göstermek için tasarlanmıştır. Bakım ekranı mantığına benzer şekilde çalışır ancak çok daha hızlıdır - belirtilen süre sonra otomatik olarak kapanır.

## 🎯 Özellikler

- ⚡ **Hızlı Açılış**: Uyarı ekranı anında açılır
- ⏰ **Otomatik Kapanma**: Belirtilen süre sonra otomatik kapanır (varsayılan: 2 saniye)
- 🎨 **Modern Tasarım**: Dikkat çekici ve kullanıcı dostu arayüz
- 📱 **Responsive**: Farklı ekran boyutlarına uyumlu
- 🔄 **Çoklu Uyarı**: Aynı anda birden fazla uyarı gösterilebilir
- ⌨️ **ESC ile Kapatma**: Kullanıcı ESC tuşu ile manuel kapatabilir

## 🚀 Kullanım

### 1. API ile Uyarı Gösterme

```bash
curl -X POST "http://192.168.53.2:4321/api/uyari-goster" \
  -H "Content-Type: application/json" \
  -d '{
    "mesaj": "Lütfen şişeyi alınız",
    "sure": 2
  }'
```

### 2. Python ile Uyarı Gösterme

```python
import requests

def uyari_goster(mesaj="Lütfen şişeyi alınız", sure=2):
    url = "http://192.168.53.2:4321/api/uyari-goster"
    data = {"mesaj": mesaj, "sure": sure}
    response = requests.post(url, json=data)
    return response.json()

# Kullanım örnekleri
uyari_goster()  # Varsayılan uyarı (2 saniye)
uyari_goster("Dikkat! Kapı açık", 3)  # Özel mesaj (3 saniye)
uyari_goster("İşlem tamamlandı", 1)  # Kısa uyarı (1 saniye)
```

### 3. Test Scripti ile Uyarı Gösterme

```bash
cd /home/sshuser/projects/kpl-yazilim
python3 uyari_test.py
```

## 📁 Dosya Yapısı

```
rvm_sistemi/
├── makine/
│   └── senaryolar/
│       └── uyari.py          # Uyarı senaryo mantığı
├── static/
│   └── uyari.html            # Uyarı ekranı HTML
└── dimdb/
    └── sunucu.py             # API endpoint'leri
```

## 🔧 API Endpoint'leri

### POST /api/uyari-goster

Uyarı gösterir.

**Request Body:**
```json
{
  "mesaj": "string",  // Uyarı mesajı (varsayılan: "Lütfen şişeyi alınız")
  "sure": integer     // Süre saniye cinsinden (varsayılan: 2)
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Uyarı gösterildi: Lütfen şişeyi alınız",
  "sure": 2
}
```

### GET /uyari

Uyarı ekranı HTML sayfasını döndürür.

**Query Parameters:**
- `mesaj`: Uyarı mesajı
- `sure`: Süre (saniye)

**Örnek:**
```
http://192.168.53.2:4321/uyari?mesaj=Test&sure=3
```

## 🎨 Uyarı Ekranı Özellikleri

### Görsel Özellikler
- **Arka Plan**: Kırmızı gradient (dikkat çekici)
- **İkon**: Büyük uyarı işareti (⚠️)
- **Animasyonlar**: 
  - Sayfa açılış animasyonu
  - İkon bounce animasyonu
  - Countdown pulse animasyonu
  - Progress bar animasyonu

### İşlevsel Özellikler
- **Countdown Timer**: Geri sayım göstergesi
- **Progress Bar**: Kalan süre göstergesi
- **Otomatik Kapanma**: Belirtilen süre sonra
- **Manuel Kapanma**: ESC tuşu ile
- **Responsive Tasarım**: Mobil uyumlu

## 🔄 Sistem Entegrasyonu

### Durum Makinesi Entegrasyonu

Uyarı sistemi, mevcut durum makinesine entegre edilmiştir:

```python
# Uyarı moduna geçiş
durum_makinesi.durum_degistir("uyari")

# Uyarı modundan çıkış
durum_makinesi.durum_degistir("oturum_yok")
```

### Chromium Entegrasyonu

Uyarı ekranı, bakım ekranı gibi ayrı bir Chromium penceresinde açılır:
- Kiosk modda tam ekran
- Otomatik kapanma
- Process yönetimi

## 🧪 Test Senaryoları

### 1. Temel Test
```bash
curl -X POST "http://192.168.53.2:4321/api/uyari-goster" \
  -H "Content-Type: application/json" \
  -d '{"mesaj": "Test uyarısı", "sure": 2}'
```

### 2. Uzun Uyarı Testi
```bash
curl -X POST "http://192.168.53.2:4321/api/uyari-goster" \
  -H "Content-Type: application/json" \
  -d '{"mesaj": "Uzun süreli uyarı", "sure": 10}'
```

### 3. Kısa Uyarı Testi
```bash
curl -X POST "http://192.168.53.2:4321/api/uyari-goster" \
  -H "Content-Type: application/json" \
  -d '{"mesaj": "Hızlı uyarı", "sure": 1}'
```

## 🚨 Kullanım Örnekleri

### 1. Şişe Alma Uyarısı
```python
uyari_goster("Lütfen şişeyi alınız", 2)
```

### 2. Kapı Açık Uyarısı
```python
uyari_goster("⚠️ Dikkat! Kapı açık", 3)
```

### 3. İşlem Tamamlandı Bildirimi
```python
uyari_goster("✅ İşlem tamamlandı", 1)
```

### 4. Zaman Doldu Uyarısı
```python
uyari_goster("⏰ Zaman doldu, lütfen işleminizi tamamlayın", 4)
```

## ⚠️ Önemli Notlar

### Güvenlik
- Uyarı sistemi şifre koruması olmadan çalışır
- Yerel ağdan herkes uyarı gönderebilir
- Production ortamında güvenlik önlemleri alınmalı

### Performans
- Uyarı sistemi çok hızlı çalışır
- Aynı anda birden fazla uyarı gösterilebilir
- Chromium process'leri otomatik temizlenir

### Sınırlamalar
- Maksimum uyarı süresi: 60 saniye (önerilen)
- Minimum uyarı süresi: 1 saniye
- Uyarı mesajı maksimum 200 karakter

## 🔧 Sorun Giderme

### Uyarı Gösterilmiyor
1. Sunucunun çalıştığını kontrol edin
2. Network bağlantısını kontrol edin
3. Chromium'un yüklü olduğunu kontrol edin

### Uyarı Kapanmıyor
1. Process'leri kontrol edin: `ps aux | grep chromium`
2. Manuel kapatma: `pkill -f chromium-browser.*4321/uyari`
3. Sunucuyu yeniden başlatın

### Görsel Sorunlar
1. HTML dosyasının doğru yerde olduğunu kontrol edin
2. CSS animasyonlarının desteklendiğini kontrol edin
3. Ekran çözünürlüğünü kontrol edin

## 📞 Destek

Herhangi bir sorun yaşarsanız:
1. Log dosyalarını kontrol edin
2. Sistem durumunu kontrol edin
3. Gerekirse sistemi yeniden başlatın

---

**Not**: Bu sistem RVM projesi için özel olarak geliştirilmiştir ve bakım ekranı mantığına dayanmaktadır.
