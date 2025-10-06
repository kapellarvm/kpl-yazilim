"""
Uyarı API Endpoint'leri
Uyarı gösterimi ve yönetimi endpoint'leri
"""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from ..modeller.schemas import UyariRequest
from ...makine.uyari_yoneticisi import uyari_yoneticisi
import os

router = APIRouter(prefix="/uyari", tags=["Uyarı"])


@router.get("/")
async def uyari_ekrani(mesaj: str = "Lütfen şişeyi alınız", sure: int = 2):
    """Uyarı ekranı HTML sayfasını döndürür"""
    html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static", "uyari.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            # Mesaj ve süre parametrelerini HTML'e aktar
            html_content = html_content.replace("{{MESAJ}}", mesaj)
            html_content = html_content.replace("{{SURE}}", str(sure))
            return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content=f"<h1>Uyarı: {mesaj}</h1><p>{sure} saniye sonra kapanacak</p>", status_code=404)


@router.post("/goster")
async def uyari_goster(request: UyariRequest):
    """Hızlı uyarı gösterir - belirtilen süre sonra otomatik kapanır"""
    try:
        # Uyarıyı göster
        basarili = uyari_yoneticisi.uyari_goster(request.mesaj, request.sure)
        
        if basarili:
            return {"status": "success", "message": f"Uyarı gösterildi: {request.mesaj}", "sure": request.sure}
        else:
            return {"status": "error", "message": "Uyarı gösterilemedi"}
    except Exception as e:
        return {"status": "error", "message": f"Uyarı hatası: {str(e)}"}


@router.get("/durumu")
async def uyari_durumu():
    """Uyarı durumunu döndürür"""
    try:
        durum = uyari_yoneticisi.uyari_durumu()
        return {"status": "success", "uyari_durumu": durum}
    except Exception as e:
        return {"status": "error", "message": f"Uyarı durumu hatası: {str(e)}"}


@router.post("/kapat")
async def uyari_kapat():
    """Aktif uyarıyı kapatır"""
    try:
        basarili = uyari_yoneticisi.uyari_kapat()
        if basarili:
            return {"status": "success", "message": "Uyarı kapatıldı"}
        else:
            return {"status": "error", "message": "Uyarı kapatılamadı"}
    except Exception as e:
        return {"status": "error", "message": f"Uyarı kapatma hatası: {str(e)}"}
