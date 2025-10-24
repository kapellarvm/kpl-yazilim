# Touchscreen Rotation Test Rehberi

## 1. Manuel Test (Hemen Test Et)

Terminal'den:
```bash
# Script'i çalıştır
/home/user/kpl-yazilim/scripts/rotate_touchscreen.sh
```

**Eğer çalışırsa:** Ekran ve dokunmatik rotasyonu hemen uygulanır ✅

**Eğer çalışmazsa:** Aşağıdaki debug adımlarına geç ⬇️

---

## 2. Debug: Touchscreen ve Display İsimlerini Bul

### Display İsimlerini Göster
```bash
xrandr | grep " connected"
```

**Örnek Çıktı:**
```
HDMI-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 477mm x 268mm
eDP-1 connected 1920x1080+1920+0 (normal left inverted right x axis y axis) 344mm x 194mm
```

→ Display isimleri: `HDMI-1`, `eDP-1`

### Touchscreen Cihazını Göster
```bash
xinput list
```

**Örnek Çıktı:**
```
⎡ Virtual core pointer                          id=2    [master pointer  (3)]
⎜   ↳ Virtual core XTEST pointer                id=4    [slave  pointer  (2)]
⎜   ↳ Weida Hi-Tech CoolTouch System            id=10   [slave  pointer  (2)]
⎜   ↳ SynPS/2 Synaptics TouchPad                id=12   [slave  pointer  (2)]
```

→ Touchscreen adı: `Weida Hi-Tech CoolTouch System`
→ Touchscreen ID: `10`

---

## 3. Script'i Özelleştir

Eğer otomatik bulunamıyorsa, `/home/user/kpl-yazilim/scripts/rotate_touchscreen.sh` dosyasını düzenle:

### Belirli Display İçin:
```bash
# Satır 20-25 civarını değiştir:
xrandr --output HDMI-1 --rotate left  # Kendi display adını yaz
```

### Belirli Touchscreen İçin:
```bash
# Satır 45-47 civarındaki yorum satırlarını aktif et:
TOUCHSCREEN_NAME="Weida Hi-Tech CoolTouch System"  # Kendi touchscreen adını yaz
xinput set-prop "$TOUCHSCREEN_NAME" --type=float "Coordinate Transformation Matrix" \
    0 -1 1 1 0 0 0 0 1
```

---

## 4. Farklı Rotasyon Yönleri

### Portrait (Left) - Varsayılan
```bash
xrandr --output HDMI-1 --rotate left
xinput set-prop 10 --type=float "Coordinate Transformation Matrix" 0 -1 1 1 0 0 0 0 1
```

### Portrait (Right)
```bash
xrandr --output HDMI-1 --rotate right
xinput set-prop 10 --type=float "Coordinate Transformation Matrix" 0 1 0 -1 0 1 0 0 1
```

### Landscape (Normal)
```bash
xrandr --output HDMI-1 --rotate normal
xinput set-prop 10 --type=float "Coordinate Transformation Matrix" 1 0 0 0 1 0 0 0 1
```

### Inverted (Ters)
```bash
xrandr --output HDMI-1 --rotate inverted
xinput set-prop 10 --type=float "Coordinate Transformation Matrix" -1 0 1 0 -1 1 0 0 1
```

---

## 5. Autostart Kontrolü

### Autostart Dosyası Var mı?
```bash
ls -la ~/.config/autostart/touchscreen-rotation.desktop
```

**Varsa:** Sistem restart'ında otomatik çalışacak ✅

### Manuel Autostart Ekle (Eğer eksikse)
```bash
mkdir -p ~/.config/autostart
cp /home/user/kpl-yazilim/scripts/touchscreen-rotation.desktop ~/.config/autostart/
```

---

## 6. Kiosk Mode İçin Alternatif (Eğer Autostart Çalışmazsa)

### LightDM Display Setup (Systemwide)
`/etc/lightdm/lightdm.conf` dosyasını düzenle:

```ini
[Seat:*]
display-setup-script=/home/user/kpl-yazilim/scripts/rotate_touchscreen.sh
```

### Systemd Service (Boot Time)
```bash
sudo nano /etc/systemd/system/touchscreen-rotation.service
```

Şunu ekle:
```ini
[Unit]
Description=Touchscreen Portrait Rotation
After=graphical.target

[Service]
Type=oneshot
User=user
Environment="DISPLAY=:0"
ExecStart=/home/user/kpl-yazilim/scripts/rotate_touchscreen.sh

[Install]
WantedBy=graphical.target
```

Aktif et:
```bash
sudo systemctl enable touchscreen-rotation.service
sudo systemctl start touchscreen-rotation.service
```

---

## 7. Sorun Giderme

### "xinput: command not found"
```bash
sudo apt install xinput x11-xserver-utils
```

### "xrandr: command not found"
```bash
sudo apt install x11-xserver-utils
```

### Ekran rotate oluyor ama touch yanlış yerde
→ Transformation matrix yanlış, debug adımlarında ID'yi doğru bul

### Hub reset sonrası touchscreen kayboluyorsa
→ Script'e `sleep 5` ekle, touchscreen'in boot olmasını bekle

---

## 8. Hızlı Komutlar

### Rotation Script Çalıştır
```bash
/home/user/kpl-yazilim/scripts/rotate_touchscreen.sh
```

### Rotasyonu Geri Al (Normal)
```bash
xrandr --output HDMI-1 --rotate normal
xinput set-prop 10 --type=float "Coordinate Transformation Matrix" 1 0 0 0 1 0 0 0 1
```

### Touchscreen Kalibrasyonu
```bash
xinput_calibrator
```

---

## Test Sonuçları

- [ ] Manuel script çalıştırma başarılı
- [ ] Ekran portrait'e döndü
- [ ] Touchscreen doğru koordinatlarda çalışıyor
- [ ] Sistem restart sonrası otomatik rotate oluyor
- [ ] Hub reset sonrası rotation korunuyor
