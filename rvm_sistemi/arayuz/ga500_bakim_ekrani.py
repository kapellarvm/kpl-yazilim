"""
GA500 Bakım Ekranı
=================
GA500 Modbus verilerini görüntüleme ve kontrol etme arayüzü
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time

# GA500 merkezi yöneticisini import et
from ..makine.modbus import ga500_yonetici


class GA500BakimEkrani:
    def __init__(self, master=None):
        self.master = master if master else tk.Tk()
        self.master.title("GA500 Bakım ve İzleme Ekranı")
        self.master.geometry("800x600")
        
        # İzleme durumu
        self.izleme_aktif = False
        self.izleme_thread = None
        
        self.arayuz_olustur()
        self.ga500_baslat()
        
    def arayuz_olustur(self):
        """Ana arayüz elemanlarını oluştur"""
        
        # Ana çerçeve
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Başlık
        title_label = ttk.Label(main_frame, text="GA500 Modbus Bakım Ekranı", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Kontrol butonları
        self.kontrol_cercevesi_olustur(main_frame)
        
        # Durum göstergeleri
        self.durum_cercevesi_olustur(main_frame)
        
        # Log alanı
        self.log_cercevesi_olustur(main_frame)
        
        # Grid ağırlıkları
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
    
    def kontrol_cercevesi_olustur(self, parent):
        """Kontrol butonları çerçevesi"""
        control_frame = ttk.LabelFrame(parent, text="Kontrol", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 10), pady=(0, 10))
        
        # Print kontrolleri
        ttk.Button(control_frame, text="Print Aç", 
                  command=self.print_ac).grid(row=0, column=0, padx=5, pady=2)
        ttk.Button(control_frame, text="Print Kapat", 
                  command=self.print_kapat).grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(control_frame, text="Detaylı Print", 
                  command=self.detayli_print_ac).grid(row=0, column=2, padx=5, pady=2)
        
        # Rapor butonları
        ttk.Button(control_frame, text="Durum Raporu", 
                  command=self.durum_raporu_goster).grid(row=1, column=0, padx=5, pady=2)
        ttk.Button(control_frame, text="Özet Durum", 
                  command=self.ozet_durum_goster).grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(control_frame, text="Sistem Sağlığı", 
                  command=self.sistem_sagligi_kontrol).grid(row=1, column=2, padx=5, pady=2)
        
        # İzleme kontrolleri
        self.izleme_button = ttk.Button(control_frame, text="İzlemeyi Başlat", 
                                       command=self.izleme_toggle)
        self.izleme_button.grid(row=2, column=0, padx=5, pady=2)
        
        ttk.Button(control_frame, text="Verileri Temizle", 
                  command=self.verileri_temizle).grid(row=2, column=1, padx=5, pady=2)
        ttk.Button(control_frame, text="Yenile", 
                  command=self.durumlari_guncelle).grid(row=2, column=2, padx=5, pady=2)
    
    def durum_cercevesi_olustur(self, parent):
        """Durum göstergeleri çerçevesi"""
        status_frame = ttk.LabelFrame(parent, text="Motor Durumları", padding="10")
        status_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10), pady=(0, 10))
        
        # Ezici Motor
        ezici_frame = ttk.LabelFrame(status_frame, text="Ezici Motor (Sürücü 1)", padding="5")
        ezici_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        self.ezici_labels = self.motor_labels_olustur(ezici_frame)
        
        # Kırıcı Motor
        kirici_frame = ttk.LabelFrame(status_frame, text="Kırıcı Motor (Sürücü 2)", padding="5")
        kirici_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.kirici_labels = self.motor_labels_olustur(kirici_frame)
        
        status_frame.columnconfigure(0, weight=1)
    
    def motor_labels_olustur(self, parent):
        """Motor durum label'larını oluştur"""
        labels = {}
        
        # Akım
        ttk.Label(parent, text="Akım:").grid(row=0, column=0, sticky=tk.W)
        labels['akim'] = ttk.Label(parent, text="0.0 A", foreground="blue")
        labels['akim'].grid(row=0, column=1, sticky=tk.W)
        
        # Frekans
        ttk.Label(parent, text="Frekans:").grid(row=1, column=0, sticky=tk.W)
        labels['frekans'] = ttk.Label(parent, text="0.0 Hz", foreground="blue")
        labels['frekans'].grid(row=1, column=1, sticky=tk.W)
        
        # Sıcaklık
        ttk.Label(parent, text="Sıcaklık:").grid(row=2, column=0, sticky=tk.W)
        labels['sicaklik'] = ttk.Label(parent, text="0 °C", foreground="blue")
        labels['sicaklik'].grid(row=2, column=1, sticky=tk.W)
        
        # Durum
        ttk.Label(parent, text="Durum:").grid(row=3, column=0, sticky=tk.W)
        labels['durum'] = ttk.Label(parent, text="Bilinmiyor", foreground="gray")
        labels['durum'].grid(row=3, column=1, sticky=tk.W)
        
        # Arıza
        ttk.Label(parent, text="Arıza:").grid(row=4, column=0, sticky=tk.W)
        labels['ariza'] = ttk.Label(parent, text="Yok", foreground="green")
        labels['ariza'].grid(row=4, column=1, sticky=tk.W)
        
        return labels
    
    def log_cercevesi_olustur(self, parent):
        """Log alanı çerçevesi"""
        log_frame = ttk.LabelFrame(parent, text="Sistem Logları", padding="10")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Log temizle butonu
        ttk.Button(log_frame, text="Logları Temizle", 
                  command=self.loglari_temizle).grid(row=1, column=0, pady=(5, 0))
        
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def ga500_baslat(self):
        """GA500 sistemini başlat"""
        try:
            ga500_yonetici.hizli_baslat(print_etkin=False, detayli=False)
            self.log_ekle("✅ GA500 Yönetici başlatıldı")
        except Exception as e:
            self.log_ekle(f"❌ GA500 başlatma hatası: {e}")
    
    def log_ekle(self, mesaj):
        """Log alanına mesaj ekle"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {mesaj}\n"
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def print_ac(self):
        """GA500 print'ini aç"""
        ga500_yonetici.print_ac()
        self.log_ekle("🔊 GA500 print açıldı")
    
    def print_kapat(self):
        """GA500 print'ini kapat"""
        ga500_yonetici.print_kapat()
        self.log_ekle("🔇 GA500 print kapatıldı")
    
    def detayli_print_ac(self):
        """GA500 detaylı print'ini aç"""
        ga500_yonetici.detayli_print_ac()
        self.log_ekle("🔍 GA500 detaylı print açıldı")
    
    def durum_raporu_goster(self):
        """Durum raporunu ayrı pencerede göster"""
        try:
            rapor = ga500_yonetici.sistem_saglik_raporu()
            
            # Yeni pencere oluştur
            rapor_window = tk.Toplevel(self.master)
            rapor_window.title("GA500 Durum Raporu")
            rapor_window.geometry("500x400")
            
            # Rapor text alanı
            rapor_text = scrolledtext.ScrolledText(rapor_window, wrap=tk.WORD)
            rapor_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Rapor içeriğini oluştur
            rapor_icerik = self.rapor_icerik_olustur(rapor)
            rapor_text.insert(tk.END, rapor_icerik)
            rapor_text.config(state=tk.DISABLED)
            
            self.log_ekle("📊 Durum raporu görüntülendi")
        except Exception as e:
            self.log_ekle(f"❌ Rapor gösterme hatası: {e}")
    
    def rapor_icerik_olustur(self, rapor):
        """Rapor içeriğini text formatında oluştur"""
        icerik = "═══════════════════════════════════\n"
        icerik += "       GA500 DURUM RAPORU\n"
        icerik += "═══════════════════════════════════\n\n"
        
        # Genel sağlık
        saglik_ikonu = "✅" if rapor['genel_saglik'] else "❌"
        icerik += f"Genel Durum: {saglik_ikonu}\n\n"
        
        # Bağlantı durumları
        icerik += "Bağlantı Durumu:\n"
        for slave_id, bagli in rapor['baglanti_durumu'].items():
            durum_ikonu = "🟢" if bagli else "🔴"
            icerik += f"  Sürücü {slave_id}: {durum_ikonu}\n"
        
        icerik += "\nMotor Durumları:\n"
        for motor_adi, durum in rapor['motor_durumlari'].items():
            motor_ikonu = "✅" if not durum['ariza'] else "❌"
            icerik += f"  {motor_adi.title()}: {motor_ikonu}\n"
            icerik += f"    Akım: {durum['akim']:.1f} A\n"
            icerik += f"    Frekans: {durum['frekans']:.1f} Hz\n"
            icerik += f"    Sıcaklık: {durum['sicaklik']} °C\n"
            icerik += f"    Durum: {durum['durum']}\n\n"
        
        # Sorunlar
        if rapor['sorunlar']:
            icerik += "Tespit Edilen Sorunlar:\n"
            for sorun in rapor['sorunlar']:
                icerik += f"  ⚠️ {sorun}\n"
        else:
            icerik += "✅ Herhangi bir sorun tespit edilmedi.\n"
        
        return icerik
    
    def ozet_durum_goster(self):
        """Özet durum göster"""
        try:
            durum_text = "📊 GA500 Özet Durum:\n"
            
            ezici_durum = ga500_yonetici.motor_durumu_al(1)
            kirici_durum = ga500_yonetici.motor_durumu_al(2)
            
            durum_text += f"  Ezici: {ezici_durum['akim']:.1f}A, "
            durum_text += f"{ezici_durum['frekans']:.1f}Hz, {ezici_durum['sicaklik']}°C\n"
            durum_text += f"  Kırıcı: {kirici_durum['akim']:.1f}A, "
            durum_text += f"{kirici_durum['frekans']:.1f}Hz, {kirici_durum['sicaklik']}°C"
            
            messagebox.showinfo("Özet Durum", durum_text)
            self.log_ekle("📋 Özet durum görüntülendi")
        except Exception as e:
            self.log_ekle(f"❌ Özet durum hatası: {e}")
    
    def sistem_sagligi_kontrol(self):
        """Sistem sağlığını kontrol et"""
        try:
            saglik = ga500_yonetici.get_sistem_durumu()
            durum_text = "✅ Sistem sağlıklı" if saglik else "❌ Sistem sorunlu"
            messagebox.showinfo("Sistem Sağlığı", durum_text)
            self.log_ekle(f"🏥 Sistem sağlığı: {'Sağlıklı' if saglik else 'Sorunlu'}")
        except Exception as e:
            self.log_ekle(f"❌ Sağlık kontrol hatası: {e}")
    
    def izleme_toggle(self):
        """İzlemeyi başlat/durdur"""
        if not self.izleme_aktif:
            self.izleme_baslat()
        else:
            self.izleme_durdur()
    
    def izleme_baslat(self):
        """Canlı izlemeyi başlat"""
        self.izleme_aktif = True
        self.izleme_button.config(text="İzlemeyi Durdur")
        self.izleme_thread = threading.Thread(target=self.izleme_dongusu, daemon=True)
        self.izleme_thread.start()
        self.log_ekle("🔄 Canlı izleme başlatıldı")
    
    def izleme_durdur(self):
        """Canlı izlemeyi durdur"""
        self.izleme_aktif = False
        self.izleme_button.config(text="İzlemeyi Başlat")
        self.log_ekle("⏹️ Canlı izleme durduruldu")
    
    def izleme_dongusu(self):
        """Canlı izleme döngüsü"""
        while self.izleme_aktif:
            try:
                self.durumlari_guncelle()
                time.sleep(1)  # 1 saniyede bir güncelle
            except Exception as e:
                self.log_ekle(f"❌ İzleme hatası: {e}")
                break
    
    def durumlari_guncelle(self):
        """Motor durumlarını güncelle"""
        try:
            # Ezici motor
            ezici_durum = ga500_yonetici.motor_durumu_al(1)
            self.motor_durumu_guncelle(self.ezici_labels, ezici_durum)
            
            # Kırıcı motor
            kirici_durum = ga500_yonetici.motor_durumu_al(2)
            self.motor_durumu_guncelle(self.kirici_labels, kirici_durum)
            
        except Exception as e:
            self.log_ekle(f"❌ Durum güncelleme hatası: {e}")
    
    def motor_durumu_guncelle(self, labels, durum):
        """Motor label'larını güncelle"""
        # Akım
        labels['akim'].config(text=f"{durum['akim']:.1f} A")
        if durum['akim'] > 3.0:
            labels['akim'].config(foreground="red")
        elif durum['akim'] > 1.0:
            labels['akim'].config(foreground="orange")
        else:
            labels['akim'].config(foreground="blue")
        
        # Frekans
        labels['frekans'].config(text=f"{durum['frekans']:.1f} Hz")
        
        # Sıcaklık
        labels['sicaklik'].config(text=f"{durum['sicaklik']} °C")
        if durum['sicaklik'] > 70:
            labels['sicaklik'].config(foreground="red")
        elif durum['sicaklik'] > 50:
            labels['sicaklik'].config(foreground="orange")
        else:
            labels['sicaklik'].config(foreground="blue")
        
        # Durum
        labels['durum'].config(text=durum['durum'])
        if durum['durum'] == "Çalışıyor":
            labels['durum'].config(foreground="green")
        else:
            labels['durum'].config(foreground="gray")
        
        # Arıza
        if durum['ariza']:
            labels['ariza'].config(text="VAR", foreground="red")
        else:
            labels['ariza'].config(text="YOK", foreground="green")
    
    def verileri_temizle(self):
        """GA500 verilerini temizle"""
        try:
            ga500_yonetici.temizle()
            self.log_ekle("🧹 GA500 verileri temizlendi")
            self.durumlari_guncelle()
        except Exception as e:
            self.log_ekle(f"❌ Veri temizleme hatası: {e}")
    
    def loglari_temizle(self):
        """Log alanını temizle"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def kapat(self):
        """Pencereyi kapat"""
        if self.izleme_aktif:
            self.izleme_durdur()
        self.master.quit()
        self.master.destroy()


def main():
    """Ana program"""
    app = GA500BakimEkrani()
    app.master.protocol("WM_DELETE_WINDOW", app.kapat)
    app.master.mainloop()


if __name__ == "__main__":
    main()