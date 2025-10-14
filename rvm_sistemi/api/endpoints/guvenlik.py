from fastapi import APIRouter, HTTPException
from rvm_sistemi.api.modeller.schemas import SuccessResponse, ErrorResponse
from rvm_sistemi.utils.logger import log_system, log_error, log_success

router = APIRouter()

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
        guvenlik_durumu["ust_kilit"]["acik"] = True
        guvenlik_durumu["ust_kilit"]["dil_var"] = False
        guvenlik_durumu["ust_sensor"]["aktif"] = False
        
        log_success("Üst kilit açıldı")
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
        guvenlik_durumu["ust_kilit"]["acik"] = False
        guvenlik_durumu["ust_kilit"]["dil_var"] = True
        guvenlik_durumu["ust_sensor"]["aktif"] = True
        
        log_success("Üst kilit kapatıldı")
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
        guvenlik_durumu["alt_kilit"]["acik"] = True
        guvenlik_durumu["alt_kilit"]["dil_var"] = False
        guvenlik_durumu["alt_sensor"]["aktif"] = False
        
        log_success("Alt kilit açıldı")
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
        guvenlik_durumu["alt_kilit"]["acik"] = False
        guvenlik_durumu["alt_kilit"]["dil_var"] = True
        guvenlik_durumu["alt_sensor"]["aktif"] = True
        
        log_success("Alt kilit kapatıldı")
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
        
        # Sensör durumunu geçici olarak değiştir (test için)
        if sensor_tipi == "ust":
            guvenlik_durumu["ust_sensor"]["aktif"] = not guvenlik_durumu["ust_sensor"]["aktif"]
        else:
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
