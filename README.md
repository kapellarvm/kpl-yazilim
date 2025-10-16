# RVM (Reverse Vending Machine) Sistemi

## 📌 Proje Özeti

Geri dönüşüm makineleri için geliştirilmiş kapsamlı Python sistemi. Kamera tabanlı görüntü işleme, motor kontrolü, sensör yönetimi ve DİM-DB entegrasyonu içerir.

## 🚀 Hızlı Başlangıç

```bash
# Sistemi başlat
cd /home/sshuser/projects/kpl-yazilim
source .venv/bin/activate
python ana.py
```

## 📁 Dosya Yapısı

```
kpl-yazilim/
├── 📄 README.md                    # Bu dosya
├── 📄 KONFIGURASYON.md             # Konfigürasyon kılavuzu
├── 📄 requirements.txt             # Python bağımlılıkları
├── 📄 ana.py                       # Ana sistem dosyası
├── 📄 .env                         # RVM konfigürasyonu (otomatik oluşturulur)
├── 📄 .env.example                 # Konfigürasyon şablonu
└── rvm_sistemi/
    ├── dimdb/                      # DİM-DB entegrasyonu
    │   ├── config.py               # Konfigürasyon yönetimi
    │   └── dimdb_istemcisi.py      # DİM-DB API istemcisi
    ├── makine/                     # Donanım kontrolü
    │   ├── goruntu/                # Kamera ve görüntü işleme
    │   ├── seri/                   # Seri port haberleşmesi
    │   └── modbus/                 # Modbus motor kontrolü
    ├── utils/                      # Yardımcı araçlar
    └── static/                     # Web arayüzü dosyaları
```

## 💻 Kullanım

### İlk Kurulum
Sistem ilk çalıştırıldığında otomatik kurulum başlar:

```bash
python ana.py
# Sistem otomatik olarak RVM ID girişi ister
# Konfigürasyon dosyası (.env) otomatik oluşturulur
```

### Temel Özellikler
- **Otomatik Konfigürasyon**: İlk çalıştırmada RVM ID girişi
- **Kamera Sistemi**: Görüntü işleme ve ürün tanıma
- **Motor Kontrolü**: Modbus RTU ile motor yönetimi
- **Sensör Entegrasyonu**: Ağırlık ve diğer sensör verileri
- **DİM-DB Bağlantısı**: Merkezi veritabanı entegrasyonu

## ✅ Sistem Durumu

- **Konfigürasyon**: ✅ Otomatik kurulum
- **Kamera Sistemi**: ✅ Çalışıyor
- **Motor Kontrolü**: ✅ Modbus RTU
- **Sensör Entegrasyonu**: ✅ Seri port
- **DİM-DB Bağlantısı**: ✅ HTTP API

## 📚 Dokümantasyon

| Dosya | Açıklama |
|-------|----------|
| [KONFIGURASYON.md](KONFIGURASYON.md) | RVM konfigürasyon kılavuzu |
| [README.md](README.md) | Ana sistem dokümantasyonu |

## 🔧 Teknik Özellikler

- **Platform**: Ubuntu Linux
- **Python**: 3.9+
- **Kamera**: USB kamera (MV-CS040-10UC)
- **Motor Kontrolü**: Modbus RTU
- **Sensör**: Seri port haberleşmesi
- **Veritabanı**: SQLite (yerel) + DİM-DB (merkezi)

## 📞 Destek

```bash
# Sistem kontrolü
python --version

# Sistemi başlat
python ana.py

# Konfigürasyon kontrolü
python -c "from rvm_sistemi.dimdb.config import config; print(f'RVM ID: {config.RVM_ID}')"
```

---

**Proje**: RVM Sistemi  
**Durum**: ✅ Production Ready  
**Versiyon**: 2.0.0  
**Tarih**: Ocak 2025

---

## 📋 Sistem Gereksinimleri

- **İşletim Sistemi:** Ubuntu 20.04+ (veya benzeri Debian tabanlı dağıtım)
- **Python:** 3.8 veya üzeri
- **Tarayıcı:** Chromium (snap versiyonu)
- **Display Server:** X11 (DISPLAY=:0)
- **Donanım:** USB portları (motor ve sensör kartları için)
- **Ağ:** Sabit IP adresi (192.168.53.2)

---

## 🚀 Adım 1: Sistem Paketlerinin Yüklenmesi

```bash
# Paket listesini güncelle
sudo apt-get update

# Gerekli sistem paketlerini yükle
sudo apt-get install -y python3 python3-pip python3-venv git chromium-browser
```

---

## 📦 Adım 2: Proje Kurulumu

```bash
# Proje dizinine git
cd /home/sshuser/projects/kpl-yazilim

# Python sanal ortamı oluştur (.venv dizini)
python3 -m venv .venv

# Sanal ortamı aktif et
source .venv/bin/activate

# Python bağımlılıklarını yükle
pip install -r requirements.txt
```

**Not:** Sanal ortam dizini `.venv` olmalıdır (venv değil)!

---

## 🔐 Adım 3: Sudo İzinlerinin Yapılandırılması

Bakım modunun çalışması için `sshuser`'ın `kioskuser` olarak Chromium çalıştırma izni gereklidir.

```bash
# Root kullanıcısına geç
sudo su

# Sudo kurallarını oluştur (Chromium, pkill ve env komutları için)
cat > /etc/sudoers.d/bakim-chromium << 'EOF'
sshuser ALL=(kioskuser) NOPASSWD: /snap/chromium/*/usr/lib/chromium-browser/chrome
sshuser ALL=(kioskuser) NOPASSWD: /usr/bin/pkill
sshuser ALL=(kioskuser) NOPASSWD: /usr/bin/env
EOF

# Dosya izinlerini ayarla
chmod 440 /etc/sudoers.d/bakim-chromium

# Konfigürasyonu doğrula (çıktı "parsed OK" olmalı)
visudo -c -f /etc/sudoers.d/bakim-chromium

# Root kullanıcısından çık
exit
```

### ✅ Test: Sudo İzinlerini Kontrol Et

```bash
# Chromium çalıştırma iznini test et
sudo -u kioskuser /snap/chromium/current/usr/lib/chromium-browser/chrome --version

# pkill iznini test et
sudo -u kioskuser pkill --help

# env iznini test et
sudo -u kioskuser env DISPLAY=:0 echo "OK"
```

Tüm komutlar hatasız çalışmalıdır!

---

## ⚙️ Adım 4: Systemd Servis Kurulumu

RVM sisteminin otomatik başlaması için systemd servisi oluşturalım.

```bash
# Systemd servis dosyasını oluştur
sudo tee /etc/systemd/system/rvm-backend.service > /dev/null << 'EOF'
[Unit]
Description=RVM Backend Service (Flask and Client)
After=network.target graphical.target multi-user.target
Wants=graphical.target

[Service]
Type=simple
User=sshuser
Group=sshuser
WorkingDirectory=/home/sshuser/projects/kpl-yazilim
Environment=DISPLAY=:0

# X11 hazır olana kadar bekle (max 30 saniye)
ExecStartPre=/bin/sh -c 'for i in $(seq 1 30); do xset -display :0 q >/dev/null 2>&1 && break || sleep 1; done'

ExecStart=/home/sshuser/projects/kpl-yazilim/.venv/bin/python ana.py
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
EOF

# Systemd konfigürasyonunu yeniden yükle
sudo systemctl daemon-reload

# Servisi etkinleştir (reboot sonrası otomatik başlatma)
sudo systemctl enable rvm-backend.service

# Servisi başlat
sudo systemctl start rvm-backend.service

# Servis durumunu kontrol et
sudo systemctl status rvm-backend.service
```

### ✅ Test: Servis Durumunu Kontrol Et

```bash
# Servis çalışıyor mu?
sudo systemctl is-active rvm-backend.service

# Servis etkin mi? (otomatik başlatma)
sudo systemctl is-enabled rvm-backend.service

# Son 50 satır log
sudo journalctl -xeu rvm-backend.service -n 50
```

**Beklenen çıktı:**
- `is-active` → `active`
- `is-enabled` → `enabled`

---

## 🖥️ Adım 5: Gnome Otomatik Başlatma (kioskuser için)

Ana ekranın (http://192.168.53.1:5432/) otomatik açılması için kioskuser'ın Gnome ayarlarında otomatik başlatma yapılandırılmalıdır.

### Manuel Yöntem (Gnome Ayarlar):

1. `kioskuser` olarak oturum aç
2. **Ayarlar** → **Uygulamalar** → **Başlangıç Uygulamaları**'na git
3. **Ekle** butonuna tıkla
4. Şu bilgileri gir:
   - **Ad:** RVM Kiosk
   - **Komut:** `/snap/chromium/current/usr/lib/chromium-browser/chrome --kiosk --noerrdialogs --disable-pinch --overscroll-history-navigation=0 http://192.168.53.1:5432/`
   - **Açıklama:** RVM Ana Ekran
5. **Ekle** butonuna tıkla

### Otomatik Yöntem (Terminal):

```bash
# kioskuser olarak çalıştır
sudo -u kioskuser mkdir -p /home/kioskuser/.config/autostart

sudo -u kioskuser tee /home/kioskuser/.config/autostart/rvm-kiosk.desktop > /dev/null << 'EOF'
[Desktop Entry]
Type=Application
Name=RVM Kiosk
Exec=/snap/chromium/current/usr/lib/chromium-browser/chrome --kiosk --noerrdialogs --disable-pinch --overscroll-history-navigation=0 http://192.168.53.1:5432/
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF
```

---

## 🧪 Adım 6: Sistem Testleri

### Test 1: Manuel Başlatma

```bash
# Ana programı manuel başlat
cd /home/sshuser/projects/kpl-yazilim
source .venv/bin/activate
python ana.py
```

**Beklenen davranış:**
- Port tarama başlamalı
- Motor ve sensör kartları bağlanmalı
- FastAPI sunucusu `http://192.168.53.2:4321` adresinde başlamalı

### Test 2: Bakım Ekranı Erişimi

1. Ağdaki başka bir bilgisayardan tarayıcı aç
2. `http://192.168.53.2:4321/bakim` adresine git
3. Bakım ekranı görünmelidir

### Test 3: Bakım Modu Aktif/Pasif

1. Bakım ekranında **"🔧 Bakım Modu: Pasif"** butonuna tıkla
2. RVM ekranında yeni Chromium penceresi açılmalı (kiosk modda)
3. Bakım ekranı fullscreen görünmeli
4. Tüm butonlar aktif hale gelmeli
5. **"🔧 Bakım Modu: Aktif"** butonuna tıkla
6. Bakım penceresi kapanmalı, ana ekran geri gelmeli

### Test 4: Reboot Sonrası Otomatik Başlatma

```bash
# Sistemi yeniden başlat
sudo reboot

# Reboot sonrası (oturum açtıktan sonra):

# 1. Ana Chromium otomatik açıldı mı? (http://192.168.53.1:5432/)
# 2. Servis otomatik başladı mı?
sudo systemctl status rvm-backend.service

# 3. Bakım modu çalışıyor mu?
# Ağdan bakım ekranına git ve "Bakım Modu: Pasif" butonuna bas
# RVM ekranında bakım ekranı açılmalı!
```

---

## 📚 Bakım Modu Kullanım Kılavuzu

### 🌐 Erişim Adresleri

- **Ana Sistem:** `http://192.168.53.1:5432/` (kioskuser otomatik açar)
- **Bakım Ekranı:** `http://192.168.53.2:4321/bakim` (ağdan erişim)

### 🔧 Bakım Modu Nasıl Çalışır?

#### 1️⃣ Bakım Modunu Aktif Etme

1. Ağdaki herhangi bir bilgisayardan `http://192.168.53.2:4321/bakim` adresine gidin
2. Ekranın sağ üstünde **"🔧 Bakım Modu: Pasif"** butonuna tıklayın
3. RVM ekranında **yeni bir Chromium penceresi** kiosk modda açılır
4. Bakım ekranı fullscreen gösterilir
5. Tüm kontrol butonları **aktif** hale gelir
6. Sistem durumu **"bakim"** moduna geçer

#### 2️⃣ Bakım Modunu Pasif Etme

1. **"🔧 Bakım Modu: Aktif"** butonuna tıklayın
2. Bakım Chromium penceresi **otomatik kapanır**
3. Ana ekran (`http://192.168.53.1:5432/`) **tekrar görünür** hale gelir
4. Kontrol butonları **pasif** duruma geçer
5. Sistem durumu **"oturum_yok"** moduna döner

---

## 🎮 Kontrol Paneli Özellikleri

### Motor Kartı Sekmesi

| Kontrol | İşlevi |
|---------|--------|
| **Motorları Aktif Et** | Motor kartını başlatır ve hazır hale getirir |
| **Konveyör İleri** | Konveyör bandını ileri yönde çalıştırır |
| **Konveyör Dur** | Konveyör bandını durdurur |
| **Yönlendirici Plastik** | Yönlendiriciyi plastik kutusu pozisyonuna getirir (700ms sonra konveyor durur) |
| **Yönlendirici Cam** | Yönlendiriciyi cam kutusu pozisyonuna getirir (700ms sonra konveyor durur) |
| **Klape Aç** | Klape mekanizmasını açar |
| **Klape Kapat** | Klape mekanizmasını kapatır |
| **Hız Parametreleri** | Motor hızlarını ayarlar (Konveyör, Yönlendirici, Klape için) |
| **Sistem Reset** | Tüm portları kapatır, yeniden tarar ve kartları yeniden başlatır |

**Görsel Animasyonlar:**
- Konveyör çalışırken → Yeşil animasyon
- Yönlendirici hareket ederken → Pozisyon göstergesi
- Klape durumu → Açık/Kapalı göstergesi

### Sensör Kartı Sekmesi

| Kontrol | İşlevi |
|---------|--------|
| **LED Aç** | Sensör kartı LED'ini açar |
| **LED Kapat** | Sensör kartı LED'ini kapatır |
| **Ağırlık Ölç** | Load cell'den anlık ağırlık ölçümü alır ve ekranda gösterir |
| **Teach** | Sensör öğrenme modunu başlatır (gyro kalibrasyonu) |
| **Tare** | Sensör sıfırlama yapar (load cell'i sıfırlar) |

**Canlı Veri Gösterimi:**
- Ağırlık verisi **her saniye** otomatik güncellenir
- Sensör durumu (bağlı/bağlı değil) gerçek zamanlı gösterilir

---

## 🔍 Sorun Giderme

### ❌ Problem: Servis Başlamıyor (reboot sonrası)

**Çözüm 1: Servis loglarını kontrol et**
```bash
sudo journalctl -xeu rvm-backend.service -n 100
```

**Çözüm 2: Manuel başlat ve durumu gözle**
```bash
sudo systemctl start rvm-backend.service
sudo systemctl status rvm-backend.service
```

**Çözüm 3: X11 hazır mı kontrol et**
```bash
xset -display :0 q
# Hata veriyorsa, X11 henüz hazır değil demektir
```

---

### ❌ Problem: Bakım Chromium Açılmıyor

**Çözüm 1: Sudo izinlerini doğrula**
```bash
sudo visudo -c -f /etc/sudoers.d/bakim-chromium
# Çıktı "parsed OK" olmalı
```

**Çözüm 2: Manuel Chromium testi**
```bash
sudo -u kioskuser env DISPLAY=:0 XAUTHORITY=/home/kioskuser/.Xauthority \
  /snap/chromium/current/usr/lib/chromium-browser/chrome --version
```

**Çözüm 3: Chromium process kontrolü**
```bash
# Açık Chromium process'lerini listele
ps aux | grep chromium

# Sıkışmış process'leri temizle
sudo -u kioskuser pkill -f "chrome.*bakim"
```

---

### ❌ Problem: Port Bağlantı Hataları

**Çözüm 1: USB portları kontrol et**
```bash
# Bağlı USB cihazları listele
ls -la /dev/ttyUSB* /dev/ttyACM*

# Port izinlerini düzelt
sudo chmod 666 /dev/ttyUSB* /dev/ttyACM*
```

**Çözüm 2: Sistem Reset kullan**
1. Bakım ekranına git
2. **"Sistem Reset"** butonuna tıkla
3. Sistem portları yeniden tarayacak ve bağlantıları kuracak

**Çözüm 3: Seri port logları**
```bash
# Ana programı verbose modda çalıştır
cd /home/sshuser/projects/kpl-yazilim
source .venv/bin/activate
python ana.py 2>&1 | tee debug.log
```

---

### ❌ Problem: Sensor Verileri Gelmiyor

**Belirtiler:**
- Ağırlık değeri sürekli "0" gösteriyor
- Sensör kartı "Bağlı Değil" durumunda

**Çözüm:**
```bash
# 1. Sensör kartı bağlantısını kontrol et
ls -la /dev/ttyUSB* /dev/ttyACM*

# 2. Ana programı yeniden başlat
sudo systemctl restart rvm-backend.service

# 3. Bakım ekranından "Sistem Reset" yap

# 4. Sensör callback'ini test et (logları izle)
sudo journalctl -xeu rvm-backend.service -f
# "a:VALUE" formatında gelen verileri göreceksiniz
```

---

### ❌ Problem: Yönlendirici Sonrası Konveyor Dönmeye Devam Ediyor

**Çözüm:**
Bu sorun düzeltildi! Yönlendirici komutlarından sonra 700ms bekleme ve otomatik konveyor durdurma eklendi.

Eğer sorun devam ederse:
```bash
# Motor kartı firmware versiyonunu kontrol et
# Gömülü sistemin komut işleme hızı yavaşsa, bekleme süresini artırın
```

`sunucu.py` dosyasında bu satırı bulun:
```python
await asyncio.sleep(0.7)  # 700ms
```
Değeri `1.0` veya `1.5` saniyeye çıkarabilirsiniz.

---

## 📊 Sistem Mimarisi

```
┌─────────────────────────────────────────────────────────────┐
│                    RVM Sistemi                              │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  kioskuser   │         │   sshuser    │         │   Motor/     │
│  (Chromium)  │◄────────│  (ana.py)    │◄────────│   Sensor     │
│ 192.168.53.1 │  HTTP   │  FastAPI     │  Serial │   Kartları   │
│    :5432     │         │ 192.168.53.2 │         │   (USB)      │
└──────────────┘         │    :4321     │         └──────────────┘
      ▲                  └──────────────┘
      │                        ▲
      │ Bakım Modu             │
      │ (Yeni Chromium)        │ HTTP API
      │                        │
      │                  ┌──────────────┐
      └──────────────────│  Ağdaki PC   │
         Kiosk Mode      │  (Bakım)     │
                         │  /bakim      │
                         └──────────────┘
```

---

## 🚨 Önemli Notlar

### ✅ Kalıcı Yapılandırmalar
- ✅ Tüm `sudoers` kuralları kalıcıdır
- ✅ Systemd servisi reboot sonrası otomatik başlar
- ✅ Gnome otomatik başlatma her oturumda çalışır

### ⚠️ Güvenlik
- ⚠️ Bakım ekranında **şifre koruması yok**
- ⚠️ Yerel ağdan herkes erişebilir
- ⚠️ Bakım modu aktifken **tüm kontroller erişilebilir**

### 🎯 En İyi Pratikler
- ✅ Bakım işi bitince **mutlaka bakım modunu pasif edin**
- ✅ Sistem reset öncesi devam eden işlemleri **durdurun**
- ✅ Motor parametrelerini **dikkatli değiştirin** (gömülü sistem limitlerini aşmayın)
- ✅ Düzenli olarak **sistem loglarını kontrol edin**

---

## 📞 Destek

Sorun yaşarsanız:

1. **Logları toplayın:**
   ```bash
   sudo journalctl -xeu rvm-backend.service -n 200 > rvm-logs.txt
   ```

2. **Sistem durumunu kontrol edin:**
   ```bash
   sudo systemctl status rvm-backend.service
   ps aux | grep chromium
   ls -la /dev/ttyUSB* /dev/ttyACM*
   ```

3. **Debug modda çalıştırın:**
   ```bash
   cd /home/sshuser/projects/kpl-yazilim
   source .venv/bin/activate
   python ana.py 2>&1 | tee full-debug.log
   ```

---

## 📝 Versiyon Bilgisi

- **Proje:** RVM Bakım Sistemi
- **Python:** 3.8+
- **FastAPI:** 0.100+
- **Chromium:** Snap (latest)
- **Sistem:** Ubuntu 20.04+

---

**🎉 Kurulum tamamlandı! Başarılar dileriz!**
