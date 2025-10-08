"""
Ana FastAPI Uygulaması
RVM API'nin merkezi yapılandırması ve routing
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from .endpoints import dimdb, bakim, uyari, motor, sensor, sistem
from .middleware.log_filter import log_filter_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama yaşam döngüsü yönetimi"""
    # Uygulama başlatma
    print("RVM API Sunucusu başlatılıyor...")
    
    yield
    
    print("\nRVM API Sunucusu kapatılıyor...")


# FastAPI uygulamasını oluştur
app = FastAPI(
    title="RVM API",
    description="Reverse Vending Machine API",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware'leri ekle
app.middleware("http")(log_filter_middleware)

# Static dosyaları serve et
try:
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    print(f"Static dosya yolu: {static_path}")
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")
        print("Static dosyalar başarıyla yüklendi.")
    else:
        print(f"Static klasör bulunamadı: {static_path}")
except Exception as e:
    print(f"Static dosyalar yüklenemedi: {e}")

# Router'ları ekle
app.include_router(dimdb.router, prefix="/api/v1")
app.include_router(bakim.router, prefix="/api/v1")
app.include_router(uyari.router, prefix="/api/v1")
app.include_router(motor.router, prefix="/api/v1")
app.include_router(sensor.router, prefix="/api/v1")
app.include_router(sistem.router, prefix="/api/v1")

# Yeni router'ları ekle
from .endpoints import ac_motor, hazne, kalibrasyon, test, websocket
app.include_router(ac_motor.router, prefix="/api/v1")
app.include_router(hazne.router, prefix="/api/v1")
app.include_router(kalibrasyon.router, prefix="/api/v1")
app.include_router(test.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")

# Geriye dönük uyumluluk için eski DİM-DB endpoint'leri (prefix olmadan)
app.include_router(dimdb.router)

# Geriye dönük uyumluluk için eski endpoint'ler (prefix olmadan)
from .endpoints.dimdb import session_start, accept_package, session_end, maintenance_mode, stop_operation, update_products, reset_rvm

# Eski endpoint'leri ekle
app.post("/sessionStart")(session_start)
app.post("/acceptPackage")(accept_package)
app.post("/sessionEnd")(session_end)
app.post("/maintenanceMode")(maintenance_mode)
app.post("/stopOperation")(stop_operation)
app.post("/updateProducts")(update_products)
app.post("/resetRvm")(reset_rvm)

# Ana sayfa endpoint'i
@app.get("/")
async def ana_sayfa():
    """Test endpoint'i"""
    return {"message": "RVM API Sunucusu çalışıyor!", "bakim_ekrani": "/api/v1/bakim"}

# Geriye dönük uyumluluk için eski endpoint'ler
@app.get("/bakim")
async def bakim_ekrani_eski():
    """Bakım ekranı HTML sayfasını döndürür (geriye dönük uyumluluk)"""
    from fastapi.responses import HTMLResponse
    import os
    
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "bakim.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Bakım ekranı dosyası bulunamadı</h1>", status_code=404)

@app.get("/uyari")
async def uyari_ekrani_eski(mesaj: str = "Lütfen şişeyi alınız", sure: int = 2):
    """Uyarı ekranı HTML sayfasını döndürür (geriye dönük uyumluluk)"""
    from fastapi.responses import HTMLResponse
    import os
    
    html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uyari.html")
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            # Mesaj ve süre parametrelerini HTML'e aktar
            html_content = html_content.replace("{{MESAJ}}", mesaj)
            html_content = html_content.replace("{{SURE}}", str(sure))
            return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(content=f"<h1>Uyarı: {mesaj}</h1><p>{sure} saniye sonra kapanacak</p>", status_code=404)
