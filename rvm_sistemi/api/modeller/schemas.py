"""
Pydantic Modelleri - API Request/Response Şemaları
"""

from pydantic import BaseModel
from typing import Optional


# --- DİM-DB API Modelleri ---
class SessionStartRequest(BaseModel):
    guid: str
    sessionId: str
    userId: str


class AcceptPackageRequest(BaseModel):
    guid: str
    uuid: str
    sessionId: str
    barcode: str


class SessionEndRequest(BaseModel):
    guid: str
    sessionId: str
    slipData: str


class StopOperationRequest(BaseModel):
    guid: str
    barcode: str


class UpdateProductsRequest(BaseModel):
    guid: str
    rvm: str
    timestamp: str


class ResetRvmRequest(BaseModel):
    guid: str
    rvm: str
    timestamp: str


# --- Motor API Modelleri ---
class MotorParametreleri(BaseModel):
    konveyor_hizi: Optional[int] = None
    yonlendirici_hizi: Optional[int] = None
    klape_hizi: Optional[int] = None


class MotorHizRequest(BaseModel):
    motor: str
    hiz: int


# --- Bakım API Modelleri ---
class BakimModuRequest(BaseModel):
    aktif: bool


class BakimUrlRequest(BaseModel):
    url: str


# --- Uyarı API Modelleri ---
class UyariRequest(BaseModel):
    mesaj: str = "Lütfen şişeyi alınız"
    sure: int = 2
    suresiz: bool = False


# --- Alarm API Modelleri ---
class AlarmRequest(BaseModel):
    alarmCode: int
    alarmMessage: str


# --- Response Modelleri ---
class ApiResponse(BaseModel):
    status: str
    message: str


class ErrorResponse(BaseModel):
    errorCode: int
    errorMessage: str


class SuccessResponse(BaseModel):
    errorCode: int = 0
    errorMessage: str = ""
    message: str = ""


# --- Sistem Durumu Modelleri ---
class SistemDurumuResponse(BaseModel):
    motor_baglanti: bool
    sensor_baglanti: bool
    mevcut_durum: str
    motor_hizlari: dict


class SensorSonDegerResponse(BaseModel):
    agirlik: float
    mesaj: str
