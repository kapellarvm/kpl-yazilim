"""
Heartbeat Servisleri
DİM-DB'ye periyodik durum bildirimi
"""

import asyncio
from ...dimdb import dimdb_istemcisi


class HeartbeatServis:
    """Heartbeat yönetimi servis sınıfı"""
    
    def __init__(self):
        self.heartbeat_task = None

    async def start_heartbeat(self) -> None:
        """Heartbeat sistemini başlatır"""
        if self.heartbeat_task is None:
            self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())
            print("✅ [DİM-DB] Heartbeat sistemi başlatıldı")

    async def stop_heartbeat(self) -> None:
        """Heartbeat sistemini durdurur"""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            self.heartbeat_task = None
            print("🛑 [DİM-DB] Heartbeat sistemi durduruldu")

    async def heartbeat_loop(self) -> None:
        """60 saniyede bir heartbeat gönderir"""
        while True:
            try:
                await dimdb_istemcisi.send_heartbeat()
                await asyncio.sleep(60)  # 60 saniye bekle
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ [DİM-DB] Heartbeat hatası: {e}")
                await asyncio.sleep(60)  # Hata durumunda da 60 saniye bekle


# Global heartbeat servis instance
heartbeat_servis = HeartbeatServis()
