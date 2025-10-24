#!/bin/bash
# usbreset utility compile script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🔨 usbreset compile ediliyor..."

gcc -o usbreset usbreset.c

if [ $? -eq 0 ]; then
    echo "✅ usbreset başarıyla compile edildi"
    chmod +x usbreset
    echo "✅ Executable izinleri verildi"
    ls -lh usbreset
else
    echo "❌ Compile hatası!"
    exit 1
fi
