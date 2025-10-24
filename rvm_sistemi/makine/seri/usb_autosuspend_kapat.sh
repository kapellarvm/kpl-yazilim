#!/bin/bash
# USB Autosuspend Kapatma Script'i
# Motor kartının sürekli kaybolmasını önlemek için

set -e

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >&2
}

log_info "USB Autosuspend kapatılıyor..."

# Yöntem 1: Tüm USB cihazları için autosuspend'i kapat
log_info "Yöntem 1: USB cihazları için autosuspend kapatılıyor..."
for device in /sys/bus/usb/devices/*/power/control; do
    if [ -f "$device" ]; then
        echo "on" | sudo tee "$device" > /dev/null 2>&1 || true
        log_info "  - $(dirname "$device" | xargs basename): autosuspend kapatıldı"
    fi
done

# Yöntem 2: USB autolevel'i kapat
log_info "Yöntem 2: USB autolevel kapatılıyor..."
for device in /sys/bus/usb/devices/*/power/autosuspend; do
    if [ -f "$device" ]; then
        echo "-1" | sudo tee "$device" > /dev/null 2>&1 || true
    fi
done

# Yöntem 3: CH340/CH341 için özel ayarlar
log_info "Yöntem 3: CH340/CH341 sürücüsü için özel ayarlar..."
for device in /sys/bus/usb/devices/*/; do
    if [ -f "$device/idVendor" ] && [ -f "$device/idProduct" ]; then
        vendor=$(cat "$device/idVendor" 2>/dev/null)
        product=$(cat "$device/idProduct" 2>/dev/null)
        
        # CH340/CH341 chip'i (Vendor ID: 1a86)
        if [ "$vendor" == "1a86" ]; then
            dev_name=$(basename "$device")
            log_info "  - CH340/CH341 bulundu: $dev_name"
            
            # Autosuspend kapat
            if [ -f "$device/power/control" ]; then
                echo "on" | sudo tee "$device/power/control" > /dev/null 2>&1
                log_success "    ✓ Autosuspend kapatıldı"
            fi
            
            # Autosuspend delay'i maksimuma çıkar
            if [ -f "$device/power/autosuspend_delay_ms" ]; then
                echo "2147483647" | sudo tee "$device/power/autosuspend_delay_ms" > /dev/null 2>&1
                log_success "    ✓ Autosuspend delay maksimuma çıkarıldı"
            fi
            
            # Persist ayarı
            if [ -f "$device/power/persist" ]; then
                echo "1" | sudo tee "$device/power/persist" > /dev/null 2>&1
                log_success "    ✓ Persist aktif edildi"
            fi
        fi
    fi
done

# Yöntem 4: Kernel parametresi kontrolü
log_info "Yöntem 4: Kernel parametreleri kontrol ediliyor..."
if ! grep -q "usbcore.autosuspend=-1" /proc/cmdline 2>/dev/null; then
    log_info "  ⚠️  GRUB'a 'usbcore.autosuspend=-1' eklenmemiş"
    log_info "  💡 Kalıcı çözüm için şu komutları çalıştırın:"
    log_info "     sudo sed -i 's/GRUB_CMDLINE_LINUX=\"/GRUB_CMDLINE_LINUX=\"usbcore.autosuspend=-1 /' /etc/default/grub"
    log_info "     sudo update-grub"
    log_info "     sudo reboot"
else
    log_success "  ✓ GRUB'da autosuspend zaten devre dışı"
fi

# Yöntem 5: udev kuralı oluştur
log_info "Yöntem 5: udev kuralı oluşturuluyor..."
UDEV_RULE="/etc/udev/rules.d/50-usb-no-autosuspend.rules"

if [ ! -f "$UDEV_RULE" ]; then
    sudo tee "$UDEV_RULE" > /dev/null <<'EOF'
# USB Autosuspend'i kapat (CH340/CH341 için)
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="1a86", ATTR{power/control}="on", ATTR{power/autosuspend_delay_ms}="2147483647"

# Tüm USB serial portları için autosuspend'i kapat
ACTION=="add", SUBSYSTEM=="usb", DRIVER=="ch341-uart", ATTR{power/control}="on"
ACTION=="add", SUBSYSTEM=="usb-serial", ATTR{power/control}="on"
EOF
    log_success "  ✓ udev kuralı oluşturuldu: $UDEV_RULE"
    
    # udev kurallarını yeniden yükle
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    log_success "  ✓ udev kuralları yeniden yüklendi"
else
    log_info "  ✓ udev kuralı zaten mevcut"
fi

log_success "USB Autosuspend başarıyla kapatıldı!"
log_info "Not: Tam kalıcı olmasi için sistemi yeniden başlatmanız önerilir."

exit 0

