#!/usr/bin/env python3
"""
System State Manager Test Script
Sistem durumunu kontrol eder
"""

import sys
import os
sys.path.append('/home/sshuser/projects/kpl-yazilim')

from rvm_sistemi.makine.seri.system_state_manager import system_state

def main():
    print("🔍 SYSTEM STATE MANAGER DURUMU")
    print("=" * 50)
    
    # Sistem durumu özeti
    status = system_state.get_status_summary()
    
    print(f"📊 Sistem Durumu: {status['system_state']}")
    print(f"🔄 Aktif Reset: {status['active_reset']}")
    print(f"⏳ Sistem Meşgul: {status['system_busy']}")
    print(f"🧵 Aktif Thread'ler: {status['active_threads']}")
    print(f"🔌 Reconnecting Kartlar: {status['reconnecting_cards']}")
    
    print("\n💳 KART DURUMLARI:")
    for card, state in status['card_states'].items():
        print(f"  {card}: {state}")
    
    print(f"\n⏰ Son Reset: {status['last_reset_time']}")
    
    # Reset yapılabilir mi?
    can_reset = system_state.can_start_reset()
    print(f"\n🔧 Reset Yapılabilir: {'✅' if can_reset else '❌'}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
