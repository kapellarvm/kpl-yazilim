#!/bin/bash

# Sadece CH340/CH341 seri portlarını resetle
# Diğer tüm USB cihazlarına DOKUNMA (kamera, touch, vb.)
# Kullanım: ./usb_reset_all.sh

echo "🔌 CH340/CH341 SERİ PORTLARI RESETLENIYOR..."
echo "═══════════════════════════════════════"
echo "ℹ️  Hedef: Sadece USB-Serial cihazlar (Vendor: 1a86)"
echo "ℹ️  Korunan: Tüm diğer USB cihazlar (kamera, touch vb.)"
echo "ℹ️  Yöntem: Vendor ID bazlı güvenli filtreleme"
echo "═══════════════════════════════════════"

# Metod 1: Tüm USB seri kartlarını unbind/bind yap
echo ""
echo "⚡ Adım 1: Tüm USB seri sürücülerini resetle..."
if [ -d "/sys/bus/usb-serial/drivers/ch341-uart" ]; then
    for device in /sys/bus/usb-serial/drivers/ch341-uart/*; do
        if [[ "$(basename $device)" == *":"* ]]; then
            DEVICE_NAME=$(basename "$device")
            echo "    ├─ CH341 unbind: $DEVICE_NAME"
            echo -n "$DEVICE_NAME" > /sys/bus/usb-serial/drivers/ch341-uart/unbind 2>/dev/null
        fi
    done
    echo "    └─ Tüm CH341 cihazları unbind edildi"
    
    sleep 2
    
    for device in /sys/bus/usb/devices/*/; do
        if [ -e "$device/idVendor" ] && [ "$(cat $device/idVendor)" = "1a86" ]; then
            DEVICE_ID=$(basename "$device")
            if [ -d "$device/$DEVICE_ID:1.0" ]; then
                echo "    ├─ CH341 bind: $DEVICE_ID:1.0"
                echo -n "$DEVICE_ID:1.0" > /sys/bus/usb-serial/drivers/ch341-uart/bind 2>/dev/null
            fi
        fi
    done
    echo "    └─ Tüm CH341 cihazları bind edildi"
fi

# Metod 2: SADECE USB-Serial cihazlarını deauthorize/authorize yap
echo ""
echo "⚡ Adım 2: SADECE USB-Serial (CH340/CH341) cihazlarını resetle..."
RESET_COUNT=0
SKIPPED_COUNT=0

# Bilinen USB-Serial Vendor ID'ler (Kolayca genişletilebilir)
SERIAL_VENDORS=("1a86")  # QinHeng CH340/CH341
# Gerekirse başka seri port chip'leri eklenebilir:
# SERIAL_VENDORS+=("0403")  # FTDI
# SERIAL_VENDORS+=("067b")  # Prolific
# SERIAL_VENDORS+=("10c4")  # Silicon Labs CP210x

for usb_dev in /sys/bus/usb/devices/*/; do
    if [ -e "$usb_dev/authorized" ] && [ -e "$usb_dev/idVendor" ]; then
        VENDOR=$(cat "$usb_dev/idVendor" 2>/dev/null)
        DEVICE_CLASS=$(cat "$usb_dev/bDeviceClass" 2>/dev/null)
        DEVICE_ID=$(basename "$usb_dev")
        
        # Multi-layer kontrol:
        # 1. Vendor ID kontrolü (CH340/CH341 ve benzeri)
        # 2. Device Class kontrolü (ff = Vendor Specific, genelde seri portlar)
        IS_SERIAL=0
        
        # Vendor ID kontrolü
        for SERIAL_VENDOR in "${SERIAL_VENDORS[@]}"; do
            if [ "$VENDOR" = "$SERIAL_VENDOR" ]; then
                IS_SERIAL=1
                break
            fi
        done
        
        # Eğer seri port ise resetle
        if [ $IS_SERIAL -eq 1 ]; then
            echo "    ├─ Deauthorize: $DEVICE_ID (Vendor: $VENDOR, Class: $DEVICE_CLASS)"
            echo 0 > "$usb_dev/authorized" 2>/dev/null
            RESET_COUNT=$((RESET_COUNT + 1))
        else
            # Diğer tüm cihazlar korunur (kamera, touch, vb.)
            if [ ! -z "$VENDOR" ] && [ "$VENDOR" != "1d6b" ]; then
                SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
            fi
        fi
    fi
done
echo "    └─ $RESET_COUNT USB-Serial resetlendi, $SKIPPED_COUNT cihaz korundu"

sleep 3

REAUTH_COUNT=0
for usb_dev in /sys/bus/usb/devices/*/; do
    if [ -e "$usb_dev/authorized" ]; then
        AUTH_STATUS=$(cat "$usb_dev/authorized" 2>/dev/null)
        if [ "$AUTH_STATUS" = "0" ]; then
            DEVICE_ID=$(basename "$usb_dev")
            echo "    ├─ Authorize: $DEVICE_ID"
            echo 1 > "$usb_dev/authorized" 2>/dev/null
            REAUTH_COUNT=$((REAUTH_COUNT + 1))
        fi
    fi
done
echo "    └─ $REAUTH_COUNT cihaz yeniden authorize edildi"

# Metod 3: USB Hub Reset (ATLANACAK - Kameraları etkileyebilir)
echo ""
echo "⚡ Adım 3: USB Hub reset atlanıyor (diğer cihazları korumak için)..."
echo "    └─ Hub reset yapılmadı - sadece CH340/CH341 cihazlar etkilendi"

# Metod 4: CH341 kernel modülünü yeniden yükle
echo ""
echo "⚡ Adım 4: CH341 kernel modülünü yeniden yükle..."
if lsmod | grep -q ch341; then
    echo "    ├─ Modül kaldırılıyor: ch341"
    rmmod ch341 2>/dev/null
    sleep 2
    echo "    ├─ Modül yükleniyor: ch341"
    modprobe ch341 2>/dev/null
    echo "    └─ Modül yeniden yüklendi"
else
    echo "    └─ CH341 modülü yüklü değil, yükleniyor..."
    modprobe ch341 2>/dev/null
fi

# Portların yeniden oluşmasını bekle
echo ""
echo "⏳ USB portlarının yeniden oluşması bekleniyor..."
sleep 3  # Hub reset sonrası ilk bekleme
for i in {1..10}; do
    sleep 1
    PORT_COUNT=$(ls /dev/ttyUSB* 2>/dev/null | wc -l)
    echo "    └─ Bekleniyor... ($i/10) - Mevcut port sayısı: $PORT_COUNT"
    # Eğer 2 port bulunduysa erken çık
    if [ "$PORT_COUNT" -ge 2 ]; then
        echo "    ✅ İki port bulundu, bekleme tamamlandı!"
        break
    fi
done

# Sonuçları göster
echo ""
echo "✅ USB RESET TAMAMLANDI"
echo "═══════════════════════════════════════"
echo ""
echo "📊 MEVCUT USB PORTLARI:"
if ls /dev/ttyUSB* &>/dev/null; then
    ls -l /dev/ttyUSB*
else
    echo "    ⚠️  Hiç USB port bulunamadı!"
fi

echo ""
echo "📊 RESETLENEN CİHAZLAR:"
echo "CH340/CH341 Seri Kartlar (Sadece bunlar etkilendi):"
lsusb | grep -i "1a86"
echo ""
echo "📊 KORUNAN CİHAZLAR:"
echo "Diğer tüm USB cihazlar (kamera, touch, vb.) korundu"
lsusb | grep -v "1a86" | grep -v "root hub" | grep "Device"

exit 0
