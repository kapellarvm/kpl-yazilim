"""
Sistem Kontrol API Endpoint'leri
Sistem durumu ve genel kontrol endpoint'leri
"""

from fastapi import APIRouter, HTTPException
from ..modeller.schemas import SuccessResponse, ErrorResponse
from ...makine.durum_degistirici import durum_makinesi
from ...makine.seri.motor_karti import MotorKart
from ...makine.seri.sensor_karti import SensorKart
import time

router = APIRouter(prefix="/sistem", tags=["Sistem"])

# Kart referansları
motor_kart = None
sensor_kart = None

def get_motor_kart():
    """Motor kartı referansını al"""
    try:
        from ...makine import kart_referanslari
        return kart_referanslari.motor_al()
    except Exception as e:
        print(f"Motor kartı alınamadı: {e}")
        return None

def get_sensor_kart():
    """Sensör kartı referansını al"""
    try:
        from ...makine import kart_referanslari
        return kart_referanslari.sensor_al()
    except Exception as e:
        print(f"Sensör kartı alınamadı: {e}")
        return None

@router.get("/durum")
async def sistem_durumu():
    """Sistem durumunu döndürür"""
    try:
        # Motor kartı durumu
        motor = get_motor_kart()
        motor_baglanti = motor is not None
        
        # Sensör kartı durumu
        sensor = get_sensor_kart()
        sensor_baglanti = sensor is not None
        
        # Mevcut durum
        mevcut_durum = durum_makinesi.durum
        
        return {
            "status": "success",
            "durum": mevcut_durum,
            "motor_baglanti": motor_baglanti,
            "sensor_baglanti": sensor_baglanti,
            "mesaj": "Sistem durumu alındı"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Sistem durum hatası: {str(e)}",
            "durum": "bilinmiyor",
            "motor_baglanti": False,
            "sensor_baglanti": False
        }

@router.post("/reset")
async def sistem_reset():
    """Sistemi resetler"""
    try:
        # Tüm kartları yeniden başlat
        global motor_kart, sensor_kart
        motor_kart = None
        sensor_kart = None
        
        # Durum makinesini sıfırla
        durum_makinesi.durum_degistir("oturum_yok")
        
        return SuccessResponse(message="Sistem başarıyla resetlendi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sistem reset hatası: {str(e)}")

@router.get("/uptime")
async def sistem_uptime():
    """Sistem çalışma süresini döndürür"""
    try:
        # Basit uptime hesaplama (gerçek implementasyon için daha gelişmiş olabilir)
        import psutil
        import time
        
        boot_time = psutil.boot_time()
        current_time = time.time()
        uptime_seconds = current_time - boot_time
        
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        seconds = int(uptime_seconds % 60)
        
        return {
            "status": "success",
            "uptime": {
                "hours": hours,
                "minutes": minutes,
                "seconds": seconds,
                "total_seconds": int(uptime_seconds)
            },
            "formatted": f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Uptime hesaplama hatası: {str(e)}",
            "uptime": None
        }

@router.get("/bellek")
async def sistem_bellek():
    """Sistem bellek kullanımını döndürür"""
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        
        return {
            "status": "success",
            "bellek": {
                "toplam": memory.total,
                "kullanilan": memory.used,
                "bos": memory.available,
                "yuzde": memory.percent
            },
            "formatted": {
                "toplam": f"{memory.total / (1024**3):.2f} GB",
                "kullanilan": f"{memory.used / (1024**3):.2f} GB",
                "bos": f"{memory.available / (1024**3):.2f} GB",
                "yuzde": f"{memory.percent:.1f}%"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Bellek bilgisi alma hatası: {str(e)}",
            "bellek": None
        }

@router.get("/cpu")
async def sistem_cpu():
    """Sistem CPU kullanımını döndürür"""
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        return {
            "status": "success",
            "cpu": {
                "kullanım_yuzde": cpu_percent,
                "core_sayisi": cpu_count
            },
            "formatted": {
                "kullanım": f"{cpu_percent:.1f}%",
                "core_sayisi": f"{cpu_count} core"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"CPU bilgisi alma hatası: {str(e)}",
            "cpu": None
        }

@router.get("/disk")
async def sistem_disk():
    """Sistem disk kullanımını döndürür"""
    try:
        import psutil
        
        disk = psutil.disk_usage('/')
        
        return {
            "status": "success",
            "disk": {
                "toplam": disk.total,
                "kullanilan": disk.used,
                "bos": disk.free,
                "yuzde": (disk.used / disk.total) * 100
            },
            "formatted": {
                "toplam": f"{disk.total / (1024**3):.2f} GB",
                "kullanilan": f"{disk.used / (1024**3):.2f} GB",
                "bos": f"{disk.free / (1024**3):.2f} GB",
                "yuzde": f"{(disk.used / disk.total) * 100:.1f}%"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Disk bilgisi alma hatası: {str(e)}",
            "disk": None
        }
