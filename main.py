import sys
import os

# src klasörünü path'e ekle (Modüllerin birbirini bulması için)
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, 'src')
sys.path.append(src_dir)

from watcher import start_watching
from reporter import generate_report
from organizer import Organizer
from filter_engine import FilterEngine

def prompt_list(prompt_text: str) -> list:
    raw = input(prompt_text + " (virgülle ayır, boş bırakma): ")
    if not raw.strip():
        return []
    return [p.strip() for p in raw.split(',') if p.strip()]

def main():
    print("DOSYA DÜZENLEME OTOMASYONU v1.0")
    print("1. Mevcut Klasörü Düzenle (Tara ve Taşı)")
    print("2. Otomatik İzlemeyi Başlat (Watcher Modu)")
    print("3. Rapor Al")
    print("4. Filtre Motorunu Çalıştır (FilterEngine)")
    print("4. Çıkış")
    
    secim = input("Seçiminiz (1-4): ")
    
    if secim == '1':
        print("Tarama başlıyor...")
        org = Organizer()
        org.scan_directory()
    elif secim == '2':
        start_watching()
    elif secim == '3':
        generate_report()
    elif secim == '4':
        # Interactive FilterEngine run
        engine = FilterEngine()
        print('\n== Filter Engine Çalıştırma ==')
        exts = prompt_list('Uzantılar (örn: .jpg,.png)')
        cats = prompt_list('Kategoriler (örn: Images,Documents)')
        try:
            min_mb = float(input('Min boyut (MB, boş bırak = 0): ') or 0)
        except ValueError:
            min_mb = 0
        try:
            max_mb_in = input('Max boyut (MB, boş = boş bırakmak için Enter): ')
            max_mb = float(max_mb_in) if max_mb_in.strip() else float('inf')
        except ValueError:
            max_mb = float('inf')

        print('Mod seçin: 1=organize, 2=archive, 3=both')
        mode_choice = input('Mod: ')
        mode_map = {'1': 'organize', '2': 'archive', '3': 'both'}
        mode = mode_map.get(mode_choice, 'organize')

        filter_conf = {
            'size_min_mb': min_mb,
            'size_max_mb': max_mb,
            'extensions': exts,
            'categories': cats,
            'use_category_folders': True,
            'archive_name': 'filtered_archive.zip'
        }

        results = engine.execute(filter_conf, organize_mode=mode)
        print('\n== İşlem Sonuçları ==')
        print(results)
        # Rapor oluştur
        try:
            generate_report()
        except Exception:
            pass
    elif secim == '4':
        sys.exit()
    else:
        print("Geçersiz seçim.")

if __name__ == "__main__":
    main()