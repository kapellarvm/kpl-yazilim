#!/bin/bash
# Touchscreen Portrait Rotation Script
# RVM Sistemi için ekran ve dokunmatik rotasyonu

echo "🔄 Touchscreen portrait rotation başlatılıyor..."

# X11 display kontrolü
if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi

# Bekleme süresi (sistem tamamen açılması için)
sleep 3

# ============ EKRAN ROTASYONU ============
echo "📺 Ekran rotasyonu yapılıyor..."

# Tüm bağlı displayler için portrait rotasyon
for OUTPUT in $(xrandr | grep " connected" | awk '{print $1}'); do
    echo "  → Display: $OUTPUT"
    xrandr --output "$OUTPUT" --rotate left
done

# Alternatif: Belirli bir display için (örnekler)
# xrandr --output HDMI-1 --rotate left
# xrandr --output eDP-1 --rotate left
# xrandr --output DP-1 --rotate left

# ============ TOUCHSCREEN ROTASYONU ============
echo "👆 Touchscreen input rotasyonu yapılıyor..."

# Touchscreen cihazını bul
TOUCHSCREEN=$(xinput list | grep -i "touch" | grep -i "pointer" | head -1 | sed 's/.*id=\([0-9]*\).*/\1/')

if [ -z "$TOUCHSCREEN" ]; then
    echo "  ⚠️  Touchscreen bulunamadı"
    echo "  ℹ️  'xinput list' komutuyla manuel kontrol edin"
else
    echo "  → Touchscreen ID: $TOUCHSCREEN"

    # Portrait (left) transformation matrix
    # Matrix: [0 -1 1, 1 0 0, 0 0 1]
    xinput set-prop "$TOUCHSCREEN" --type=float "Coordinate Transformation Matrix" \
        0 -1 1 1 0 0 0 0 1

    echo "  ✅ Touchscreen rotasyonu tamamlandı"
fi

# ============ ALTERNATİF: İSME GÖRE ROTASYON ============
# Eğer touchscreen'in tam adını biliyorsanız:
# TOUCHSCREEN_NAME="Weida Hi-Tech CoolTouch System"
# xinput set-prop "$TOUCHSCREEN_NAME" --type=float "Coordinate Transformation Matrix" \
#     0 -1 1 1 0 0 0 0 1

echo "✅ Rotation script tamamlandı"
