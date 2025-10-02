# Merkezi kart referansları
# Bu modül motor ve sensor kartlarına global erişim sağlar

motor = None
sensor = None

def motor_referansini_ayarla(motor_instance):
    """Motor kartı referansını ayarlar"""
    global motor
    motor = motor_instance
    print(f"[kart_referanslari] Motor referansı ayarlandı: {motor}")

def sensor_referansini_ayarla(sensor_instance):
    """Sensor kartı referansını ayarlar"""
    global sensor
    sensor = sensor_instance
    print(f"[kart_referanslari] Sensor referansı ayarlandı: {sensor}")

def motor_al():
    """Motor kartı referansını döndürür"""
    return motor

def sensor_al():
    """Sensor kartı referansını döndürür"""
    return sensor
