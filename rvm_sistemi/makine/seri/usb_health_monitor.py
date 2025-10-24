"""
USB Health Monitor - Touchscreen & Camera İzleme Servisi

Bu servis touchscreen ve kamera cihazlarının USB bağlantı sağlığını izler.
Device numarası değişimi tespit edildiğinde agresif USB reset tetikler.

Özellikler:
- 10 saniye periyot
- State-aware (reconnect sırasında bypass)
- İzole tasarım (sadece 2 değişkene bakar)
- CH340 muaf (kendi mekanizmaları var)
"""

import threading
import time
import subprocess
from typing import Optional
from rvm_sistemi.utils.logger import log_system, log_warning, log_error
from rvm_sistemi.makine.seri.system_state_manager import system_state, SystemState


class USBHealthMonitor:
    """
    USB cihaz sağlık izleme servisi

    Touchscreen ve kamera cihazlarının USB device numaralarını izler.
    Baseline'dan sapma tespit edildiğinde agresif USB reset tetikler.
    """

    def __init__(self):
        """USB Health Monitor başlat"""
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.check_interval = 10  # saniye

        log_system("USB Health Monitor oluşturuldu")

    def start(self):
        """İzleme servisini başlat"""
        if self.running:
            log_warning("USB Health Monitor zaten çalışıyor")
            return

        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="usb_health_monitor"
        )
        self.monitor_thread.start()
        log_system(f"✅ USB Health Monitor başlatıldı (periyot: {self.check_interval}s)")

    def stop(self):
        """İzleme servisini durdur"""
        if not self.running:
            return

        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=15)
        log_system("USB Health Monitor durduruldu")

    def _monitor_loop(self):
        """Ana izleme döngüsü"""
        log_system("🔍 [USB-HEALTH] İzleme döngüsü başladı")

        while self.running:
            try:
                # State kontrolü - Reconnect devam ediyorsa BYPASS
                current_state = system_state.get_system_state()
                if current_state != SystemState.NORMAL:
                    # Reconnect/reset devam ediyor, izleme yapma
                    # log_system(f"⏸️  [USB-HEALTH] Bypass - Sistem durumu: {current_state.value}")
                    time.sleep(self.check_interval)
                    continue

                # Cihaz kontrolü yap
                self._check_devices()

                # Bir sonraki kontrole kadar bekle
                time.sleep(self.check_interval)

            except Exception as e:
                log_error(f"USB Health Monitor döngü hatası: {e}")
                time.sleep(self.check_interval)

        log_system("🔍 [USB-HEALTH] İzleme döngüsü sonlandı")

    def _check_devices(self):
        """
        USB cihazları kontrol et

        Baseline ile mevcut durumu karşılaştırır.
        Değişim tespit edilirse agresif reset tetikler.
        """
        try:
            # Mevcut baseline'ı al
            baseline_touchscreen, baseline_camera = system_state.get_usb_baseline()

            # Baseline henüz set edilmemişse (ilk başlangıç)
            if baseline_touchscreen is None and baseline_camera is None:
                # İlk baseline'ı set et
                log_system("🔍 [USB-HEALTH] İlk baseline set ediliyor...")
                system_state.update_usb_baseline()
                return

            # Mevcut device numaralarını al
            current_touchscreen = self._get_device_number("2575:0001")
            current_camera = self._get_device_number("2bdf:0001")

            # Touchscreen kontrolü
            if current_touchscreen != baseline_touchscreen:
                log_warning(f"⚡ [USB-HEALTH] Touchscreen device değişimi tespit edildi!")
                log_warning(f"   Baseline: {baseline_touchscreen}")
                log_warning(f"   Mevcut:   {current_touchscreen}")
                self._trigger_recovery("touchscreen", baseline_touchscreen, current_touchscreen)
                return  # Recovery tetiklendi, döngüye geri dön

            # Camera kontrolü
            if current_camera != baseline_camera:
                log_warning(f"⚡ [USB-HEALTH] Camera device değişimi tespit edildi!")
                log_warning(f"   Baseline: {baseline_camera}")
                log_warning(f"   Mevcut:   {current_camera}")
                self._trigger_recovery("camera", baseline_camera, current_camera)
                return  # Recovery tetiklendi, döngüye geri dön

            # Hiçbir değişim yok - sessizce devam
            # log_system(f"✅ [USB-HEALTH] Cihazlar sağlıklı (T:{current_touchscreen}, C:{current_camera})")

        except Exception as e:
            log_error(f"USB cihaz kontrolü hatası: {e}")

    def _get_device_number(self, vendor_product: str) -> Optional[str]:
        """
        Belirli bir vendor:product ID için device numarasını al

        Args:
            vendor_product: Vendor:Product ID (örn: "2575:0001")

        Returns:
            Device numarası (örn: "075") veya None
        """
        try:
            result = subprocess.run(
                ["lsusb"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                return None

            # Parse et
            for line in result.stdout.strip().split('\n'):
                if vendor_product in line:
                    # Örnek: Bus 003 Device 075: ID 2575:0001 Weida Hi-Tech Co., Ltd. CoolTouch® System
                    parts = line.split()
                    if len(parts) >= 4 and parts[1] == "Bus" and parts[3] == "Device":
                        device_str = parts[4].rstrip(':')  # "075:"
                        return device_str

            return None  # Cihaz bulunamadı

        except Exception as e:
            log_error(f"Device numarası alınırken hata ({vendor_product}): {e}")
            return None

    def _trigger_recovery(self, device_name: str, baseline: Optional[str], current: Optional[str]):
        """
        USB recovery tetikle (agresif reset)

        Args:
            device_name: Cihaz adı (log için)
            baseline: Baseline device numarası
            current: Mevcut device numarası
        """
        log_warning(f"🚨 [USB-HEALTH] {device_name.upper()} reconnect tespit edildi!")
        log_warning(f"   Recovery başlatılıyor: {baseline} → {current}")

        # State tekrar kontrol et (race condition önleme)
        if system_state.get_system_state() != SystemState.NORMAL:
            log_warning("   Reset zaten devam ediyor, recovery iptal edildi")
            return

        # Agresif USB reset tetikle
        try:
            from rvm_sistemi.makine.seri.port_yonetici import PortYonetici

            port_manager = PortYonetici()
            success = port_manager.reset_all_usb_ports()

            if success:
                log_system(f"✅ [USB-HEALTH] {device_name.upper()} için USB reset tamamlandı")
                # Baseline güncellenecek (reset sonrası otomatik)
            else:
                log_error(f"❌ [USB-HEALTH] {device_name.upper()} için USB reset başarısız")

        except Exception as e:
            log_error(f"USB recovery tetikleme hatası ({device_name}): {e}")


# Global instance
usb_health_monitor = USBHealthMonitor()
