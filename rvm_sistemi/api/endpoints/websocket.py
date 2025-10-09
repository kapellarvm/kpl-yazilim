"""
WebSocket API Endpoint'leri
Gerçek zamanlı veri güncellemeleri için WebSocket bağlantıları
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
from ..modeller.schemas import SuccessResponse, ErrorResponse

router = APIRouter(prefix="/ws", tags=["WebSocket"])

class ConnectionManager:
    """WebSocket bağlantı yöneticisi"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.bakim_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket, connection_type: str = "general"):
        """Yeni WebSocket bağlantısı kabul et"""
        await websocket.accept()
        
        if connection_type == "bakim":
            self.bakim_connections.append(websocket)
            print(f"[WebSocket] Bakım bağlantısı eklendi. Toplam: {len(self.bakim_connections)}")
        else:
            self.active_connections.append(websocket)
            print(f"[WebSocket] Genel bağlantı eklendi. Toplam: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, connection_type: str = "general"):
        """WebSocket bağlantısını kapat"""
        if connection_type == "bakim":
            if websocket in self.bakim_connections:
                self.bakim_connections.remove(websocket)
        else:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        
        print(f"WebSocket bağlantısı kapatıldı. Tip: {connection_type}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Belirli bir WebSocket'e mesaj gönder"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"WebSocket mesaj gönderme hatası: {e}")
    
    async def broadcast_to_bakim(self, message: str):
        """Tüm bakım ekranı bağlantılarına mesaj gönder"""
        if not self.bakim_connections:
            return
        
        disconnected = []
        for connection in self.bakim_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"[WebSocket] Bakım broadcast hatası: {e}")
                disconnected.append(connection)
        
        # Bağlantısı kopanları temizle
        for connection in disconnected:
            self.bakim_connections.remove(connection)
    
    async def broadcast(self, message: str):
        """Tüm aktif bağlantılara mesaj gönder"""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Broadcast hatası: {e}")
                disconnected.append(connection)
        
        # Bağlantısı kopanları temizle
        for connection in disconnected:
            self.active_connections.remove(connection)

# Global connection manager
manager = ConnectionManager()

@router.websocket("/bakim")
async def websocket_bakim(websocket: WebSocket):
    """Bakım ekranı için WebSocket bağlantısı"""
    await manager.connect(websocket, "bakim")
    
    try:
        # Bağlantı kurulduğunda test mesajı gönder
        await manager.send_personal_message("WebSocket bağlantısı kuruldu!", websocket)
        
        while True:
            # Client'tan gelen mesajları dinle
            data = await websocket.receive_text()
            # Echo mesajı gönder
            await manager.send_personal_message(f"Echo: {data}", websocket)
            
    except WebSocketDisconnect:
        print("[WebSocket] Client bağlantıyı kapattı")
        manager.disconnect(websocket, "bakim")
    except Exception as e:
        print(f"[WebSocket] Bakım WebSocket hatası: {e}")
        manager.disconnect(websocket, "bakim")

@router.websocket("/general")
async def websocket_general(websocket: WebSocket):
    """Genel WebSocket bağlantısı"""
    await manager.connect(websocket, "general")
    
    try:
        while True:
            # Client'tan gelen mesajları dinle
            data = await websocket.receive_text()
            
            # Echo mesajı gönder
            await manager.send_personal_message(f"Echo: {data}", websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, "general")
    except Exception as e:
        print(f"Genel WebSocket hatası: {e}")
        manager.disconnect(websocket, "general")

# Modbus veri gönderme fonksiyonları
async def send_modbus_data_to_bakim(motor_type: str, motor_data: Dict[str, Any]):
    """Modbus verisini bakım ekranına gönder"""
    try:
        message = {
            "type": "modbus_update",
            "motor_type": motor_type,
            "data": motor_data,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await manager.broadcast_to_bakim(json.dumps(message))
        
    except Exception as e:
        print(f"Modbus veri gönderme hatası: {e}")

async def send_system_status_to_bakim(status_data: Dict[str, Any]):
    """Sistem durumunu bakım ekranına gönder"""
    try:
        message = {
            "type": "system_status",
            "data": status_data,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await manager.broadcast_to_bakim(json.dumps(message))
        
    except Exception as e:
        print(f"Sistem durum gönderme hatası: {e}")

async def send_sensor_data_to_bakim(sensor_data: Dict[str, Any]):
    """Sensör verisini bakım ekranına gönder"""
    try:
        message = {
            "type": "sensor_update",
            "data": sensor_data,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await manager.broadcast_to_bakim(json.dumps(message))
        
    except Exception as e:
        print(f"Sensör veri gönderme hatası: {e}")

async def send_alarm_data_to_bakim(alarm_data: Dict[str, Any]):
    """Alarm verisini bakım ekranına gönder"""
    try:
        message = {
            "type": "alarm_update",
            "data": alarm_data,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await manager.broadcast_to_bakim(json.dumps(message))
        
    except Exception as e:
        print(f"Alarm veri gönderme hatası: {e}")

@router.get("/status")
async def websocket_status():
    """WebSocket bağlantı durumunu döndürür"""
    return {
        "status": "success",
        "bakim_connections": len(manager.bakim_connections),
        "general_connections": len(manager.active_connections),
        "total_connections": len(manager.bakim_connections) + len(manager.active_connections)
    }

@router.post("/test-alarm")
async def test_alarm(alarm_type: str = "kma"):
    """Test için alarm mesajı gönder"""
    try:
        # Alarm verisini hazırla
        alarm_data = {}
        
        if alarm_type == "kma":
            alarm_data['konveyor_alarm'] = True
        elif alarm_type == "yma":
            alarm_data['yonlendirici_alarm'] = True
        elif alarm_type == "sma":
            alarm_data['seperator_alarm'] = True
        elif alarm_type == "kmk":
            alarm_data['konveyor_alarm'] = False
        elif alarm_type == "ymk":
            alarm_data['yonlendirici_alarm'] = False
        elif alarm_type == "smk":
            alarm_data['seperator_alarm'] = False
        else:
            return {"status": "error", "message": "Geçersiz alarm tipi"}
        
        # WebSocket'e gönder
        await send_alarm_data_to_bakim(alarm_data)
        
        return {
            "status": "success",
            "message": f"Test alarm gönderildi: {alarm_type}",
            "alarm_data": alarm_data
        }
        
    except Exception as e:
        return {"status": "error", "message": f"Test alarm hatası: {str(e)}"}
