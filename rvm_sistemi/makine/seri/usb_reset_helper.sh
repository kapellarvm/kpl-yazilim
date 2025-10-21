#!/bin/bash

# USB reset yardımcı script
# Kullanım: ./usb_reset_helper.sh /dev/ttyUSB0

if [ "$#" -ne 1 ]; then
    echo "Kullanım: $0 /dev/ttyUSBx"
    exit 1
fi

PORT=$1

# Port varlığını kontrol et
if [ ! -e "$PORT" ]; then
    echo "❌ Port bulunamadı: $PORT"
    exit 1
fi

# USB bilgilerini al
USB_PATH=$(readlink -f "$PORT")
if [[ ! "$USB_PATH" =~ /sys/devices/pci.* ]]; then
    echo "❌ USB yolu bulunamadı: $PORT"
    exit 1
fi

# USB bus ve device numaralarını al
BUS_DEVICE=$(echo "$USB_PATH" | grep -o 'usb[0-9]*/[0-9]*/[0-9]*-[0-9]*' | head -n1)
if [ -z "$BUS_DEVICE" ]; then
    echo "❌ USB bus/device bilgisi bulunamadı"
    exit 1
fi

# Bus ve device numaralarını ayır
BUS=$(echo "$BUS_DEVICE" | cut -d'/' -f1 | grep -o '[0-9]*')
DEVICE=$(echo "$BUS_DEVICE" | cut -d'/' -f3 | cut -d'-' -f1)

if [ -z "$BUS" ] || [ -z "$DEVICE" ]; then
    echo "❌ Bus/Device numaraları alınamadı"
    exit 1
fi

# USB device yolunu oluştur
USB_DEV="/dev/bus/usb/$BUS/$DEVICE"

if [ ! -e "$USB_DEV" ]; then
    echo "❌ USB device bulunamadı: $USB_DEV"
    exit 1
fi

# USB reset programını derle (eğer yoksa)
if [ ! -e "./usbreset" ]; then
    echo "🔧 USB reset programı derleniyor..."
    gcc usb_reset.c -o usbreset
    if [ $? -ne 0 ]; then
        echo "❌ Derleme hatası!"
        exit 1
    fi
fi

# Reset işlemini gerçekleştir
echo "🔄 USB reset başlatılıyor: $PORT"
echo "    └─ USB Device: $USB_DEV"

sudo ./usbreset "$USB_DEV"
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "✅ USB reset başarılı: $PORT"
    # Portun yeniden oluşmasını bekle
    sleep 2
    if [ -e "$PORT" ]; then
        echo "✅ Port yeniden hazır: $PORT"
    else
        echo "⚠️ Port henüz hazır değil, biraz daha bekleyin..."
        sleep 3
        if [ -e "$PORT" ]; then
            echo "✅ Port yeniden hazır: $PORT"
        else
            echo "❌ Port oluşturulamadı: $PORT"
            exit 1
        fi
    fi
else
    echo "❌ USB reset başarısız: $PORT"
    exit 1
fi

exit 0