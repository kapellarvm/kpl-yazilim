"""
Bakım API Endpoint'leri
Bakım modu ve sistem yönetimi endpoint'leri
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from ..modeller.schemas import BakimModuRequest, BakimUrlRequest
from ...makine.durum_degistirici import durum_makinesi
import os

router = APIRouter(prefix="/bakim", tags=["Bakım"])


@router.get("/")
async def bakim_ekrani():
    """Bakım ekranı HTML sayfasını döndürür"""
    html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "bakim.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Bakım ekranı dosyası bulunamadı</h1>", status_code=404)


@router.post("/modu-ayarla")
async def bakim_modu_ayarla(request: BakimModuRequest):
    """Bakım modunu aktif/pasif eder"""
    try:
        if request.aktif:
            # Durum makinesine bakım moduna geç - otomatik ekran değişimi yapılacak
            durum_makinesi.durum_degistir("bakim")
            return {"status": "success", "message": "Bakım modu aktif edildi, ekran açıldı", "durum": "bakim"}
        else:
            # Durum makinesine normal moda geç - otomatik ana ekrana dönülecek
            durum_makinesi.durum_degistir("oturum_yok")
            return {"status": "success", "message": "Bakım modu pasif edildi, ana ekrana dönüldü", "durum": "oturum_yok"}
    except Exception as e:
        return {"status": "error", "message": f"Bakım modu hatası: {str(e)}"}


@router.post("/url-ayarla")
async def bakim_url_ayarla(request: BakimUrlRequest):
    """Bakım ekranı URL'ini ayarlar"""
    try:
        durum_makinesi.bakim_url = request.url
        return {"status": "success", "message": f"Bakım URL'i güncellendi: {request.url}"}
    except Exception as e:
        return {"status": "error", "message": f"URL ayarlama hatası: {str(e)}"}


@router.get("/url")
async def bakim_url_getir():
    """Mevcut bakım URL'ini döndürür"""
    return {"status": "success", "url": durum_makinesi.bakim_url}
