from .senaryolar import oturum_var, oturum_yok, bakim, temizlik
from .senaryolar import uyari
from .modbus_parser import modbus_parser
from rvm_sistemi.utils.logger import log_system, log_error, log_success, log_warning
from .goruntu.goruntu_isleme_servisi import GoruntuIslemeServisi

goruntu_isleme_servisi = GoruntuIslemeServisi()

class DurumMakinesi:
    def __init__(self):
        self.durum = "oturum_yok"  # Başlangıç durumu
        self.onceki_durum = None  # Önceki durumu takip et
        self.bakim_url = "http://192.168.53.2:4321/bakim"  # Varsayılan bakım URL'i
        
    def durum_degistir(self, yeni_durum):
        print(f"Durum değiştiriliyor: {self.durum} -> {yeni_durum}")
        log_system(f"Durum değiştiriliyor: {self.durum} -> {yeni_durum}")
        self.onceki_durum = self.durum
        self.durum = yeni_durum
        
        
        # Bakım moduna giriliyorsa, otomatik ekran değişimi
        if yeni_durum == "bakim" and self.onceki_durum != "bakim":
            bakim.bakim_moduna_gir(self.bakim_url)
        
        # Bakım modundan çıkılıyorsa, ana ekrana dön
        elif self.onceki_durum == "bakim" and yeni_durum != "bakim":
            bakim.bakim_modundan_cik()
        
        # Temizlik moduna giriliyorsa, otomatik ekran değişimi
        elif yeni_durum == "temizlik" and self.onceki_durum != "temizlik":
            temizlik.temizlik_moduna_gir()
        
        # Temizlik modundan çıkılıyorsa, ana ekrana dön
        elif self.onceki_durum == "temizlik" and yeni_durum != "temizlik":
            temizlik.temizlik_modundan_cik()
        
        elif yeni_durum == "oturum_yok" and self.onceki_durum != "oturum_yok":
            uyari.uyari_kapat()

        elif yeni_durum == "oturum_var" and self.onceki_durum != "oturum_var":
            uyari.uyari_kapat()
        
        self.olayi_isle(self.durum)

    def olayi_isle(self, olay):

        if olay == "gsb":
            print("🔐 [GÜVENLİK] GSB moduna geçiliyor...")
            barkod = goruntu_isleme_servisi.goruntu_yakala_ve_isle("qr")
            print(f"🔍 [GÜVENLİK] Okunan barkod: {barkod}")
            
            if barkod == "KPL-Bakim-9G5SQ61T2Q3Q":
                print("✅ [GÜVENLİK] GSB barkodu doğrulandı, bakım moduna geçiliyor")
                self.durum_degistir("bakim")
            elif barkod == "KPL-Temizlik-9G5SQ6UTYQ3Q":
                print("✅ [GÜVENLİK] GSB barkodu doğrulandı, temizlik moduna geçiliyor")
                self.durum_degistir("temizlik")
            else:
                print("❌ [GÜVENLİK] Geçersiz GSB barkodu, oturum yok moduna dönülüyor")

        if self.durum == "oturum_yok":
            oturum_yok.olayi_isle(olay)
        elif self.durum == "oturum_var":
            oturum_var.mesaj_isle(olay)
        elif self.durum == "bakim":
            bakim.olayi_isle(olay)
        elif self.durum == "temizlik":
            temizlik.olayi_isle(olay)
        
                
    def modbus_mesaj(self, modbus_veri):
        # Modbus verisini parse et
        parsed_data = modbus_parser.parse_modbus_string(modbus_veri)
        
        if parsed_data:
            motor_id = parsed_data['motor_id']
            motor_data = parsed_data['data']
            
            # Bakım modundaysa veriyi ekrana gönder
            if self.durum == "bakim":
                self._send_modbus_to_bakim(motor_id, motor_data)
            # Temizlik modundaysa veriyi ekrana gönder
            elif self.durum == "temizlik":
                self._send_modbus_to_temizlik(motor_id, motor_data)
        
        # Eski sistem için geriye dönük uyumluluk
        if self.durum == "oturum_var":
            oturum_var.modbus_mesaj(modbus_veri)
        elif self.durum == "bakim":
            bakim.modbus_mesaj(modbus_veri)
        elif self.durum == "temizlik":
            temizlik.modbus_mesaj(modbus_veri)
    
    def _send_modbus_to_bakim(self, motor_id, motor_data):
        """Modbus verisini bakım ekranına gönderir"""
        try:
            # Motor tipini belirle
            motor_type = "crusher" if motor_id == 1 else "breaker"
            
            # Veriyi formatla
            formatted_data = modbus_parser.format_for_display(motor_data)
            
            # Konsola yazdır
            #print(f"[BAKIM] {motor_type.upper()} Motor Verisi:")
            #for key, value in formatted_data.items():
             #   print(f"  {key}: {value}")
            
            # WebSocket ile gerçek zamanlı güncelleme
            self._send_websocket_update(motor_type, formatted_data)
            
        except Exception as e:
            log_error(f"Modbus bakım gönderim hatası: {e}")
    
    def _send_modbus_to_temizlik(self, motor_id, motor_data):
        """Modbus verisini temizlik ekranına gönderir"""
        try:
            # Motor tipini belirle
            motor_type = "crusher" if motor_id == 1 else "breaker"
            
            # Veriyi formatla
            formatted_data = modbus_parser.format_for_display(motor_data)
            
            # WebSocket ile gerçek zamanlı güncelleme
            self._send_websocket_update_temizlik(motor_type, formatted_data)
            
        except Exception as e:
            log_error(f"Modbus temizlik gönderim hatası: {e}")
    
    def _send_websocket_update(self, motor_type, formatted_data):
        """WebSocket ile bakım ekranına güncelleme gönder"""
        try:
            # WebSocket modülünü import et
            from ..api.endpoints.websocket import send_modbus_data_to_bakim
            import asyncio
            
            # Asyncio event loop'u al veya oluştur
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # WebSocket mesajını gönder
            if loop.is_running():
                # Eğer loop çalışıyorsa, task olarak ekle
                asyncio.create_task(send_modbus_data_to_bakim(motor_type, formatted_data))
            else:
                # Eğer loop çalışmıyorsa, çalıştır
                loop.run_until_complete(send_modbus_data_to_bakim(motor_type, formatted_data))
                
        except Exception as e:
            log_error(f"WebSocket güncelleme hatası: {e}")
    
    def _send_websocket_update_temizlik(self, motor_type, formatted_data):
        """WebSocket ile temizlik ekranına güncelleme gönder"""
        try:
            # WebSocket modülünü import et
            from ..api.endpoints.websocket import send_modbus_data_to_temizlik
            import asyncio
            
            # Asyncio event loop'u al veya oluştur
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # WebSocket mesajını gönder
            if loop.is_running():
                # Eğer loop çalışıyorsa, task olarak ekle
                asyncio.create_task(send_modbus_data_to_temizlik(motor_type, formatted_data))
            else:
                # Eğer loop çalışmıyorsa, çalıştır
                loop.run_until_complete(send_modbus_data_to_temizlik(motor_type, formatted_data))
                
        except Exception as e:
            log_error(f"Temizlik WebSocket güncelleme hatası: {e}")
            

durum_makinesi = DurumMakinesi()
