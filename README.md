# RVM (Reverse Vending Machine) Sistemi

## 📌 Proje Özeti

Geri dönüşüm makineleri için geliştirilmiş kapsamlı Python sistemi. Kamera tabanlı görüntü işleme, motor kontrolü, sensör yönetimi ve DİM-DB entegrasyonu içerir.

---

## 🚀 Hızlı Başlangıç (Kurulu Sistemler İçin)

```bash
# Sistemi başlat
cd /home/sshuser/projects/kpl-yazilim
source .venv/bin/activate
python ana.py
```

---

## 📋 Sistem Gereksinimleri

- **İşletim Sistemi:** Ubuntu 20.04+ (veya benzeri Debian tabanlı dağıtım)
- **Python:** 3.8 veya üzeri
- **Display Server:** X11 (Openbox)
- **Donanım:**
  - USB portları (motor ve sensör kartları için CH340/CH341 USB-to-serial)
  - Touchscreen (Weida Hi-Tech CoolTouch)
  - USB Kamera (MV-CS004-10UC)
- **Ağ:** Sabit IP adresi (192.168.53.2)

---

# 🏗️ SIFIRDAN KURULUM REHBERİ

Bu bölüm **hiç kurulum yapılmamış** bir Ubuntu sistemine RVM yazılımının **tamamen sıfırdan** nasıl kurulacağını açıklar.

---

## 📦 ADIM 1: Temel Sistem Paketleri

```bash
# Paket listesini güncelle
sudo apt update

# Python ve temel araçlar
sudo apt install -y python3 python3-pip python3-venv git
```

---

## 🖥️ ADIM 2: Kiosk Mod Kurulumu (KRİTİK!)

RVM sistemi **kiosk mode** ile çalışır. Bu, bilgisayarın özel bir kullanıcı (`kioskuser`) ile otomatik başlaması ve tam ekran Chromium açması anlamına gelir.

### ⚠️ ÖNEMLİ: Bu Dosya Projede YOK!

`kiosk_setup.sh` dosyası **GIT reposunda YOKTUR**. Bu dosyayı **manuel olarak oluşturmanız** gerekir.

### 📝 kiosk_setup.sh Dosyasını Oluşturma

```bash
# Setup klasörünü oluştur
sudo mkdir -p /var/opt/setup
cd /var/opt/setup

# Dosyayı oluştur
sudo nano kiosk_setup.sh
```

**Aşağıdaki içeriği yapıştır:**

```bash
#!/bin/bash
set -e

### 1. Yeni kullanıcı oluştur (eğer yoksa)
echo "[+] Kullanıcı kontrol ediliyor: kioskuser"
if ! id "kioskuser" &>/dev/null; then
    echo "[+] Kullanıcı oluşturuluyor: kioskuser"
    sudo adduser --disabled-password --gecos "" kioskuser
    sudo usermod -aG video,audio,input kioskuser
else
    echo "[+] Kullanıcı zaten mevcut: kioskuser"
    sudo usermod -aG video,audio,input kioskuser
fi

### 2. Minimal gerekli paketler kuruluyor (Server için optimize edildi)
echo "[+] Minimal gerekli paketler yükleniyor..."
sudo apt update
sudo apt install -y --no-install-recommends \
    lightdm \
    openbox \
    chromium-browser \
    xserver-xorg \
    x11-xserver-utils \
    xinput \
    x11-utils

### 3. LightDM'i aktif hale getir
echo "[+] LightDM giriş yöneticisi ayarlanıyor..."
sudo debconf-set-selections <<< "lightdm shared/default-x-display-manager select lightdm"
sudo systemctl enable lightdm

### 4. LightDM otomatik giriş yapılandırması
echo "[+] LightDM otomatik giriş yapılandırması yapılıyor..."
sudo bash -c 'cat > /etc/lightdm/lightdm.conf' <<EOF
[Seat:*]
autologin-user=kioskuser
autologin-user-timeout=0
user-session=openbox
EOF

### 5. Openbox autostart dosyası oluşturuluyor
echo "[+] Openbox autostart ayarları yapılıyor..."
sudo -u kioskuser mkdir -p /home/kioskuser/.config/openbox

sudo -u kioskuser bash -c 'cat > /home/kioskuser/.config/openbox/autostart' <<'EOF'
# Ekran güç yönetimini devre dışı bırak
xset -dpms
xset s off
xset s noblank

# Ekran döndürme (mevcut ekranları kontrol et)
SCREEN=$(xrandr | grep " connected" | head -n1 | cut -d' ' -f1)
if [ ! -z "$SCREEN" ]; then
    xrandr --output "$SCREEN" --rotate left || true
fi

# Dokunmatik ekran ayarı (varsa)
TOUCH_ID=$(xinput list | grep -i 'touch' | grep -o 'id=[0-9]*' | cut -d= -f2 | head -n1)
if [ ! -z "$TOUCH_ID" ]; then
    xinput set-prop "$TOUCH_ID" "Coordinate Transformation Matrix" 0 -1 1 1 0 0 0 0 1
fi

# Chromium'u kiosk modda başlat
chromium-browser --noerrdialogs --kiosk --incognito --disable-pinch --overscroll-history-navigation=0 --touch-events=enabled http://192.168.53.1:5432
EOF

### 6. Touchscreen Portrait Rotation Setup
echo "[+] Touchscreen portrait rotation ayarları yapılıyor..."

# Rotation script'i proje klasöründen kopyala
ROTATION_SOURCE="/home/sshuser/projects/kpl-yazilim/scripts/rotate_touchscreen.sh"
sudo cp "$ROTATION_SOURCE" /home/kioskuser/rotate_touchscreen.sh
sudo chown kioskuser:kioskuser /home/kioskuser/rotate_touchscreen.sh
sudo chmod +x /home/kioskuser/rotate_touchscreen.sh

sudo chown -R kioskuser:kioskuser /home/kioskuser/.config
sudo chmod +x /home/kioskuser/.config/openbox/autostart

echo "[✓] Touchscreen rotation ayarları tamamlandı"
echo "[✓] Minimal kiosk sistemi kuruldu. Sistemi yeniden başlatabilirsiniz: sudo reboot"
```

**Kaydet ve çık:** `Ctrl+O`, `Enter`, `Ctrl+X`

### ▶️ kiosk_setup.sh'yi Çalıştırma

```bash
# Executable yap
sudo chmod +x /var/opt/setup/kiosk_setup.sh

# NOT: Henüz çalıştırmayın! Önce proje kurulmalı (Adım 3)
# Çünkü rotation script proje içinde: /home/sshuser/projects/kpl-yazilim/scripts/rotate_touchscreen.sh
```

---

## 📂 ADIM 3: Proje Kurulumu

```bash
# Proje klasörünü oluştur
sudo mkdir -p /home/sshuser/projects
cd /home/sshuser/projects

# Git reposunu clone et
git clone https://github.com/kapellarvm/kpl-yazilim.git
cd kpl-yazilim

# Python sanal ortamı oluştur (.venv dizini)
python3 -m venv .venv

# Sanal ortamı aktif et
source .venv/bin/activate

# Python bağımlılıklarını yükle
pip install -r requirements.txt
```

**⚠️ NOT:** Sanal ortam dizini `.venv` olmalıdır (venv değil)!

---

## 🎨 ADIM 4: Kiosk Setup'ı Çalıştır

Artık proje kuruldu, rotation script yerinde. Şimdi kiosk setup çalıştırılabilir:

```bash
sudo bash /var/opt/setup/kiosk_setup.sh
```

**Bu script şunları yapar:**
1. ✅ `kioskuser` kullanıcısı oluşturur
2. ✅ LightDM ve Openbox kurulumunu yapar
3. ✅ Otomatik giriş yapılandırır
4. ✅ Openbox autostart içinde ekran rotasyonu ayarlar
5. ✅ Touchscreen rotation script'ini kopyalar
6. ✅ Chromium kiosk mode ayarlar

---

## 🔐 ADIM 5: Sudo İzinlerinin Yapılandırılması

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

## ⚙️ ADIM 6: Systemd Servis Kurulumu

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

## 🧪 ADIM 7: İlk Reboot ve Test

```bash
# Sistemi yeniden başlat
sudo reboot
```

### Reboot Sonrası Beklenen Davranış:

1. ✅ Sistem `kioskuser` ile otomatik giriş yapar
2. ✅ Ekran **portrait mode** (dikey) başlar
3. ✅ Touchscreen koordinatları doğru çalışır
4. ✅ Chromium tam ekran açılır: `http://192.168.53.1:5432`
5. ✅ RVM backend servisi otomatik başlar (`192.168.53.2:4321`)

---

## 🔧 Motor Reconnect ve Touchscreen Rotation Mekanizması

### 🎯 Problem: Motor Kartı Şok Durumu

Motor kartı bazen "şok durumuna" girer (donanım feedback hatası) ve USB bus'tan kaybolur. Bu durumda:

1. ❌ Normal USB device reset **çalışmaz**
2. ✅ **USB hub power cycle** (deauthorize/authorize) gerekir

### ⚡ Çözüm: USB Hub Reset

`usb_reset_all.sh` scripti şunları yapar:

```bash
# USB3 hub'ı deauthorize et (güç kes)
echo 0 > /sys/bus/usb/devices/usb3/authorized

# 3 saniye bekle (kapasitörler boşalsın)
sleep 3

# USB3 hub'ı authorize et (güç ver)
echo 1 > /sys/bus/usb/devices/usb3/authorized
```

**Yan Etki:** Hub'a bağlı **tüm cihazlar** (motor, sensör, **touchscreen**, kamera) resetlenir.

### 🖱️ Touchscreen Rotation Problemi

USB hub reset sonrasında touchscreen **landscape mode** (yatay) açılır, ama fiziksel ekran **portrait** (dikey). Bu, dokunma koordinatlarını bozar.

### ✅ Çözüm: Otomatik Rotation Script

Hub reset sonrasında `usb_reset_all.sh` otomatik olarak rotation script çağırır:

```bash
# usb_reset_all.sh içinde (satır 149)
su - kioskuser -c "DISPLAY=:0 /home/kioskuser/rotate_touchscreen.sh" &
```

**Rotation script şunları yapar:**

1. **Ekranı döndür:** `xrandr --output $SCREEN --rotate left`
2. **Touchscreen koordinatlarını dönüştür:**
   ```bash
   xinput set-prop $TOUCH_ID "Coordinate Transformation Matrix" 0 -1 1 1 0 0 0 0 1
   ```

### 📋 Rotation Mekanizmaları

| Durum | Nasıl Çalışır | Dosya |
|-------|--------------|-------|
| **Sistem Başlangıcı** | Openbox autostart içinde xrandr + xinput | `/home/kioskuser/.config/openbox/autostart` |
| **Hub Reset Sonrası** | usb_reset_all.sh rotation script çağırıyor | `/home/kioskuser/rotate_touchscreen.sh` |

---

## 📁 Dosya Yapısı

```
kpl-yazilim/
├── 📄 README.md                    # Bu dosya
├── 📄 KONFIGURASYON.md             # Konfigürasyon kılavuzu
├── 📄 requirements.txt             # Python bağımlılıkları
├── 📄 ana.py                       # Ana sistem dosyası
├── 📄 .env                         # RVM konfigürasyonu (otomatik oluşturulur)
├── 📄 .env.example                 # Konfigürasyon şablonu
├── scripts/
│   └── rotate_touchscreen.sh      # Touchscreen rotation script
│   └── TEST_ROTATION.md            # Rotation test rehberi
└── rvm_sistemi/
    ├── dimdb/                      # DİM-DB entegrasyonu
    ├── makine/                     # Donanım kontrolü
    │   ├── goruntu/                # Kamera ve görüntü işleme
    │   ├── seri/                   # Seri port haberleşmesi
    │   │   ├── usb_reset_all.sh    # USB reset script (hub reset içerir!)
    │   │   ├── motor_karti.py      # Motor kartı kontrolü
    │   │   └── port_yonetici.py    # Port yönetimi
    │   └── modbus/                 # Modbus motor kontrolü
    ├── utils/                      # Yardımcı araçlar
    └── static/                     # Web arayüzü dosyaları
```

### ⚠️ PROJEDE OLMAYAN DOSYALAR (Manuel Oluşturulmalı):

| Dosya | Konum | Açıklama |
|-------|-------|----------|
| `kiosk_setup.sh` | `/var/opt/setup/` | Kiosk mode kurulum scripti |
| `rvm-backend.service` | `/etc/systemd/system/` | Systemd servis dosyası |
| `bakim-chromium` | `/etc/sudoers.d/` | Sudo izinleri |
| `lightdm.conf` | `/etc/lightdm/` | Otomatik giriş yapılandırması |

---

## 💻 Temel Özellikler

- **Otomatik Konfigürasyon**: İlk çalıştırmada RVM ID girişi
- **Kamera Sistemi**: Görüntü işleme ve ürün tanıma
- **Motor Kontrolü**: CH340/CH341 seri port ile motor yönetimi
- **Sensör Entegrasyonu**: Ağırlık ve diğer sensör verileri
- **DİM-DB Bağlantısı**: Merkezi veritabanı entegrasyonu
- **Motor Reconnect**: USB hub reset ile şok durumundan kurtarma
- **Touchscreen Rotation**: Hub reset sonrası otomatik rotation

---

## 🎮 Bakım Modu Kullanım Kılavuzu

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

### Sensör Kartı Sekmesi

| Kontrol | İşlevi |
|---------|--------|
| **LED Aç** | Sensör kartı LED'ini açar |
| **LED Kapat** | Sensör kartı LED'ini kapatır |
| **Ağırlık Ölç** | Load cell'den anlık ağırlık ölçümü alır ve ekranda gösterir |
| **Teach** | Sensör öğrenme modunu başlatır (gyro kalibrasyonu) |
| **Tare** | Sensör sıfırlama yapar (load cell'i sıfırlar) |

---

## 🔍 Sorun Giderme

### ❌ Problem: Sistem Başlangıcında Ekran Yatay

**Belirtiler:**
- Reboot sonrası ekran landscape (yatay) modda
- Touchscreen koordinatları yanlış

**Çözüm:**
```bash
# 1. Openbox autostart kontrolü
cat /home/kioskuser/.config/openbox/autostart
# xrandr ve xinput komutları olmalı

# 2. Manuel rotation test
DISPLAY=:0 xrandr --output $(xrandr | grep " connected" | head -n1 | cut -d' ' -f1) --rotate left

# 3. kiosk_setup.sh yeniden çalıştır
sudo bash /var/opt/setup/kiosk_setup.sh
sudo reboot
```

---

### ❌ Problem: Motor Reconnect Sonrası Touchscreen Çalışmıyor

**Belirtiler:**
- Motor reconnect başarılı ama dokunmatik yanıt vermiyor
- Ekran yatay durumda

**Çözüm:**
```bash
# 1. Rotation script yerinde mi?
ls -la /home/kioskuser/rotate_touchscreen.sh

# 2. Script executable mi?
chmod +x /home/kioskuser/rotate_touchscreen.sh

# 3. Manuel test
sudo -u kioskuser DISPLAY=:0 /home/kioskuser/rotate_touchscreen.sh

# 4. usb_reset_all.sh kontrolü
grep "rotate_touchscreen.sh" /home/sshuser/projects/kpl-yazilim/rvm_sistemi/makine/seri/usb_reset_all.sh
# Bu satır olmalı: su - kioskuser -c "DISPLAY=:0 /home/kioskuser/rotate_touchscreen.sh" &
```

---

### ❌ Problem: Motor Kartı Reconnect Olmuyor

**Belirtiler:**
- Motor şok durumuna giriyor
- Reconnect 300+ saniye sürüyor veya başarısız

**Çözüm:**
```bash
# 1. USB hub kontrolü
ls /sys/bus/usb/devices/usb3/authorized
# Dosya varsa hub reset çalışır

# 2. Manual hub reset test
echo 0 | sudo tee /sys/bus/usb/devices/usb3/authorized
sleep 3
echo 1 | sudo tee /sys/bus/usb/devices/usb3/authorized

# 3. Logları kontrol et
sudo journalctl -xeu rvm-backend.service -n 100 | grep -i "hub reset"
```

---

### ❌ Problem: Servis Başlamıyor (reboot sonrası)

**Çözüm:**
```bash
# 1. Servis loglarını kontrol et
sudo journalctl -xeu rvm-backend.service -n 100

# 2. Manuel başlat ve durumu gözle
sudo systemctl start rvm-backend.service
sudo systemctl status rvm-backend.service

# 3. X11 hazır mı kontrol et
xset -display :0 q
# Hata veriyorsa, X11 henüz hazır değil demektir
```

---

### ❌ Problem: Bakım Chromium Açılmıyor

**Çözüm:**
```bash
# 1. Sudo izinlerini doğrula
sudo visudo -c -f /etc/sudoers.d/bakim-chromium
# Çıktı "parsed OK" olmalı

# 2. Manuel Chromium testi
sudo -u kioskuser env DISPLAY=:0 XAUTHORITY=/home/kioskuser/.Xauthority \
  /snap/chromium/current/usr/lib/chromium-browser/chrome --version

# 3. Chromium process kontrolü
ps aux | grep chromium

# Sıkışmış process'leri temizle
sudo -u kioskuser pkill -f "chrome.*bakim"
```

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

USB Hub Reset Flow:
Motor Şok → usb_reset_all.sh → Hub Deauthorize → 3s → Hub Authorize
                                        ↓
                               Touchscreen Resetlenir
                                        ↓
                            rotation script çağrılır
                                        ↓
                         Ekran + Touchscreen Düzelir
```

---

## 🔧 Teknik Özellikler

- **Platform**: Ubuntu Linux
- **Python**: 3.9+
- **Display Server**: X11 (Openbox)
- **Kamera**: USB kamera (MV-CS004-10UC)
- **Motor Kontrolü**: CH340/CH341 USB-to-serial (Vendor ID: 1a86)
- **Sensör**: CH340/CH341 USB-to-serial
- **Touchscreen**: Weida Hi-Tech CoolTouch (Vendor ID: 2575)
- **Veritabanı**: SQLite (yerel) + DİM-DB (merkezi)
- **USB Hub Reset**: Bus 3 deauthorize/authorize mekanizması

---

## ⚡ Elektrik Kesintisi Tespiti

Sistem **bus voltage monitoring** ile elektrik kesintisini tespit eder:

### 🔧 Voltage Monitoring Özellikleri

- **Eşik Değeri**: 300V (ayarlanabilir)
- **Hysteresis**: 50V (300V altı kesinti, 350V üstü normal)
- **Tespit Süresi**: 2 ardışık düşük voltaj okuması (1 saniye)
- **Monitoring Interval**: 0.5 saniye
- **Veri Kaynağı**: Modbus DC bus voltage register'ı
- **Başlangıç Bypass**: 20 saniye (yanlış alarm önleme)

---

## 🚨 Önemli Notlar

### ✅ Kalıcı Yapılandırmalar
- ✅ Tüm `sudoers` kuralları kalıcıdır
- ✅ Systemd servisi reboot sonrası otomatik başlar
- ✅ Openbox otomatik başlatma her oturumda çalışır
- ✅ Hub reset sonrası touchscreen otomatik düzelir

### ⚠️ Güvenlik
- ⚠️ Bakım ekranında **şifre koruması yok**
- ⚠️ Yerel ağdan herkes erişebilir
- ⚠️ Bakım modu aktifken **tüm kontroller erişilebilir**

### 🎯 En İyi Pratikler
- ✅ Bakım işi bitince **mutlaka bakım modunu pasif edin**
- ✅ Sistem reset öncesi devam eden işlemleri **durdurun**
- ✅ Motor parametrelerini **dikkatli değiştirin**
- ✅ Düzenli olarak **sistem loglarını kontrol edin**
- ✅ kiosk_setup.sh dosyasını **yedekleyin** (projede yok!)

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
   lsusb | grep -E "(1a86|2575|2bdf)"
   ```

3. **Debug modda çalıştırın:**
   ```bash
   cd /home/sshuser/projects/kpl-yazilim
   source .venv/bin/activate
   python ana.py 2>&1 | tee full-debug.log
   ```

---

## 📝 Versiyon Bilgisi

- **Proje:** RVM Sistemi
- **Python:** 3.8+
- **FastAPI:** 0.100+
- **Chromium:** Latest (apt)
- **Sistem:** Ubuntu 20.04+
- **Son Güncelleme:** Ekim 2024
- **Kritik Özellikler:**
  - ✅ Motor kartı şok durumu kurtarma (USB hub reset)
  - ✅ Touchscreen rotation otomatiği (hub reset sonrası)
  - ✅ ESP32 boot handshake protokolü
  - ✅ Eski firmware uyumluluğu (fallback mode)

---

## 📚 Dokümantasyon

| Dosya | Açıklama |
|-------|----------|
| [README.md](README.md) | Ana sistem dokümantasyonu (bu dosya) |
| [KONFIGURASYON.md](KONFIGURASYON.md) | RVM konfigürasyon kılavuzu |
| [scripts/TEST_ROTATION.md](scripts/TEST_ROTATION.md) | Touchscreen rotation test rehberi |

---

**🎉 Başarılar dileriz!**

---

## ✨ Hızlı Başvuru Komutları

```bash
# Sistemi başlat
cd /home/sshuser/projects/kpl-yazilim && source .venv/bin/activate && python ana.py

# Servis durumu
sudo systemctl status rvm-backend.service

# Logları izle
sudo journalctl -xeu rvm-backend.service -f

# Manuel rotation test
sudo -u kioskuser DISPLAY=:0 /home/kioskuser/rotate_touchscreen.sh

# USB cihazları listele
lsusb | grep -E "(1a86|2575|2bdf)"

# Motor/sensör portları
ls -la /dev/ttyUSB*

# Kiosk setup yeniden çalıştır
sudo bash /var/opt/setup/kiosk_setup.sh

# Git güncellemeleri çek
cd /home/sshuser/projects/kpl-yazilim && git pull

# RVM ID kontrol
python -c "from rvm_sistemi.dimdb.config import config; print(f'RVM ID: {config.RVM_ID}')"
```
