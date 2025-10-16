#!/usr/bin/env python3
import os
import subprocess

def play_sound():
    """Plays the oturum_acildi.wav file using system audio player"""
    sound_path = "rvm_sistemi/static/sounds/oturum_acildi.wav"
    
    # Check if file exists
    if not os.path.exists(sound_path):
        print(f"Ses dosyası bulunamadı: {sound_path}")
        return
    
    print("Ses çalınıyor...")
    
    # Try different audio players
    players = ['aplay', 'paplay', 'play', 'mpv', 'vlc', 'mplayer']
    
    for player in players:
        try:
            subprocess.run([player, sound_path], check=True, 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("Ses başarıyla çalındı!")
            return
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    print("Hiçbir ses çalıcı bulunamadı. Lütfen aplay, paplay, play, mpv, vlc veya mplayer yükleyin.")

def main():
    """Main function to handle user input"""
    print("Ses Deneme Programı")
    print("S tuşuna basıp Enter'a basın (çıkmak için 'q' + Enter)")
    print("-" * 40)
    
    while True:
        try:
            user_input = input("Komut: ").strip().lower()
            
            if user_input == 's':
                play_sound()
            elif user_input == 'q':
                print("Programdan çıkılıyor...")
                break
            else:
                print("Geçersiz komut. 's' + Enter veya 'q' + Enter kullanın.")
                
        except (KeyboardInterrupt, EOFError):
            print("\nProgramdan çıkılıyor...")
            break
        except Exception as e:
            print(f"Hata: {e}")

if __name__ == "__main__":
    main()