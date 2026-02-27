import os
from datetime import datetime

def generate_report(output_path="report.txt"):
    """Basit bir günlük rapor oluşturur."""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("--- File Organizer Pro Raporu ---\n")
            f.write(f"Oluşturulma Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("-" * 34 + "\n")
            f.write("İşlem tamamlandı. Dosyalar başarıyla organize edildi.\n")
        return True
    except Exception as e:
        print(f"Rapor oluşturma hatası: {e}")
        return False
