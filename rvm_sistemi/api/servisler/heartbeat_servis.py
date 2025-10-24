"""
Heartbeat Servisleri
DİM-DB'ye periyodik durum bildirimi - Optimized Async Version
"""

import asyncio
import time
from ...dimdb import dimdb_istemcisi
from ...utils.logger import log_dimdb, log_error, log_system, log_success, log_warning, log_heartbeat
from ...utils.terminal import ok, warn, err, status


class HeartbeatServis:
    """Optimized Heartbeat yönetimi servis sınıfı"""
    
    def __init__(self, heartbeat_interval: int = 60):
        self.heartbeat_task = None
        self.heartbeat_interval = heartbeat_interval
        self.is_running = False
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self.total_heartbeats = 0
        self.successful_heartbeats = 0
        self.failed_heartbeats = 0
        self.start_time = None

    async def start_heartbeat(self) -> None:
        """Heartbeat sistemini başlatır"""
        if self.is_running:
            warn("DİM-DB", "Heartbeat sistemi zaten çalışıyor")
            log_warning("Heartbeat sistemi zaten çalışıyor - başlatma atlandı")
            return
            
        self.is_running = True
        self.start_time = time.time()
        self.total_heartbeats = 0
        self.successful_heartbeats = 0
        self.failed_heartbeats = 0
        self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())
        ok("DİM-DB", "Heartbeat sistemi başlatıldı")
        log_system(f"Heartbeat sistemi başlatıldı - Interval: {self.heartbeat_interval}s, Max Errors: {self.max_consecutive_errors}")
        log_heartbeat(f"Servis başlatıldı - Task ID: {id(self.heartbeat_task)}, Başlangıç zamanı: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    async def stop_heartbeat(self) -> None:
        """Heartbeat sistemini durdurur"""
        if not self.is_running:
            warn("DİM-DB", "Heartbeat sistemi zaten durmuş")
            log_warning("Heartbeat sistemi zaten durmuş - durdurma atlandı")
            return
            
        self.is_running = False
        log_system("Heartbeat sistemi durduruluyor...")
        
        if self.heartbeat_task:
            task_id = id(self.heartbeat_task)
            self.heartbeat_task.cancel()
            log_heartbeat(f"Task iptal edildi - Task ID: {task_id}")
            
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                log_heartbeat("Task başarıyla iptal edildi")
            except Exception as e:
                log_error(f"Heartbeat task iptal edilirken hata: {e}")
            
            self.heartbeat_task = None
        
        status("DİM-DB", "Heartbeat sistemi durduruldu", level="stop")
        
        # Final istatistikleri logla
        if self.start_time:
            uptime = time.time() - self.start_time
            success_rate = (self.successful_heartbeats / self.total_heartbeats) * 100 if self.total_heartbeats > 0 else 0
            error_rate = (self.failed_heartbeats / self.total_heartbeats) * 100 if self.total_heartbeats > 0 else 0
            
            final_stats = f"Heartbeat Final İstatistikleri - Uptime: {uptime:.0f}s, Toplam: {self.total_heartbeats}, Başarılı: {self.successful_heartbeats} ({success_rate:.1f}%), Başarısız: {self.failed_heartbeats} ({error_rate:.1f}%), Ardışık Hata: {self.consecutive_errors}"
            log_system(f"Heartbeat sistemi durduruldu - {final_stats}")
            log_dimdb(f"Final istatistik - {final_stats}")
        else:
            log_system(f"Heartbeat sistemi durduruldu - Toplam hata sayısı: {self.consecutive_errors}")

    async def heartbeat_loop(self) -> None:
        """Optimized heartbeat döngüsü - 60 saniyede bir heartbeat gönderir"""
        loop_count = 0
        
        while self.is_running:
            loop_count += 1
            self.total_heartbeats += 1
            try:
                start_time = time.time()
                log_heartbeat(f"Gönderim başlatılıyor - Döngü #{loop_count}")
                
                await dimdb_istemcisi.send_heartbeat()
                duration = time.time() - start_time
                
                # Başarılı gönderim - error counter'ı sıfırla
                self.consecutive_errors = 0
                self.successful_heartbeats += 1
                success_rate = (self.successful_heartbeats / self.total_heartbeats) * 100
                
                ok("DİM-DB", f"Heartbeat gönderildi ({duration:.2f}s)")
                log_success(f"Heartbeat başarıyla gönderildi - Süre: {duration:.2f}s, Döngü: #{loop_count}")
                log_heartbeat(f"Performans - Gönderim süresi: {duration:.3f}s, Başarı oranı: {success_rate:.1f}%")
                
                # Her 10 heartbeat'te bir istatistik raporu
                if loop_count % 10 == 0:
                    self._log_statistics(loop_count)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except asyncio.CancelledError:
                status("DİM-DB", "Heartbeat döngüsü iptal edildi", level="stop")
                log_heartbeat(f"Döngü iptal edildi - Toplam döngü: {loop_count}")
                break
            except Exception as e:
                self.consecutive_errors += 1
                self.failed_heartbeats += 1
                error_rate = (self.failed_heartbeats / self.total_heartbeats) * 100
                error_msg = f"Heartbeat hatası - Döngü: #{loop_count}, Hata: {self.consecutive_errors}/{self.max_consecutive_errors}, Hata oranı: {error_rate:.1f}%, Detay: {str(e)}"
                err("DİM-DB", f"Heartbeat hatası ({self.consecutive_errors}/{self.max_consecutive_errors}): {e}")
                log_error(error_msg)
                
                # Çok fazla ardışık hata varsa daha uzun bekle
                if self.consecutive_errors >= self.max_consecutive_errors:
                    wait_time = self.heartbeat_interval * 2
                    warning_msg = f"Çok fazla ardışık hata! {wait_time} saniye bekleniyor... (Hata sayısı: {self.consecutive_errors})"
                    warn("DİM-DB", warning_msg)
                    log_warning(warning_msg)
                    log_heartbeat(f"Uzun bekleme başlatıldı - {wait_time}s")
                    await asyncio.sleep(wait_time)
                    self.consecutive_errors = 0  # Reset after long wait
                    log_heartbeat("Hata sayacı sıfırlandı - normal işleme dönülüyor")
                else:
                    # Kısa bekleme süresi (hata durumunda)
                    log_heartbeat(f"Hata sonrası kısa bekleme - 5 saniye (Hata: {self.consecutive_errors}/{self.max_consecutive_errors})")
                    await asyncio.sleep(5)

    def _log_statistics(self, loop_count: int) -> None:
        """Periyodik istatistik raporu"""
        if self.start_time:
            uptime = time.time() - self.start_time
            success_rate = (self.successful_heartbeats / self.total_heartbeats) * 100 if self.total_heartbeats > 0 else 0
            error_rate = (self.failed_heartbeats / self.total_heartbeats) * 100 if self.total_heartbeats > 0 else 0
            
            stats_msg = f"Heartbeat İstatistikleri - Döngü: #{loop_count}, Uptime: {uptime:.0f}s, Toplam: {self.total_heartbeats}, Başarılı: {self.successful_heartbeats} ({success_rate:.1f}%), Başarısız: {self.failed_heartbeats} ({error_rate:.1f}%), Ardışık Hata: {self.consecutive_errors}"
            log_system(stats_msg)
            log_dimdb(f"Detaylı istatistik - {stats_msg}")

    def get_status(self) -> dict:
        """Heartbeat servis durumunu döndürür"""
        uptime = time.time() - self.start_time if self.start_time else 0
        success_rate = (self.successful_heartbeats / self.total_heartbeats) * 100 if self.total_heartbeats > 0 else 0
        error_rate = (self.failed_heartbeats / self.total_heartbeats) * 100 if self.total_heartbeats > 0 else 0
        
        status = {
            "is_running": self.is_running,
            "heartbeat_interval": self.heartbeat_interval,
            "consecutive_errors": self.consecutive_errors,
            "max_consecutive_errors": self.max_consecutive_errors,
            "task_id": id(self.heartbeat_task) if self.heartbeat_task else None,
            "total_heartbeats": self.total_heartbeats,
            "successful_heartbeats": self.successful_heartbeats,
            "failed_heartbeats": self.failed_heartbeats,
            "success_rate": round(success_rate, 1),
            "error_rate": round(error_rate, 1),
            "uptime_seconds": round(uptime, 0)
        }
        log_heartbeat(f"Durum sorgusu - Status: {status}")
        return status


# Global heartbeat servis instance
heartbeat_servis = HeartbeatServis()
