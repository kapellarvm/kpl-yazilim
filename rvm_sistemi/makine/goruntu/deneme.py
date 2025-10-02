
from image import capture_and_process

if __name__ == "__main__":

    while True:
        key = input("Tuş: ").strip().lower()
        if key == "a":
            print("\ncapture_and_process() çalıştırılıyor...\n")
            result = capture_and_process()
            print("Sonuç:", result)
        elif key == "q":
            print("Çıkılıyor...")
            break
        else:
            print("Geçersiz tuş. 'a' veya 'q' gir.")
    