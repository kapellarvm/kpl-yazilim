# RVM BAKIM VE TEMİZLİK EKRANLARI DOKÜMANI

## İÇİNDEKİLER

1. [GENEL BAKIŞ](#genel-bakış)
2. [ANA BAKIM PANELİ](#ana-bakım-paneli)
3. [TEMİZLİK PANELİ](#temizlik-paneli)
4. [UYKU MODU SİSTEMİ](#uyku-modu-sistemi)
5. [TEKNİK ÖZELLİKLER](#teknik-özellikler)
6. [KULLANIM KILAVUZU](#kullanım-kılavuzu)
7. [GÜVENLİK UYARILARI](#güvenlik-uyarıları)

---

## GENEL BAKIŞ

RVM (Reverse Vending Machine) sisteminin bakım ve temizlik işlemleri için özel olarak tasarlanmış üç farklı sistem bulunmaktadır. Bu sistemler, makinenin farklı bileşenlerini izleme, kontrol etme, bakım yapma ve enerji tasarrufu sağlama imkanı sunar.

### Sistem Özellikleri
- **Tamamen Offline Çalışma**: İnternet bağlantısı gerektirmez
- **Gerçek Zamanlı İzleme**: WebSocket teknolojisi ile canlı veri akışı
- **Modüler Yapı**: Her ekran farklı sistem bileşenlerine odaklanır
- **Responsive Tasarım**: Farklı ekran boyutlarına uyumlu

---

## ANA BAKIM PANELİ

### Genel Bilgiler
- **Dosya**: `rvm_sistemi/static/bakim.html`
- **Boyut**: 61KB HTML dosyası
- **Teknoloji**: HTML5, Tailwind CSS, JavaScript
- **Erişim**: Web tarayıcısı üzerinden

### Ana Özellikler

#### 1. Sistem Kontrolü
- **Bakım Modu Toggle**: Sistem bakım moduna alınabilir
- **Sistem Reset**: Acil durumlarda sistem sıfırlanabilir
- **URL Değiştirme**: Sistem konfigürasyonu değiştirilebilir
- **IP Adresi**: 192.168.53.2

#### 2. Sekme Yapısı

##### Sensör Kartı Sekmesi
**Giriş Sensörü (OPT 1009)**
- Optik sensör görselleştirmesi
- Teach ve Test fonksiyonları
- Gerilim, akım ve sağlık durumu izleme
- Işın kesme animasyonu

**Loadcell Ağırlık Sensörleri**
- Gerçek zamanlı ağırlık ölçümü
- Tare alma fonksiyonu
- Ağırlık ölçme butonu
- Gram cinsinden gösterim

**Konveyör LED Kontrolü**
- Parlaklık ayarı (0-100%)
- Açma/kapama kontrolü
- Gerilim ve akım izleme
- Sağlık durumu göstergesi

**Hazne Doluluk Sensörleri**
- Metal Hazne: Gri renkli gösterim
- Plastik Hazne: Mavi renkli gösterim
- Cam Hazne: Yeşil renkli gösterim
- Yüzdelik doluluk oranı

**AC Motorlar**
- Ezici Motor: Dişli animasyonu ile
- Kırıcı Motor: Dişli animasyonu ile
- Frekans, voltaj, akım, güç izleme
- İleri/Dur/Geri kontrol butonları
- Sıcaklık ve arıza durumu

##### Motor Kartı Sekmesi
**Konveyör Motor**
- Güç anahtarı toggle
- Konum ve alarm LED'leri
- Animasyonlu şişe taşıma
- Hız ayarı (0-100%)
- İleri/Dur/Geri kontrolü

**Yönlendirici Motor**
- Güç anahtarı toggle
- Kar tanesi animasyonu
- Plastik/Cam yönlendirme
- Hız ayarı ve kaydetme

**Klape Motor**
- Güç anahtarı toggle
- Dikey çubuk animasyonu
- Plastik/Metal yönlendirme
- Hız kontrolü

**Sensör Kontrolleri**
- Yönlendirici OPT Sensörü
- Yönlendirici İndüktif Sensör
- Klape İndüktif Sensör
- Teach ve Test fonksiyonları

**Kalibrasyon ve Test**
- Yönlendirici Motor Kalibrasyonu
- Klape Motor Kalibrasyonu
- Yönlendirici Sensör Kalibrasyonu
- Tümünü Kalibre Et butonu
- Senaryo Testleri (Plastik/Metal/Cam)

##### Güvenlik Kartı Sekmesi
**Kilit Kontrolleri**
- Üst Kapak Kilidi: Animasyonlu kilit görseli
- Alt Kapak Kilidi: Animasyonlu kilit görseli
- Kilit Aç/Kapat butonları
- Bus voltajı, şönt voltajı, akım izleme

**Emniyet Sensörleri**
- Üst Kapak Emniyet Sensörü
- Alt Kapak Emniyet Sensörü
- Manyetik sensör görselleştirmesi
- Test Et fonksiyonu

**Soğutma Fanı**
- Fan animasyonu
- Hız ayarı (0-100%)
- Açma/Kapama kontrolü
- Gerçek zamanlı döndürme efekti

**Güvenlik Rölesi**
- Röle durumu göstergesi
- Bypass kontrolü
- Reset fonksiyonu
- Kart resetleme

#### 3. Alt Bilgi Paneli
**Sistem Durumu**
- Çalışma durumu
- Çalışma süresi
- Son aktivite zamanı

**Sensör Değerleri**
- KPL04-PN-0001: Sıcaklık, Basınç, Nem
- KPL04-PN-0002: Sıcaklık, Basınç, Nem

**Bağlantı Durumu**
- Sensör Kartı bağlantısı
- Motor Kartı bağlantısı
- API Sunucusu durumu

**Hızlı Kontroller**
- Diagnostik
- Depoyu Boşalt
- Sistem Reset

**Etiket Bilgileri**
- Üretici: KAPELLA ELEKTROMEKANİK A.Ş.
- Marka: KapellaRVM
- Model: KPL04
- Seri No: 2025-KPL04-0001
- Teknik Özellikler: 220-230V, 15A, 3.3kW, 50-60Hz

---

## TEMİZLİK PANELİ

### Genel Bilgiler
- **Dosya**: `rvm_sistemi/static/temizlik.html`
- **Boyut**: 57KB HTML dosyası
- **Teknoloji**: HTML5, Tailwind CSS, JavaScript
- **Erişim**: Web tarayıcısı üzerinden

### Ana Özellikler

#### 1. Temizlik Modu Kontrolü
- **Toggle Switch**: Temizlik modunu aktif/pasif yapar
- **Durum Göstergesi**: AKTİF (yeşil) / PASİF (kırmızı)
- **API Entegrasyonu**: `/api/v1/temizlik-modu` endpoint'i

#### 2. Kilit Kontrolleri
**Üst Kapak Kilidi**
- Animasyonlu kilit ikonu
- Aç/Kapat butonları
- API çağrıları: `/api/v1/guvenlik/ust-kilit-ac` ve `/api/v1/guvenlik/ust-kilit-kapat`

**Alt Kapak Kilidi**
- Animasyonlu kilit ikonu
- Aç/Kapat butonları
- API çağrıları: `/api/v1/guvenlik/alt-kilit-ac` ve `/api/v1/guvenlik/alt-kilit-kapat`

#### 3. Sensör Kategorileri

##### Giriş ve Konveyör Sensörleri
- **Giriş Sensörü**: Bus V, Şönt V, Akım, Güç izleme
- **Konveyör LED**: Bus V, Şönt V, Akım, Güç izleme

##### Hazne Sensörleri
- **Plastik Hazne**: Doluluk oranı izleme
- **Metal Hazne**: Doluluk oranı izleme
- **Cam Hazne**: Doluluk oranı izleme

##### Yönlendirme Sensörleri
- **Yönlendirici Optik**: OPT sensör durumu
- **Yönlendirici İndüktif**: İndüktif sensör durumu
- **Klape İndüktif**: Klape sensör durumu

##### Emniyet Sensörleri
- **Üst Kapak Kilit**: Kilit durumu
- **Alt Kapak Kilit**: Kilit durumu
- **Üst Kapak Emniyet**: Emniyet sensörü
- **Alt Kapak Emniyet**: Emniyet sensörü

##### AC Motorlar
- **AC Ezici Motor**: Frekans, Voltaj, Akım, Güç, Bus V, Sıcaklık
- **AC Kırıcı Motor**: Frekans, Voltaj, Akım, Güç, Bus V, Sıcaklık

#### 4. WebSocket Entegrasyonu
- **Gerçek Zamanlı Veri**: `/api/v1/ws/temizlik` endpoint'i
- **Otomatik Yeniden Bağlanma**: Bağlantı kesildiğinde 5 saniye sonra tekrar bağlanır
- **Veri Tipleri**:
  - `modbus_update`: Motor verileri
  - `system_status`: Sistem durumu
  - `sensor_update`: Sensör verileri

#### 5. Sensör Durumu Göstergeleri
- **İyi**: Yeşil nokta
- **Uyarı**: Sarı nokta
- **Hata**: Kırmızı nokta

---

## UYKU MODU SİSTEMİ

### Genel Bilgiler
- **Dosya**: `rvm_sistemi/api/servisler/uyku_modu_servisi.py`
- **Teknoloji**: Python Threading, FastAPI
- **Boyut**: 200+ satır kod
- **Erişim**: API endpoint'leri ve otomatik sistem

### Ana Özellikler

#### 1. Otomatik Uyku Modu
- **15 Dakika Bekleme**: Oturum olmadığında otomatik uyku modu
- **Aktivite Takibi**: Son aktivite zamanını takip eder
- **Otomatik Çıkış**: Oturum başladığında uyku modundan çıkar
- **Thread Tabanlı**: Arka planda sürekli çalışan kontrol sistemi

#### 2. Enerji Tasarrufu Mesajları
**Uyku Moduna Geçiş Mesajları:**
- 💤 Uyku modu aktif - Enerji tüketimi minimuma düşürüldü
- 🔋 Motorlar güç tasarrufu modunda - İşlem bekliyor
- ⚡ LED'ler dim edildi - Görsel uyarılar pasif
- 🌙 Sensörler düşük güç modunda - Temel izleme aktif
- 💡 Sistem hazır durumda - Oturum başlatılması bekleniyor
- 🔌 AC motorlar güvenli modda - Bekleme konumunda
- 📊 Sistem performansı optimize edildi - Kaynak kullanımı azaltıldı
- 🛡️ Güvenlik sistemleri aktif - Kritik fonksiyonlar korunuyor

**Uyku Modundan Çıkış Mesajları:**
- 🌅 Uyku modundan çıkılıyor - Sistem aktifleştiriliyor
- ⚡ Enerji seviyeleri normale döndürülüyor
- 🔧 Motorlar hazırlık moduna geçiyor
- 💡 LED'ler tam parlaklığa ayarlanıyor
- 📡 Sensörler tam güç modunda aktifleştiriliyor
- 🎯 Sistem operasyonel duruma geçiyor
- ✅ Tüm bileşenler hazır - Oturum başlatılabilir

#### 3. İstatistik Takibi
- **Uyku Modu Sayısı**: Toplam uyku modu geçiş sayısı
- **Toplam Uyku Süresi**: Saat cinsinden toplam uyku süresi
- **Enerji Tasarrufu**: kWh cinsinden tasarruf miktarı
- **Ortalama Uyku Süresi**: Ortalama uyku modu süresi
- **Tasarruf Oranı**: Yüzdelik enerji tasarrufu

#### 4. API Endpoint'leri

##### Uyku Durumu
- `GET /api/v1/uyku/durum` - Uyku modu durumunu al
- `GET /api/v1/uyku/istatistikler` - Detaylı istatistikleri al
- `GET /api/v1/uyku/test` - Test endpoint'i

##### Uyku Kontrolü
- `POST /api/v1/uyku/aktivite` - Manuel aktivite kaydetme
- `POST /api/v1/uyku/zorla-uyku` - Zorla uyku moduna geç
- `POST /api/v1/uyku/uyku-cik` - Zorla uyku modundan çık
- `POST /api/v1/uyku/ayarlar` - Uyku ayarlarını güncelle

#### 5. Sistem Entegrasyonu
- **Otomatik Başlatma**: Sistem başladığında otomatik aktif
- **Oturum Entegrasyonu**: Oturum servisi ile entegre
- **Log Entegrasyonu**: Sistem loglarına entegre
- **Terminal Çıktısı**: Renkli terminal mesajları

#### 6. Konfigürasyon
- **Uyku Süresi**: 5-60 dakika arası ayarlanabilir (varsayılan: 15dk)
- **Kontrol Aralığı**: 30 saniyede bir kontrol
- **Enerji Tasarrufu**: Yaklaşık 2.5kW tasarruf hesaplaması
- **Thread Yönetimi**: Daemon thread ile güvenli çalışma

#### 7. Güvenlik Özellikleri
- **Thread Güvenliği**: Thread-safe operasyonlar
- **Hata Yönetimi**: Kapsamlı exception handling
- **Graceful Shutdown**: Güvenli sistem kapatma
- **Resource Management**: Kaynak yönetimi ve temizlik

#### 8. Test ve Debugging
- **Test Scripti**: `test_uyku_modu.py` ile kapsamlı test
- **Debug Endpoint**: Detaylı sistem durumu
- **Log Monitoring**: Kapsamlı log takibi
- **Performance Metrics**: Performans metrikleri

---

## TEKNİK ÖZELLİKLER

### Web Teknolojileri
- **HTML5**: Modern web standartları
- **Tailwind CSS**: Utility-first CSS framework
- **JavaScript ES6+**: Modern JavaScript özellikleri
- **WebSocket**: Gerçek zamanlı veri iletişimi
- **Fetch API**: Modern HTTP istekleri

### Dosya Yapısı
```
rvm_sistemi/
├── static/
│   ├── bakim.html          # Ana bakım paneli
│   ├── temizlik.html       # Temizlik paneli
│   ├── css/
│   │   ├── bakim.css       # Bakım paneli stilleri
│   │   └── temizlik.css    # Temizlik paneli stilleri
│   ├── js/
│   │   ├── bakim.js        # Bakım paneli JavaScript
│   │   └── tailwindcss.min.js # Tailwind CSS
│   └── fonts/
│       └── inter-font.css  # Inter font tanımları
```

### API Endpoints
- `GET /api/v1/sensor/durum` - Sensör durumları
- `POST /api/v1/temizlik-modu` - Temizlik modu aktif
- `POST /api/v1/temizlik-modundan-cik` - Temizlik modundan çık
- `POST /api/v1/guvenlik/ust-kilit-ac` - Üst kilit aç
- `POST /api/v1/guvenlik/ust-kilit-kapat` - Üst kilit kapat
- `POST /api/v1/guvenlik/alt-kilit-ac` - Alt kilit aç
- `POST /api/v1/guvenlik/alt-kilit-kapat` - Alt kilit kapat
- `WS /api/v1/ws/temizlik` - Temizlik WebSocket

---

## KULLANIM KILAVUZU

### Ana Bakım Paneli Kullanımı

#### 1. Erişim
- Web tarayıcısında `http://192.168.53.2/bakim` adresine gidin
- Sistem otomatik olarak bağlantı durumunu kontrol eder

#### 2. Bakım Modu
- Sağ üstteki "⚙ Bakım Modu" butonuna tıklayın
- Sistem bakım moduna geçer ve tüm kontroller aktif olur

#### 3. Sensör Kontrolü
- "Sensör Kartı" sekmesini seçin
- Her sensör için "Teach" ve "Test Et" butonlarını kullanın
- Sensör değerleri gerçek zamanlı olarak güncellenir

#### 4. Motor Kontrolü
- "Motor Kartı" sekmesini seçin
- Motor güç anahtarlarını açın/kapatın
- Hız ayarlarını yapın ve "Kaydet" butonuna basın
- İleri/Dur/Geri butonları ile motor kontrolü yapın

#### 5. Güvenlik Kontrolü
- "Güvenlik Kartı" sekmesini seçin
- Kilitleri açmak/kapatmak için butonları kullanın
- Emniyet sensörlerini test edin
- Fan hızını ayarlayın

### Temizlik Paneli Kullanımı

#### 1. Erişim
- Web tarayıcısında `http://192.168.53.2/temizlik` adresine gidin

#### 2. Temizlik Modu Aktifleştirme
- Sağ üstteki toggle switch'i açın
- Durum "AKTİF" olarak değişir
- Tüm kontroller aktif hale gelir

#### 3. Kilit Kontrolü
- "Kilit Kontrolleri" bölümünde
- Üst ve alt kapak kilitlerini açın/kapatın
- Animasyonlar ile durum değişimini izleyin

#### 4. Sensör İzleme
- Sensör kategorileri altında
- Tüm sensörlerin durumunu izleyin
- Renk kodlu durum göstergelerini takip edin

### Uyku Modu Sistemi Kullanımı

#### 1. Otomatik Çalışma
- Sistem başladığında otomatik olarak aktif olur
- 15 dakika boyunca oturum olmadığında uyku moduna geçer
- Oturum başladığında otomatik olarak uyku modundan çıkar

#### 2. API ile Kontrol
**Uyku Durumu Sorgulama:**
```bash
curl http://localhost:4321/api/v1/uyku/durum
```

**İstatistikleri Görüntüleme:**
```bash
curl http://localhost:4321/api/v1/uyku/istatistikler
```

**Manuel Aktivite Kaydetme:**
```bash
curl -X POST http://localhost:4321/api/v1/uyku/aktivite
```

**Uyku Ayarlarını Güncelleme:**
```bash
curl -X POST http://localhost:4321/api/v1/uyku/ayarlar \
  -H "Content-Type: application/json" \
  -d '{"uyku_suresi_dakika": 10}'
```

#### 3. Test Scripti Kullanımı
```bash
python test_uyku_modu.py
```

#### 4. Log Takibi
- Uyku modu geçişleri sistem loglarında kaydedilir
- Terminal çıktısında renkli mesajlar görünür
- Enerji tasarrufu istatistikleri tutulur

---

## GÜVENLİK UYARILARI

### ⚠️ ÖNEMLİ UYARILAR

#### 1. Bakım Modu
- Bakım modu aktifken sistem normal çalışmaz
- Sadece yetkili personel bakım modunu kullanmalıdır
- Bakım işlemi tamamlandıktan sonra bakım modundan çıkılmalıdır

#### 2. Kilit Kontrolü
- Kilitler açıkken sistem güvenliği tehlikeye girer
- Kilit açma işlemi sadece bakım/temizlik sırasında yapılmalıdır
- İşlem tamamlandıktan sonra kilitler mutlaka kapatılmalıdır

#### 3. Motor Kontrolü
- Motorlar çalışırken yakın durulmamalıdır
- Motor hız ayarları dikkatli yapılmalıdır
- Acil durumda "Dur" butonları kullanılmalıdır

#### 4. Elektriksel Güvenlik
- Sistem 220-230V AC ile çalışır
- Elektriksel işlemler sadece yetkili elektrikçiler tarafından yapılmalıdır
- Çalışma öncesi elektrik kesilmelidir

#### 5. Sensör Kalibrasyonu
- Sensör kalibrasyonu hassas işlemdir
- Yanlış kalibrasyon sistem arızasına neden olabilir
- Kalibrasyon sadece eğitimli personel tarafından yapılmalıdır

#### 6. Uyku Modu Güvenliği
- Uyku modu sırasında sistem tamamen pasif değildir
- Kritik güvenlik sistemleri aktif kalır
- Uyku modundan çıkış sırasında sistem kontrolleri yapılmalıdır
- Enerji tasarrufu hesaplamaları yaklaşık değerlerdir

### 🔒 GÜVENLİK PROSEDÜRLERİ

#### Bakım Öncesi
1. Sistem güç kaynağını kapatın
2. Bakım modunu aktif edin
3. Tüm kilitleri açın
4. Güvenlik ekipmanlarını takın

#### Bakım Sırasında
1. Sadece gerekli kontrolleri yapın
2. Sistem parametrelerini değiştirmeyin
3. Acil durumda sistem reset butonunu kullanın

#### Bakım Sonrası
1. Tüm kilitleri kapatın
2. Bakım modundan çıkın
3. Sistem testini yapın
4. Güç kaynağını açın

### 📞 ACİL DURUM İLETİŞİMİ

- **Teknik Destek**: +90 XXX XXX XX XX
- **Acil Servis**: +90 XXX XXX XX XX
- **Üretici**: KAPELLA ELEKTROMEKANİK A.Ş.

---

## SONUÇ

RVM sisteminin bakım ve temizlik ekranları, sistemin güvenli ve verimli çalışması için kritik öneme sahiptir. Bu doküman, sistem operatörlerinin ve bakım personelinin ekranları doğru ve güvenli bir şekilde kullanmasını sağlamak amacıyla hazırlanmıştır.

Tüm işlemler sırasında güvenlik prosedürlerine uyulması ve sadece yetkili personelin bu ekranları kullanması gerekmektedir.

---

**Doküman Versiyonu**: 1.0  
**Son Güncelleme**: 2025  
**Hazırlayan**: KAPELLA ELEKTROMEKANİK A.Ş.  
**Model**: KapellaRVM KPL04
