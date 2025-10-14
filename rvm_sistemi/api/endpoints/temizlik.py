from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
import os
from ..modeller.schemas import SuccessResponse

router = APIRouter()

@router.get("/temizlik")
async def temizlik_ekrani():
    """Temizlik ekranını döndürür"""
    try:
        # Temizlik HTML dosyasının yolunu belirle
        temizlik_html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "temizlik.html")
        
        if os.path.exists(temizlik_html_path):
            with open(temizlik_html_path, 'r', encoding='utf-8') as file:
                content = file.read()
            return HTMLResponse(content=content)
        else:
            return HTMLResponse(content="<h1>Temizlik ekranı dosyası bulunamadı</h1>", status_code=404)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Temizlik ekranı hatası: {str(e)}")

@router.post("/temizlik-modu")
async def temizlik_modu_ayarla():
    """Temizlik modunu aktif eder"""
    try:
        from ...makine.durum_degistirici import durum_makinesi
        from ...utils.logger import log_system
        
        print(f"[DEBUG] API - Temizlik modu aktif ediliyor...")
        log_system("API - Temizlik modu aktif ediliyor")
        
        # Temizlik moduna geç
        from ...makine.senaryolar.temizlik import temizlik
        durum_makinesi.durum_degistir("temizlik")
        
        print(f"[DEBUG] API - Temizlik modu aktif edildi")
        log_system("API - Temizlik modu aktif edildi")
        
        return SuccessResponse(message="Temizlik modu aktif edildi")
    except Exception as e:
        print(f"[DEBUG] API - Temizlik modu hatası: {e}")
        return {"status": "error", "message": f"Temizlik modu hatası: {str(e)}"}

@router.post("/temizlik-url-ayarla")
async def temizlik_url_ayarla(request: dict):
    """Temizlik ekranı URL'ini ayarlar"""
    try:
        from ...makine.senaryolar.temizlik import temizlik
        
        if 'url' not in request:
            return {"status": "error", "message": "URL parametresi gerekli"}
        
        temizlik.temizlik_url = request['url']
        return SuccessResponse(message=f"Temizlik URL'i güncellendi: {request['url']}")
    except Exception as e:
        return {"status": "error", "message": f"URL ayarlama hatası: {str(e)}"}

@router.get("/temizlik-url")
async def temizlik_url_getir():
    """Mevcut temizlik URL'ini döndürür"""
    try:
        from ...makine.senaryolar.temizlik import temizlik
        return {"status": "success", "url": temizlik.temizlik_url}
    except Exception as e:
        return {"status": "error", "message": f"URL alma hatası: {str(e)}"}

@router.post("/temizlik-modundan-cik")
async def temizlik_modundan_cik():
    """Temizlik modundan çıkar"""
    try:
        from ...makine.senaryolar.temizlik import temizlik
        from ...utils.logger import log_system
        
        print(f"[DEBUG] API - Temizlik modundan çıkılıyor...")
        log_system("API - Temizlik modundan çıkılıyor")
        
        # Önce temizlik modunu kapat
        temizlik.temizlik_modundan_cik()
        
        print(f"[DEBUG] API - Temizlik modundan çıkıldı")
        log_system("API - Temizlik modundan çıkıldı")
        
        return SuccessResponse(message="Temizlik modundan çıkıldı")
    except Exception as e:
        print(f"[DEBUG] API - Temizlik modu çıkış hatası: {e}")
        return {"status": "error", "message": f"Temizlik modu çıkış hatası: {str(e)}"}

@router.get("/temizlik/durum")
async def temizlik_durum():
    """Temizlik durumunu döndürür"""
    try:
        from ...makine.durum_degistirici import durum_makinesi
        
        return {
            "status": "success",
            "durum": durum_makinesi.durum,
            "temizlik_aktif": durum_makinesi.durum == "temizlik",
            "mesaj": "Temizlik durumu alındı"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Temizlik durum hatası: {str(e)}",
            "durum": "bilinmiyor",
            "temizlik_aktif": False
        }
