#!/bin/bash

# Tüm USB portlarını resetle
# Kullanım: ./usb_reset_all.sh

echo "🔌 TÜM USB PORTLARI RESETLENIYOR..."
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

# Metod 2: Tüm USB cihazlarını deauthorize/authorize yap
echo ""
echo "⚡ Adım 2: Tüm USB cihazlarını deauthorize/authorize et..."
RESET_COUNT=0
for usb_dev in /sys/bus/usb/devices/*/; do
    if [ -e "$usb_dev/authorized" ] && [ -e "$usb_dev/idVendor" ]; then
        VENDOR=$(cat "$usb_dev/idVendor" 2>/dev/null)
        DEVICE_ID=$(basename "$usb_dev")
        
        # CH340/CH341 cihazları (1a86) veya tüm USB cihazları resetle
        if [ "$VENDOR" = "1a86" ] || [[ "$DEVICE_ID" == [0-9]-[0-9]* ]]; then
            echo "    ├─ Deauthorize: $DEVICE_ID (Vendor: $VENDOR)"
            echo 0 > "$usb_dev/authorized" 2>/dev/null
            RESET_COUNT=$((RESET_COUNT + 1))
        fi
    fi
done
echo "    └─ $RESET_COUNT cihaz deauthorize edildi"

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

# Metod 3: USB Hub Reset (EN ÖNEMLİ)
echo ""
echo "⚡ Adım 3: USB Hub'ları resetle..."
# Tüm USB hub'ları resetle
for hub in /sys/bus/usb/devices/usb*/authorized; do
    if [ -e "$hub" ]; then
        HUB_NAME=$(dirname "$hub" | xargs basename)
        echo "    ├─ $HUB_NAME hub deauthorize ediliyor..."
        echo 0 > "$hub" 2>/dev/null
        sleep 0.5
    fi
done

sleep 1

for hub in /sys/bus/usb/devices/usb*/authorized; do
    if [ -e "$hub" ]; then
        HUB_NAME=$(dirname "$hub" | xargs basename)
        echo "    ├─ $HUB_NAME hub authorize ediliyor..."
        echo 1 > "$hub" 2>/dev/null
        sleep 0.5
    fi
done
echo "    └─ Tüm USB hub'lar resetlendi"

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
echo "📊 USB CİHAZLARI:"
lsusb | grep -i "ch340\|ch341\|serial"

exit 0
