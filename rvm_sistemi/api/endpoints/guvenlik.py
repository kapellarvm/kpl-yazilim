from fastapi import APIRouter, HTTPException
from rvm_sistemi.api.modeller.schemas import SuccessResponse, ErrorResponse
from rvm_sistemi.utils.logger import log_system, log_error, log_success, log_warning
from rvm_sistemi.makine.seri.sensor_karti import SensorKart

router = APIRouter()

# Sensor kartı referansı (ana.py'dan alınacak)
sensor_kart = None

def get_sensor_kart():
    """Sensor kartı referansını alır"""
    global sensor_kart
    if sensor_kart is None:
        # Ana sistemden sensor kartını al
        try:
            from rvm_sistemi.makine.kart_referanslari import sensor_al
            sensor_kart = sensor_al()
            if sensor_kart:
                log_success("Sensor kartı referansı alındı")
            else:
                log_warning("Sensor kartı referansı bulunamadı")
        except Exception as e:
            log_error(f"Sensor kartı alınamadı: {e}")
    return sensor_kart

# Güvenlik kartı durumu (şimdilik mock data)
guvenlik_durumu = {
    "ust_kilit": {
        "acik": False,
        "dil_var": True,
        "voltaj": 12.0,
        "akim": 75,
        "guc": 0.9
    },
    "alt_kilit": {
        "acik": False,
        "dil_var": True,
        "voltaj": 12.1,
        "akim": 74,
        "guc": 0.89
    },
    "ust_sensor": {
        "aktif": True,
        "voltaj": 5.0,
        "akim": 5,
        "guc": 0.025
    },
    "alt_sensor": {
        "aktif": True,
        "voltaj": 5.0,
        "akim": 5,
        "guc": 0.025
    },
    "fan": {
        "hiz": 0,
        "calisiyor": False
    },
    "guvenlik_role": {
        "aktif": False,
        "bypass": False
    }
}

@router.get("/guvenlik/durum")
async def guvenlik_durum():
    """Güvenlik kartı durumunu getirir"""
    try:
        log_system("Güvenlik kartı durumu sorgulandı")
        return SuccessResponse(
            status="success",
            message="Güvenlik kartı durumu alındı",
            data=guvenlik_durumu
        )
    except Exception as e:
        log_error(f"Güvenlik durumu alma hatası: {e}")
        raise HTTPException(status_code=500, detail="Güvenlik durumu alınamadı")

@router.post("/guvenlik/ust-kilit-ac")
async def ust_kilit_ac():
    """Üst kiliti açar"""
    try:
        # Sensor kartından üst kilit açma komutunu gönder
        sensor = get_sensor_kart()
        if sensor:
            sensor.ust_kilit_ac()
            log_success("Üst kilit açma komutu gönderildi")
        else:
            log_warning("Sensor kartı bulunamadı, mock data kullanılıyor")
            guvenlik_durumu["ust_kilit"]["acik"] = True
            guvenlik_durumu["ust_kilit"]["dil_var"] = False
            guvenlik_durumu["ust_sensor"]["aktif"] = False
        
        return SuccessResponse(
            status="success",
            message="Üst kilit başarıyla açıldı"
        )
    except Exception as e:
        log_error(f"Üst kilit açma hatası: {e}")
        raise HTTPException(status_code=500, detail="Üst kilit açılamadı")

@router.post("/guvenlik/ust-kilit-kapat")
async def ust_kilit_kapat():
    """Üst kiliti kapatır"""
    try:
        # Sensor kartından üst kilit kapatma komutunu gönder
        sensor = get_sensor_kart()
        if sensor:
            sensor.ust_kilit_kapat()
            log_success("Üst kilit kapatma komutu gönderildi")
        else:
            log_warning("Sensor kartı bulunamadı, mock data kullanılıyor")
            guvenlik_durumu["ust_kilit"]["acik"] = False
            guvenlik_durumu["ust_kilit"]["dil_var"] = True
            guvenlik_durumu["ust_sensor"]["aktif"] = True
        
        return SuccessResponse(
            status="success",
            message="Üst kilit başarıyla kapatıldı"
        )
    except Exception as e:
        log_error(f"Üst kilit kapatma hatası: {e}")
        raise HTTPException(status_code=500, detail="Üst kilit kapatılamadı")

@router.post("/guvenlik/alt-kilit-ac")
async def alt_kilit_ac():
    """Alt kiliti açar"""
    try:
        # Sensor kartından alt kilit açma komutunu gönder
        sensor = get_sensor_kart()
        if sensor:
            sensor.alt_kilit_ac()
            log_success("Alt kilit açma komutu gönderildi")
        else:
            log_warning("Sensor kartı bulunamadı, mock data kullanılıyor")
            guvenlik_durumu["alt_kilit"]["acik"] = True
            guvenlik_durumu["alt_kilit"]["dil_var"] = False
            guvenlik_durumu["alt_sensor"]["aktif"] = False
        
        return SuccessResponse(
            status="success",
            message="Alt kilit başarıyla açıldı"
        )
    except Exception as e:
        log_error(f"Alt kilit açma hatası: {e}")
        raise HTTPException(status_code=500, detail="Alt kilit açılamadı")

@router.post("/guvenlik/alt-kilit-kapat")
async def alt_kilit_kapat():
    """Alt kiliti kapatır"""
    try:
        # Sensor kartından alt kilit kapatma komutunu gönder
        sensor = get_sensor_kart()
        if sensor:
            sensor.alt_kilit_kapat()
            log_success("Alt kilit kapatma komutu gönderildi")
        else:
            log_warning("Sensor kartı bulunamadı, mock data kullanılıyor")
            guvenlik_durumu["alt_kilit"]["acik"] = False
            guvenlik_durumu["alt_kilit"]["dil_var"] = True
            guvenlik_durumu["alt_sensor"]["aktif"] = True
        
        return SuccessResponse(
            status="success",
            message="Alt kilit başarıyla kapatıldı"
        )
    except Exception as e:
        log_error(f"Alt kilit kapatma hatası: {e}")
        raise HTTPException(status_code=500, detail="Alt kilit kapatılamadı")

@router.post("/guvenlik/fan-ac")
async def fan_ac():
    """Soğutma fanını açar"""
    try:
        # Sensor kartından fan açma komutunu gönder
        sensor = get_sensor_kart()
        if sensor:
            sensor.fan_pwm(50)  # Varsayılan hız %50
            log_success("Fan açma komutu gönderildi")
        else:
            log_warning("Sensor kartı bulunamadı, mock data kullanılıyor")
        
        guvenlik_durumu["fan"]["calisiyor"] = True
        guvenlik_durumu["fan"]["hiz"] = 50  # Varsayılan hız
        
        log_success("Soğutma fanı açıldı")
        return SuccessResponse(
            status="success",
            message="Soğutma fanı başarıyla açıldı"
        )
    except Exception as e:
        log_error(f"Fan açma hatası: {e}")
        raise HTTPException(status_code=500, detail="Fan açılamadı")

@router.post("/guvenlik/fan-kapat")
async def fan_kapat():
    """Soğutma fanını kapatır"""
    try:
        # Sensor kartından fan kapatma komutunu gönder
        sensor = get_sensor_kart()
        if sensor:
            sensor.fan_pwm(0)  # Hızı 0'a ayarla
            log_success("Fan kapatma komutu gönderildi")
        else:
            log_warning("Sensor kartı bulunamadı, mock data kullanılıyor")
        
        guvenlik_durumu["fan"]["calisiyor"] = False
        guvenlik_durumu["fan"]["hiz"] = 0
        
        log_success("Soğutma fanı kapatıldı")
        return SuccessResponse(
            status="success",
            message="Soğutma fanı başarıyla kapatıldı"
        )
    except Exception as e:
        log_error(f"Fan kapatma hatası: {e}")
        raise HTTPException(status_code=500, detail="Fan kapatılamadı")

@router.post("/guvenlik/fan-hiz")
async def fan_hiz_ayarla(hiz: int):
    """Fan hızını ayarlar (0-100)"""
    try:
        if hiz < 0 or hiz > 100:
            raise HTTPException(status_code=400, detail="Hız 0-100 arasında olmalıdır")
        
        # Sensor kartından fan hız ayarlama komutunu gönder
        sensor = get_sensor_kart()
        if sensor:
            sensor.fan_pwm(hiz)
            log_success(f"Fan hız ayarlama komutu gönderildi: {hiz}%")
        else:
            log_warning("Sensor kartı bulunamadı, mock data kullanılıyor")
        
        guvenlik_durumu["fan"]["hiz"] = hiz
        guvenlik_durumu["fan"]["calisiyor"] = hiz > 0
        
        log_success(f"Fan hızı {hiz}% olarak ayarlandı")
        return SuccessResponse(
            status="success",
            message=f"Fan hızı {hiz}% olarak ayarlandı"
        )
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Fan hız ayarlama hatası: {e}")
        raise HTTPException(status_code=500, detail="Fan hızı ayarlanamadı")

@router.post("/guvenlik/role-reset")
async def guvenlik_role_reset():
    """Güvenlik rölesini resetler"""
    try:
        # Sensor kartından güvenlik rölesi reset komutunu gönder
        sensor = get_sensor_kart()
        if sensor:
            sensor.guvenlik_role_reset()
            log_success("Güvenlik rölesi reset komutu gönderildi")
        else:
            log_warning("Sensor kartı bulunamadı, mock data kullanılıyor")
        
        # Durumu güncelle
        guvenlik_durumu["guvenlik_role"]["aktif"] = True
        guvenlik_durumu["guvenlik_role"]["bypass"] = False
        
        log_success("Güvenlik rölesi resetlendi")
        return SuccessResponse(
            status="success",
            message="Güvenlik rölesi başarıyla resetlendi"
        )
    except Exception as e:
        log_error(f"Güvenlik rölesi reset hatası: {e}")
        raise HTTPException(status_code=500, detail="Güvenlik rölesi resetlenemedi")

@router.post("/guvenlik/role-bypass")
async def guvenlik_role_bypass():
    """Güvenlik rölesi bypass'ını aç/kapat"""
    try:
        # Sensor kartından bypass komutunu gönder
        sensor = get_sensor_kart()
        if sensor:
            # Mevcut bypass durumuna göre komut gönder
            if guvenlik_durumu["guvenlik_role"]["bypass"]:
                sensor.bypass_modu_kapat()
                log_success("Bypass kapatma komutu gönderildi")
            else:
                sensor.bypass_modu_ac()
                log_success("Bypass açma komutu gönderildi")
        else:
            log_warning("Sensor kartı bulunamadı, mock data kullanılıyor")
        
        # Durumu güncelle
        guvenlik_durumu["guvenlik_role"]["bypass"] = not guvenlik_durumu["guvenlik_role"]["bypass"]
        
        durum = "açıldı" if guvenlik_durumu["guvenlik_role"]["bypass"] else "kapatıldı"
        log_success(f"Güvenlik rölesi bypass {durum}")
        return SuccessResponse(
            status="success",
            message=f"Güvenlik rölesi bypass {durum}"
        )
    except Exception as e:
        log_error(f"Güvenlik rölesi bypass hatası: {e}")
        raise HTTPException(status_code=500, detail="Güvenlik rölesi bypass yapılamadı")

@router.post("/guvenlik/sensor-test")
async def sensor_test(sensor_tipi: str):
    """Sensör testi yapar (ust/alt)"""
    try:
        if sensor_tipi not in ["ust", "alt"]:
            raise HTTPException(status_code=400, detail="Sensör tipi 'ust' veya 'alt' olmalıdır")
        
        # Sensor kartından manyetik sensör sağlık kontrolü yap
        sensor = get_sensor_kart()
        # Sensör durumunu geçici olarak değiştir (test için)
        if sensor_tipi == "ust":
            sensor.ust_kilit_durum_sorgula()
            guvenlik_durumu["ust_sensor"]["aktif"] = not guvenlik_durumu["ust_sensor"]["aktif"]
        else:
            sensor.alt_kilit_durum_sorgula()
            guvenlik_durumu["alt_sensor"]["aktif"] = not guvenlik_durumu["alt_sensor"]["aktif"]
        
        log_success(f"{sensor_tipi} sensör testi yapıldı")
        return SuccessResponse(
            status="success",
            message=f"{sensor_tipi} sensör testi başarıyla yapıldı"
        )
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Sensör test hatası: {e}")
        raise HTTPException(status_code=500, detail="Sensör testi yapılamadı")

@router.post("/guvenlik/guvenlik-kart-reset")
async def guvenlik_kart_reset():
    """Güvenlik kartını resetler"""
    try:
        # Sensor kartından güvenlik kartı reset komutunu gönder
        sensor = get_sensor_kart()
        if sensor:
            sensor.guvenlik_kart_reset()
            log_success("Güvenlik kartı reset komutu gönderildi")
        else:
            log_warning("Sensor kartı bulunamadı, mock data kullanılıyor")
        
        # Tüm güvenlik durumlarını sıfırla
        guvenlik_durumu["ust_kilit"]["acik"] = False
        guvenlik_durumu["ust_kilit"]["dil_var"] = True
        guvenlik_durumu["alt_kilit"]["acik"] = False
        guvenlik_durumu["alt_kilit"]["dil_var"] = True
        guvenlik_durumu["ust_sensor"]["aktif"] = True
        guvenlik_durumu["alt_sensor"]["aktif"] = True
        guvenlik_durumu["fan"]["calisiyor"] = False
        guvenlik_durumu["fan"]["hiz"] = 0
        guvenlik_durumu["guvenlik_role"]["aktif"] = True
        guvenlik_durumu["guvenlik_role"]["bypass"] = False
        
        log_success("Güvenlik kartı resetlendi")
        return SuccessResponse(
            status="success",
            message="Güvenlik kartı başarıyla resetlendi"
        )
    except Exception as e:
        log_error(f"Güvenlik kartı reset hatası: {e}")
        raise HTTPException(status_code=500, detail="Güvenlik kartı resetlenemedi")
