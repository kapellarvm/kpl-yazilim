import uvicorn
import asyncio
import schedule
import time

# Projenin diğer modüllerini doğru paket yolundan import et
from rvm_sistemi.dimdb import istemci

async def run_heartbeat_scheduler():
    """Heartbeat'i periyodik olarak gönderen asenkron görev."""
    print("Heartbeat zamanlayıcı başlatıldı...")
    # schedule kütüphanesi asenkron görevleri doğrudan desteklemediği için
    # her tetiklendiğinde yeni bir asyncio task'ı oluşturuyoruz.
    schedule.every(60).seconds.do(lambda: asyncio.create_task(istemci.send_heartbeat()))
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

async def main():
    """
    Ana fonksiyon, Uvicorn sunucusunu ve heartbeat görevini başlatır.
    """
    # FastAPI sunucusunu başlatmak için Uvicorn konfigürasyonu
    config = uvicorn.Config(
        "rvm_sistemi.dimdb.sunucu:app", 
        host="0.0.0.0", 
        port=4321, 
        log_level="info"
    )
    server = uvicorn.Server(config)

    # Heartbeat görevini başlat
    heartbeat_task = asyncio.create_task(run_heartbeat_scheduler())

    print("RVM Sistemi Arka Plan Servisleri Başlatılıyor...")
    print("Uvicorn sunucusu http://0.0.0.0:4321 adresinde başlatılıyor.")
    
    # Sunucuyu çalıştır (bu satır programı burada bekletir)
    await server.serve()

    # Sunucu kapandığında heartbeat görevini de durdur
    heartbeat_task.cancel()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram sonlandırılıyor.")

