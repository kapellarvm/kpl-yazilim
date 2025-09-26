import sys
import threading
import time
import schedule

# Projenin diğer modüllerini doğru paket yolundan import et
from rvm_sistemi.dimdb import sunucu, istemci


# --- ARKA PLAN GÖREVLERİ ---

def run_web_server():
    """
    DİM DB'den gelen istekleri dinleyecek olan Flask sunucusunu başlatır.
    """
    print("Web sunucusu başlatılıyor...")
    sunucu.app.run(host='0.0.0.0', port=4321, debug=False, use_reloader=False)

def start_periodic_tasks():
    """
    Periyodik olarak çalışması gereken istemci görevlerini yönetir.
    """
    print("Periyodik görevler zamanlanıyor...")
    schedule.every(60).seconds.do(istemci.send_heartbeat)

    while True:
        schedule.run_pending()
        time.sleep(1)

def graceful_shutdown():
    """
    Program kapatılırken aktif bir oturum olup olmadığını kontrol eder
    ve varsa, oturum bilgilerini DİM-DB'ye gönderir.
    """
    print("\nKapatma işlemi başlatıldı...")
    if sunucu.is_session_active():
        print("Aktif bir oturum bulundu, veriler gönderiliyor...")
        sunucu.handle_graceful_shutdown()
        # İsteğin gönderilmesi için kısa bir bekleme süresi
        time.sleep(2)
    else:
        print("Aktif oturum bulunamadı. Temiz çıkış yapılıyor.")
    
    print("Program sonlandırıldı.")
    sys.exit(0)

# --- ANA UYGULAMA GİRİŞ NOKTASI ---

if __name__ == '__main__':
    print("RVM Sistemi Arka Plan Servisleri Başlatılıyor...")

    # Arka plan görevleri için thread'leri başlat
    server_thread = threading.Thread(target=run_web_server, name="WebServerThread")
    server_thread.daemon = True
    server_thread.start()

    tasks_thread = threading.Thread(target=start_periodic_tasks, name="PeriodicTasksThread")
    tasks_thread.daemon = True
    tasks_thread.start()

    print("Servisler çalışıyor. Çıkmak için CTRL+C'ye basın.")
    try:
        # Ana thread'in kapanmasını ve programın sonlanmasını engelle
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        graceful_shutdown()

