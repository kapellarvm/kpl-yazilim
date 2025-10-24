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

        # None tolerance tracking (geçici None'ları ignore etmek için)
        self.touchscreen_none_count = 0
        self.camera_none_count = 0
        self.max_none_tolerance = 2  # 2 kontrol döngüsü (20 saniye) bekle

        # İlk başlangıç gecikmesi
        self.startup_delay = 5  # Program başladıktan 5 saniye sonra başla
        self.startup_time = time.time()

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

        Önemli kontroller:
        1. İlk başlangıç gecikmesi (cihazlar tamamen boot olsun)
        2. Reconnection state kontrolü (motor/sensor reconnection sırasında bypass)
        3. None tolerance (geçici None'ları ignore et)
        """
        try:
            # ✅ Kontrol 1: İlk başlangıç gecikmesi
            elapsed = time.time() - self.startup_time
            if elapsed < self.startup_delay:
                # İlk 5 saniye sessizce bekle
                return

            # ✅ Kontrol 2: Reconnection state kontrolü
            # Motor veya sensor reconnecting durumundaysa BYPASS
            # Çünkü motor/sensor USB hub reset yaparken touchscreen değişimi NORMAL yan etki
            motor_reconnecting = system_state.is_card_reconnecting("motor")
            sensor_reconnecting = system_state.is_card_reconnecting("sensor")

            if motor_reconnecting or sensor_reconnecting:
                # Motor/sensor reconnection devam ediyor, touchscreen değişimi beklenir
                # USB Health Monitor müdahale etmemeli (sonsuz döngü riski!)
                return

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

            # ✅ Kontrol 3: None tolerance (geçici None'ları ignore et)
            # Hub reset sırasında cihazlar geçici kaybolabilir

            # Touchscreen kontrolü
            if current_touchscreen != baseline_touchscreen:
                # None durumu özel - geçici kaybolma olabilir
                if current_touchscreen is None:
                    self.touchscreen_none_count += 1
                    if self.touchscreen_none_count <= self.max_none_tolerance:
                        # Henüz tolerance limitinde, bekle
                        log_warning(f"⚠️  [USB-HEALTH] Touchscreen geçici kayboldu (None), bekleniyor... ({self.touchscreen_none_count}/{self.max_none_tolerance})")
                        return
                    # Tolerance limit aşıldı, gerçek sorun var
                    log_warning(f"⚡ [USB-HEALTH] Touchscreen device değişimi tespit edildi!")
                    log_warning(f"   Baseline: {baseline_touchscreen}")
                    log_warning(f"   Mevcut:   {current_touchscreen} (kalıcı kayıp)")
                else:
                    # Device numarası değişti (None değil)
                    log_warning(f"⚡ [USB-HEALTH] Touchscreen device değişimi tespit edildi!")
                    log_warning(f"   Baseline: {baseline_touchscreen}")
                    log_warning(f"   Mevcut:   {current_touchscreen}")

                self._trigger_recovery("touchscreen", baseline_touchscreen, current_touchscreen)
                return  # Recovery tetiklendi, döngüye geri dön
            else:
                # Touchscreen sağlıklı, none counter'ı sıfırla
                self.touchscreen_none_count = 0

            # Camera kontrolü
            if current_camera != baseline_camera:
                # None durumu özel - geçici kaybolma olabilir
                if current_camera is None:
                    self.camera_none_count += 1
                    if self.camera_none_count <= self.max_none_tolerance:
                        # Henüz tolerance limitinde, bekle
                        log_warning(f"⚠️  [USB-HEALTH] Camera geçici kayboldu (None), bekleniyor... ({self.camera_none_count}/{self.max_none_tolerance})")
                        return
                    # Tolerance limit aşıldı, gerçek sorun var
                    log_warning(f"⚡ [USB-HEALTH] Camera device değişimi tespit edildi!")
                    log_warning(f"   Baseline: {baseline_camera}")
                    log_warning(f"   Mevcut:   {current_camera} (kalıcı kayıp)")
                else:
                    # Device numarası değişti (None değil)
                    log_warning(f"⚡ [USB-HEALTH] Camera device değişimi tespit edildi!")
                    log_warning(f"   Baseline: {baseline_camera}")
                    log_warning(f"   Mevcut:   {current_camera}")

                self._trigger_recovery("camera", baseline_camera, current_camera)
                return  # Recovery tetiklendi, döngüye geri dön
            else:
                # Camera sağlıklı, none counter'ı sıfırla
                self.camera_none_count = 0

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
                    if len(parts) >= 4 and parts[0] == "Bus" and parts[2] == "Device":
                        device_str = parts[3].rstrip(':')  # "075:" -> "075"
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

        # ✅ Kritik: State tekrar kontrol et (race condition önleme)
        if system_state.get_system_state() != SystemState.NORMAL:
            log_warning("   Reset zaten devam ediyor, recovery iptal edildi")
            return

        # ✅ Kritik: Motor/sensor reconnection tekrar kontrol et
        # Recovery başlatmadan hemen önce tekrar kontrol (timing hassas)
        if system_state.is_card_reconnecting("motor") or system_state.is_card_reconnecting("sensor"):
            log_warning("   Motor/sensor reconnection başladı, USB Health Monitor recovery iptal edildi")
            log_warning("   Motor/sensor zaten hub reset yapacak, touchscreen değişimi normal yan etki")
            return

        # Agresif USB reset tetikle (direkt script çağır - motor/sensor reconnection ile aynı yöntem)
        try:
            import os
            script_path = os.path.join(
                os.path.dirname(__file__),
                "usb_reset_ch340.sh"
            )

            if os.path.exists(script_path):
                log_system(f"🔧 [USB-HEALTH] {device_name.upper()} için USB reset başlatılıyor...")
                result = subprocess.run(
                    ['sudo', script_path],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    log_system(f"✅ [USB-HEALTH] {device_name.upper()} için USB reset tamamlandı")

                    # ✅ KRİTİK: Recovery sonrası baseline güncelle (sonsuz döngü önleme)
                    # USB reset touchscreen/camera device numaralarını değiştirmiş olabilir
                    # Baseline'ı hemen güncelle ki bir sonraki kontrol döngüsünde tekrar tetikleme
                    time.sleep(2)  # USB cihazlarının re-enumerate olması için kısa bekleme
                    log_system(f"🔄 [USB-HEALTH] Baseline güncelleniyor (recovery sonrası)...")
                    system_state.update_usb_baseline()

                    # Counter'ları sıfırla
                    self.touchscreen_none_count = 0
                    self.camera_none_count = 0

                    log_system(f"✅ [USB-HEALTH] Recovery tamamlandı - Baseline güncellendi")
                else:
                    log_error(f"❌ [USB-HEALTH] {device_name.upper()} için USB reset başarısız: {result.stderr}")
            else:
                log_error(f"❌ [USB-HEALTH] USB reset script bulunamadı: {script_path}")

        except Exception as e:
            log_error(f"USB recovery tetikleme hatası ({device_name}): {e}")


# Global instance
usb_health_monitor = USBHealthMonitor()
