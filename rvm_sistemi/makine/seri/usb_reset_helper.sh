#!/bin/bash
# USB Port Reset Helper Script
# Kullanım: sudo ./usb_reset_helper.sh /dev/ttyUSB0

PORT=$1

if [ -z "$PORT" ]; then
    echo "Kullanım: $0 <port_adi>"
    echo "Örnek: $0 /dev/ttyUSB0"
    exit 1
fi

echo "USB Port Reset: $PORT"

# Method 1: Using usbreset if available
if command -v usbreset &> /dev/null; then
    echo "Method 1: usbreset kullanılıyor..."
    usbreset "$PORT"
    if [ $? -eq 0 ]; then
        echo "✓ usbreset başarılı"
        exit 0
    fi
fi

# Method 2: Find USB device path and reset via sysfs
echo "Method 2: sysfs üzerinden reset..."

# Get the USB device path
USB_PATH=$(readlink -f /sys/class/tty/$(basename $PORT)/device/../..)
if [ -n "$USB_PATH" ]; then
    BUSNUM=$(cat $USB_PATH/busnum 2>/dev/null)
    DEVNUM=$(cat $USB_PATH/devnum 2>/dev/null)
    
    if [ -n "$BUSNUM" ] && [ -n "$DEVNUM" ]; then
        echo "USB Device: Bus $BUSNUM Device $DEVNUM"
        
        # Reset using authorize
        echo "USB cihazı devre dışı bırakılıyor..."
        echo 0 > $USB_PATH/authorized
        sleep 1
        echo "USB cihazı etkinleştiriliyor..."
        echo 1 > $USB_PATH/authorized
        sleep 1
        
        echo "✓ USB reset tamamlandı"
        exit 0
    fi
fi

# Method 3: Driver unbind/bind
echo "Method 3: Driver unbind/bind..."

DRIVERS=("ftdi_sio" "ch341" "cp210x" "cdc_acm")
PORT_NAME=$(basename $PORT)

for DRIVER in "${DRIVERS[@]}"; do
    DRIVER_PATH="/sys/bus/usb-serial/drivers/$DRIVER"
    if [ -d "$DRIVER_PATH" ]; then
        echo "Driver bulundu: $DRIVER"
        
        # Unbind
        if [ -e "$DRIVER_PATH/$PORT_NAME" ]; then
            echo "Unbinding $PORT_NAME from $DRIVER..."
            echo -n "$PORT_NAME" > "$DRIVER_PATH/unbind"
            sleep 1
            
            # Bind
            echo "Binding $PORT_NAME to $DRIVER..."
            echo -n "$PORT_NAME" > "$DRIVER_PATH/bind"
            sleep 1
            
            echo "✓ Driver reset tamamlandı"
            exit 0
        fi
    fi
done

echo "⚠ USB reset başarısız oldu"
exit 1