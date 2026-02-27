import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config_loader import load_config
from organizer import Organizer
from logger import get_logger

class OrganizationHandler(FileSystemEventHandler):
    """Event handler that triggers organization on file creation."""
    def __init__(self, organizer):
        self.organizer = organizer
        self.logger = get_logger()

    def on_created(self, event):
        if event.is_directory:
            return
            
        self.logger.info(f"YENİ DOSYA TESPİT EDİLDİ: {event.src_path}")
        print(f"\nAlgılandı: {Path(event.src_path).name}")
        
        time.sleep(1) # Wait for file write to complete
        
        self.organizer.organize_file(event.src_path)

class Watcher:
    """Main Watcher class that handles scanning and monitoring."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.organizer = Organizer()
        self.observer = Observer()
        self.handler = OrganizationHandler(self.organizer)

    def scan_existing(self):
        """Scans and organizes existing files in the directory."""
        if not self.directory.exists():
            return

        print(f"--- Mevcut Dosyalar Taranıyor: {self.directory} ---")
        count = 0
        for item in self.directory.iterdir():
            if item.is_file():
                if self.organizer.organize_file(item):
                    count += 1
        print(f"--- Tarama Tamamlandı. Düzenlenen: {count} ---")

    def start(self):
        """Starts the watcher process."""
        if not self.directory.exists():
            print(f"Hata: İzlenecek klasör yok -> {self.directory}")
            return

        # 1. Initial Scan
        self.scan_existing()

        # 2. Start Monitoring
        self.observer.schedule(self.handler, str(self.directory), recursive=False)
        self.observer.start()

        print(f"İzleme başlatıldı (Kaynak: {self.directory})")
        print("Watcher modu aktif... Durdurmak için Ctrl+C")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        print("\nİzleme durduruluyor...")
        self.observer.stop()
        self.observer.join()

def start_watching():
    """Entry point used by main.py."""
    config = load_config()
    source_dir = config["source_directory"]
    
    watcher = Watcher(source_dir)
    watcher.start()

if __name__ == "__main__":
    start_watching()
