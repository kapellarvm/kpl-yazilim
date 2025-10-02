# RVM Bakım Sistemi

## Kurulum ve Konfigürasyon

### 1. Gerekli Paketlerin Yüklenmesi

```bash
# Sistem paketleri
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv

# Python sanal ortamı oluştur
cd /home/sshuser/projects/kpl-yazilim
python3 -m venv venv
source venv/bin/activate

# Python bağımlılıklarını yükle
pip install -r requirements.txt
```

### 2. Bakım Modu İçin Sistem Konfigürasyonu

Bakım modunun çalışması için aşağıdaki adımlar **mutlaka** yapılmalıdır:

#### 2.1. Sudo İzinlerinin Ayarlanması

```bash
# Root kullanıcısına geç
sudo su

# Chromium ve pkill için sudo izinleri ekle
echo 'sshuser ALL=(kioskuser) NOPASSWD: /snap/chromium/*/usr/lib/chromium-browser/chrome' | sudo tee /etc/sudoers.d/bakim-chromium > /dev/null
echo 'sshuser ALL=(kioskuser) NOPASSWD: /usr/bin/pkill' | sudo tee -a /etc/sudoers.d/bakim-chromium > /dev/null

# İzinleri ayarla
sudo chmod 440 /etc/sudoers.d/bakim-chromium

# Konfigürasyonu doğrula (çıktı "parsed OK" olmalı)
sudo visudo -c -f /etc/sudoers.d/bakim-chromium

# Root kullanıcısından çık
exit
```

**Önemli:** `visudo -c` komutu **"parsed OK"** çıktısı vermelidir. Hata verirse, dosyayı kontrol edin!

#### 2.2. Konfigürasyonu Test Etme

```bash
# Chromium çalıştırma iznini test et
sudo -u kioskuser /snap/chromium/current/usr/lib/chromium-browser/chrome --version

# pkill iznini test et
sudo -u kioskuser pkill --help
```

Her iki komut da hatasız çalışmalıdır.

## Uygulamayı Başlatma

```bash
cd /home/sshuser/projects/kpl-yazilim
source venv/bin/activate
python ana.py
```

## Bakım Modu Kullanımı

### Bakım Ekranı Erişimi

- **Bakım Ekranı URL:** `http://192.168.53.2:4321/bakim`
- **Ana Sistem URL:** `http://192.168.53.1:5432/`

Ağdaki herhangi bir bilgisayardan bakım ekranına erişebilirsiniz.

### Bakım Modu Özellikleri

1. **Bakım Modu Aktif:**
   - Bakım ekranında "🔧 Bakım Modu: Pasif" butonuna tıklayın
   - Yeni bir Chromium penceresi kiosk modda açılır
   - Bakım ekranı fullscreen gösterilir
   - Tüm butonlar ve kontroller aktif hale gelir
   - Sistem durumu "bakim" moduna geçer

2. **Bakım Modu Pasif:**
   - "🔧 Bakım Modu: Aktif" butonuna tıklayın
   - Bakım Chromium penceresi kapanır
   - Ana ekran tekrar görünür hale gelir
   - Butonlar ve kontroller pasif duruma geçer
   - Sistem durumu "oturum_yok" moduna döner

### Motor Kartı Kontrolleri

- **Motorları Aktif Et:** Motor kartını başlatır
- **Konveyör İleri/Dur:** Konveyör hareketini kontrol eder
- **Yönlendirici Plastik/Cam:** Yönlendiriciyi ilgili pozisyona getirir
- **Klape Aç/Kapat:** Klape mekanizmasını kontrol eder
- **Parametre Ayarları:** Motor hız parametrelerini ayarlar

### Sensör Kartı Kontrolleri

- **LED Aç/Kapat:** Sensör kartı LED'ini kontrol eder
- **Ağırlık Ölç:** Load cell'den ağırlık ölçümü alır
- **Teach:** Sensör öğrenme modunu başlatır
- **Tare:** Sensör sıfırlama yapar

### Sistem Reset

"Sistem Reset" butonu ile:
- Mevcut port bağlantıları kapatılır
- Portlar yeniden taranır
- Motor ve sensör kartları yeniden başlatılır

## Sorun Giderme

### Bakım Chromium Açılmıyorsa

```bash
# Sudo izinlerini kontrol et
sudo visudo -c -f /etc/sudoers.d/bakim-chromium

# kioskuser olarak Chromium'u manuel test et
sudo -u kioskuser env DISPLAY=:0 /snap/chromium/current/usr/lib/chromium-browser/chrome --version
```

### Port Bağlantı Sorunları

```bash
# Mevcut USB portları listele
ls -la /dev/ttyUSB* /dev/ttyACM*

# Port izinlerini kontrol et
sudo chmod 666 /dev/ttyUSB* /dev/ttyACM*
```

### Uygulamayı Loglarla Çalıştırma

```bash
cd /home/sshuser/projects/kpl-yazilim
source venv/bin/activate
python ana.py 2>&1 | tee ana.log
```

## Sistem Gereksinimleri

- Ubuntu 20.04+ veya benzeri Debian tabanlı dağıtım
- Python 3.8+
- Chromium browser (snap versiyonu)
- X11 display server (DISPLAY=:0)
- USB port erişimi (motor ve sensör kartları için)

## Notlar

- Tüm sudo konfigürasyonları **kalıcıdır** ve sistem yeniden başlatıldığında korunur
- Bakım modu aktifken sistem ana iş akışlarını durdurmaz
- Motor ve sensör kontrolleri yalnızca bakım modu aktifken çalışır
- Chromium kiosk modda çalıştığı için normal tarayıcı özellikleri (URL bar, vb.) görünmez
