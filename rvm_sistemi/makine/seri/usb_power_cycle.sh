#!/bin/bash

# USB portun gücünü kapat/aç - EN AGRESIF YÖNTEM
# Kullanım: ./usb_power_cycle.sh /dev/ttyUSB0

if [ "$#" -ne 1 ]; then
    echo "Kullanım: $0 /dev/ttyUSBx"
    exit 1
fi

PORT=$1

echo "🔌 USB port TAM RESET başlatılıyor..."
echo "    └─ Port: $PORT"

# Metod 1: USB cihazı bul ve authorize=0 yap
echo "⚡ Metod 1: USB cihazı deauthorize ediliyor..."
for usb_dev in /sys/bus/usb/devices/*/; do
    if [ -e "$usb_dev/authorized" ]; then
        # Bu USB cihazının altında ttyUSB portları var mı kontrol et
        if find "$usb_dev" -name "ttyUSB*" 2>/dev/null | grep -q "$(basename $PORT)"; then
            echo 0 > "$usb_dev/authorized" 2>/dev/null
            echo "    └─ Cihaz deauthorize edildi: $(basename $usb_dev)"
            sleep 2
            echo 1 > "$usb_dev/authorized" 2>/dev/null
            echo "    └─ Cihaz yeniden authorize edildi"
            break
        fi
    fi
done

# Metod 2: CH341 sürücüsünü unbind/bind yap
echo "⚡ Metod 2: CH341 sürücüsü resetleniyor..."
if [ -d "/sys/bus/usb-serial/drivers/ch341-uart" ]; then
    for device in /sys/bus/usb-serial/drivers/ch341-uart/*; do
        if [[ "$(basename $device)" == *":"* ]]; then
            DEVICE_NAME=$(basename "$device")
            echo -n "$DEVICE_NAME" > /sys/bus/usb-serial/drivers/ch341-uart/unbind 2>/dev/null
            echo "    └─ Sürücü unbind: $DEVICE_NAME"
            sleep 1
            echo -n "$DEVICE_NAME" > /sys/bus/usb-serial/drivers/ch341-uart/bind 2>/dev/null
            echo "    └─ Sürücü bind: $DEVICE_NAME"
        fi
    done
fi

# Metod 3: USB cihazını doğrudan unbind/bind yap
echo "⚡ Metod 3: USB cihazı driver'dan resetleniyor..."
for usb_dev in /sys/bus/usb/devices/*/; do
    if find "$usb_dev" -name "ttyUSB*" 2>/dev/null | grep -q "$(basename $PORT)"; then
        DEVICE_ID=$(basename "$usb_dev")
        if [ -e "/sys/bus/usb/drivers/usb/$DEVICE_ID" ]; then
            echo -n "$DEVICE_ID" > /sys/bus/usb/drivers/usb/unbind 2>/dev/null
            echo "    └─ USB unbind: $DEVICE_ID"
            sleep 2
            echo -n "$DEVICE_ID" > /sys/bus/usb/drivers/usb/bind 2>/dev/null
            echo "    └─ USB bind: $DEVICE_ID"
        fi
    fi
done

# Metod 4: Kernel modülünü yeniden yükle
echo "⚡ Metod 4: CH341 kernel modülü yeniden yükleniyor..."
if lsmod | grep -q ch341; then
    rmmod ch341 2>/dev/null
    echo "    └─ Modül kaldırıldı: ch341"
    sleep 1
    modprobe ch341 2>/dev/null
    echo "    └─ Modül yeniden yüklendi: ch341"
fi

# Portun yeniden oluşmasını bekle
echo "⏳ Port yeniden oluşması bekleniyor..."
for i in {1..10}; do
    sleep 1
    if [ -e "$PORT" ]; then
        echo "✅ Port başarıyla yeniden oluşturuldu: $PORT ($i saniye)"
        exit 0
    fi
    echo "    └─ Bekleniyor... ($i/10)"
done

# Son kontrol
if [ -e "$PORT" ]; then
    echo "✅ Port başarıyla yeniden oluşturuldu: $PORT"
    exit 0
else
    echo "❌ Port yeniden oluşturulamadı: $PORT"
    echo "⚠️  Fiziksel olarak çıkarıp takmak gerekebilir"
    exit 1
fi