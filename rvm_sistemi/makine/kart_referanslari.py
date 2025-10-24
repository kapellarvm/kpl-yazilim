# Merkezi kart referansları
# Bu modül motor ve sensor kartlarına global erişim sağlar

motor = None
sensor = None
ac_motor_kontrol = None
port_saglik_servisi = None

def motor_referansini_ayarla(motor_instance):
    """Motor kartı referansını ayarlar"""
    global motor
    motor = motor_instance
    #print(f"[kart_referanslari] Motor referansı ayarlandı: {motor}")

def sensor_referansini_ayarla(sensor_instance):
    """Sensor kartı referansını ayarlar"""
    global sensor
    sensor = sensor_instance
    #print(f"[kart_referanslari] Sensor referansı ayarlandı: {sensor}")

def motor_al():
    """Motor kartı referansını döndürür"""
    return motor

def sensor_al():
    """Sensor kartı referansını döndürür"""
    return sensor

def ac_motor_kontrol_referansini_ayarla(ac_motor_instance):
    """AC Motor kontrol referansını ayarlar"""
    global ac_motor_kontrol
    ac_motor_kontrol = ac_motor_instance
    #print(f"[kart_referanslari] AC Motor kontrol referansı ayarlandı: {ac_motor_kontrol}")

def ac_motor_kontrol_al():
    """AC Motor kontrol referansını döndürür"""
    return ac_motor_kontrol

def port_saglik_servisi_referansini_ayarla(port_saglik_instance):
    """Port Sağlık Servisi referansını ayarlar"""
    global port_saglik_servisi
    port_saglik_servisi = port_saglik_instance

def port_saglik_servisi_al():
    """Port Sağlık Servisi referansını döndürür"""
    return port_saglik_servisi
