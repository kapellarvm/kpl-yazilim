"""
Sensör Kontrol API Endpoint'leri
Sensör kontrolü ve ölçüm endpoint'leri
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..modeller.schemas import SuccessResponse, ErrorResponse
from ...makine.seri.sensor_karti import SensorKart
from ...makine.durum_degistirici import durum_makinesi
from ...utils.logger import log_sensor, log_error, log_success, log_warning
import asyncio

router = APIRouter(prefix="/sensor", tags=["Sensör"])

# Pydantic modelleri
class LedPwmRequest(BaseModel):
    deger: int

class KomutGonderRequest(BaseModel):
    komut: str

# Sensör kartı referansı (ana.py'dan alınacak)
sensor_kart = None

def get_sensor_kart():
    """Sensör kartı referansını al"""
    try:
        # Ana.py'dan oluşturulan sensör kartını al
        from ...makine import kart_referanslari
        return kart_referanslari.sensor_al()
    except Exception as e:
        print(f"Sensör kartı alınamadı: {e}")
        log_error(f"Sensör kartı alınamadı: {e}")
        return None

@router.get("/durum")
async def sensor_durum():
    """Sensör kartı durumunu kontrol eder"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            return {
                "status": "error",
                "message": "Sensör kartı bağlantısı yok. Sistem çalıştırılmamış olabilir.",
                "bagli": False
            }
        
        # Sensör sağlık durumunu kontrol et
        saglikli = sensor.getir_saglik_durumu()
        return {
            "status": "success",
            "message": "Sensör kartı bağlı",
            "bagli": True,
            "saglikli": saglikli,
            "port": sensor.port_adi
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Sensör durum kontrolü hatası: {str(e)}",
            "bagli": False
        }

@router.post("/teach")
async def sensor_teach():
    """Giriş sensör teach işlemini başlatır"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok. Sistem çalıştırılmamış olabilir.")
        
        # Giriş sensör teach işlemi
        sensor.teach()
        return SuccessResponse(message="Giriş sensör teach tamamlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Teach hatası: {str(e)}")

@router.post("/agirlik-olc")
async def agirlik_olc():
    """Ağırlık ölçümü yapar - Yeni sistem: 'lo' komutu gönderir"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # Yeni sistem: 'lo' komutu gönder, ağırlık callback ile gelecek
        result = sensor.agirlik_olc()
        if result:
            return {
                "status": "success",
                "message": "Ağırlık ölçüm komutu gönderildi, sonuç callback ile gelecek"
            }
        else:
            raise HTTPException(status_code=500, detail="Ağırlık ölçüm komutu gönderilemedi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ağırlık ölçüm hatası: {str(e)}")

@router.post("/tare")
async def sensor_tare():
    """Loadcell tare işlemini yapar"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok. Sistem çalıştırılmamış olabilir.")
        
        # Tare işlemi
        sensor.tare()
        return SuccessResponse(message="Loadcell tare tamamlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tare hatası: {str(e)}")

@router.post("/led-ac")
async def led_ac():
    """LED'i açar"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # LED'i aç
        sensor.led_ac()
        return SuccessResponse(message="LED açıldı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LED açma hatası: {str(e)}")

@router.post("/led-kapat")
async def led_kapat():
    """LED'i kapatır"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # LED'i kapat
        sensor.led_kapat()
        return SuccessResponse(message="LED kapatıldı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LED kapatma hatası: {str(e)}")

@router.post("/led-pwm")
async def led_pwm(request: LedPwmRequest):
    """LED PWM değerini ayarlar (0-100)"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # Değeri 0-100 arasında sınırla
        deger = max(0, min(100, request.deger))
        
        # LED PWM değerini ayarla
        sensor.led_pwm(deger)
        return SuccessResponse(message=f"LED PWM değeri {deger} olarak ayarlandı")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LED PWM ayarlama hatası: {str(e)}")

@router.post("/sds-sensorler")
async def sds_sensorler():
    """SDS sensör durumlarını sorgular"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # SDS komutunu gönder
        result = sensor.sds_sensorler()
        if result:
            return SuccessResponse(message="SDS sensör sorgulama komutu gönderildi, sonuç callback ile gelecek")
        else:
            raise HTTPException(status_code=500, detail="SDS sensör sorgulama komutu gönderilemedi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SDS sensör sorgulama hatası: {str(e)}")

@router.post("/doluluk-orani")
async def doluluk_orani():
    """Doluluk oranlarını sorgular"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        # Doluluk oranı komutunu gönder
        result = sensor.doluluk_oranı()
        if result:
            return SuccessResponse(message="Doluluk oranı sorgulama komutu gönderildi, sonuç callback ile gelecek")
        else:
            raise HTTPException(status_code=500, detail="Doluluk oranı sorgulama komutu gönderilemedi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Doluluk oranı sorgulama hatası: {str(e)}")

@router.post("/komut-gonder")
async def komut_gonder(request: KomutGonderRequest):
    """Sensör kartına özel komut gönderir (msud, msad vb.)"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok")
        
        komut = request.komut.strip().lower()
        log_sensor(f"Komut gönderiliyor: {komut}")
        
        # Komuta göre ilgili metodu çağır
        if komut == "msud":
            sensor.ust_kilit_durum_sorgula()
            log_success("Üst kapak durum sorgusu gönderildi")
            return SuccessResponse(message="Üst kapak durum sorgusu gönderildi, sonuç callback ile gelecek")
        elif komut == "msad":
            sensor.alt_kilit_durum_sorgula()
            log_success("Alt kapak durum sorgusu gönderildi")
            return SuccessResponse(message="Alt kapak durum sorgusu gönderildi, sonuç callback ile gelecek")
        else:
            log_warning(f"Bilinmeyen komut: {komut}")
            raise HTTPException(status_code=400, detail=f"Bilinmeyen komut: {komut}")
            
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Komut gönderme hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Komut gönderme hatası: {str(e)}")

@router.get("/son-deger")
async def sensor_son_deger():
    """Son sensör değerlerini döndürür"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            return {
                "status": "error",
                "message": "Sensör kartı bağlantısı yok",
                "data": None
            }
        
        # Son değerleri al
        agirlik = sensor.son_agirlik_degeri()
        mesaj = sensor.son_mesaj()
        
        return {
            "status": "success",
            "data": {
                "agirlik": agirlik,
                "mesaj": mesaj
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Sensör değer alma hatası: {str(e)}",
            "data": None
        }

@router.post("/ping")
async def sensor_ping():
    """Sensör kartını ping eder ve sağlık durumunu döndürür"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            return {
                "status": "error",
                "message": "Sensör kartı bulunamadı",
                "saglikli": False
            }
        
        # Ping işlemini başlat
        sensor.ping()
        
        # Sağlık durumunu al
        saglikli = sensor.getir_saglik_durumu()
        
        return {
            "status": "success",
            "message": "Ping tamamlandı",
            "saglikli": saglikli
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ping hatası: {str(e)}",
            "saglikli": False
        }

@router.post("/reset")
async def sensor_reset():
    """Sensör kartını resetler"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            raise HTTPException(status_code=500, detail="Sensör kartı bağlantısı yok. Sistem çalıştırılmamış olabilir.")
        
        # Sensör kartını resetle
        sensor.reset()
        return SuccessResponse(message="Sensör kartı başarıyla resetlendi")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sensör reset hatası: {str(e)}")

@router.get("/durum")
async def sensor_durum():
    """Sensör durumunu döndürür"""
    try:
        sensor = get_sensor_kart()
        if not sensor:
            return {"status": "error", "message": "Sensör kartı bağlantısı yok", "bagli": False}
        
        return {
            "status": "success",
            "bagli": True,
            "mesaj": "Sensör kartı bağlı"
        }
    except Exception as e:
        return {"status": "error", "message": f"Sensör durum hatası: {str(e)}", "bagli": False}
