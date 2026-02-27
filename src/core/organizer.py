import shutil
from pathlib import Path
from config_loader import load_config
from logger import get_logger
from reporter import generate_report
from db_manager import DBManager
import datetime
import os
import mimetypes

class Organizer:
    def __init__(self):
        # Config ve Logger yükle (Hata almamak için güvenli yükleme)
        self.config = load_config()
        self.logger = get_logger()
        
        self.source_dir = Path(self.config["source_directory"])
        self.dest_dir = Path(self.config["destination_directory"])
        self.extensions_map = self.config["file_extensions"]
        self.db = DBManager()
        
        # Cleaner kontrolü
        try:
            from cleaner import sanitize_filename
            self.sanitize_filename = sanitize_filename
        except ImportError:
            self.sanitize_filename = lambda name: name.lower().replace(" ", "_")

    def _get_unique_path(self, target_folder, clean_name):
        """Generates a unique path to avoid overwriting existing files."""
        destination_path = target_folder / clean_name
        
        if not destination_path.exists():
            return destination_path
            
        counter = 1
        stem = Path(clean_name).stem
        suffix = Path(clean_name).suffix
        
        while True:
            new_name = f"{stem}_{counter}{suffix}"
            candidate_path = target_folder / new_name
            if not candidate_path.exists():
                return candidate_path
            counter += 1

    def _handle_backup(self, file_path):
        """Creates a timestamped copy of the file in the backups folder if enabled."""
        if not self.config.get("backup_enabled", False):
            return
            
        try:
            backup_root = Path("backups")
            date_folder = datetime.datetime.now().strftime("%Y-%m-%d")
            backup_dir = backup_root / date_folder
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Original filename for backup
            dest_backup = backup_dir / Path(file_path).name
            
            # If exists, add unique suffix
            if dest_backup.exists():
                stem = dest_backup.stem
                suffix = dest_backup.suffix
                time_str = datetime.datetime.now().strftime("%H%M%S")
                dest_backup = backup_dir / f"{stem}_{time_str}{suffix}"
                
            shutil.copy2(str(file_path), str(dest_backup))
            self.logger.info(f"YEDEK ALINDI: {file_path.name} -> {dest_backup.parent}")
        except Exception as e:
            self.logger.error(f"Yedekleme Hatası: {e}")

    def organize_file(self, file_path):
        """Watcher için tekil dosya organizasyonu."""
        file_path = Path(file_path)
        
        # Temel kontroller
        if not file_path.exists() or file_path.is_dir():
            print(f"Atlandı (Klasör veya Yok): {file_path}")
            return False
            
        if file_path.suffix in ['.tmp', '.crdownload', '.part']:
            return False

        # Rapor dosyalarını görmezden gel (Sonsuz döngüyü önlemek için)
        if file_path.name == "report.txt" or (file_path.name.startswith("report_") and file_path.suffix == ".txt"):
            return False

        # 1. Kategori Bulma
        file_extension = file_path.suffix.lower()
        found_category = None
        
        # Önce Özel Modelleri Kontrol Et
        custom_models = self.config.get("models", [])
        import fnmatch
        for model in custom_models:
            if not model.get("active", True):
                continue
            
            patterns = [p.strip() for p in model.get("pattern", "").split(",")]
            for pattern in patterns:
                if fnmatch.fnmatch(file_path.name, pattern):
                    found_category = model.get("target")
                    break
            if found_category:
                break
        
        # Özel model yoksa varsayılanlara bak
        if not found_category:
            found_category = "Others"
            for category, extensions in self.extensions_map.items():
                if file_extension in extensions:
                    found_category = category
                    break
        
        # 2. Hedef Klasör
        target_folder = self.dest_dir / found_category
        target_folder.mkdir(parents=True, exist_ok=True)
        
        # 3. İsim Temizleme & Yedekleme
        self.config = load_config() # Canlı ayar kontrolü
        
        if self.config.get("backup_enabled", False):
            self._handle_backup(file_path)
            
        if self.config.get("clean_names", True):
            clean_name = self.sanitize_filename(file_path.name)
        else:
            clean_name = file_path.name
            
        destination_path = self._get_unique_path(target_folder, clean_name)
        
        # 4. Taşıma
        try:
            shutil.move(str(file_path), str(destination_path))
            
            log_msg = f"TASINDI | {found_category} | {file_path.name} -> {destination_path.name}"
            self.logger.info(log_msg)
            print(f"✔ [OK] {found_category}: {destination_path.name}")
            
            # --- DB'YE KAYDET ---
            try:
                stats = os.stat(destination_path)
                mime_type, _ = mimetypes.guess_type(str(destination_path))
                file_metadata = {
                    'name': destination_path.name,
                    'ext': destination_path.suffix.lower(),
                    'mime': mime_type or 'unknown',
                    'size': stats.st_size,
                    'created': datetime.datetime.fromtimestamp(stats.st_ctime).isoformat(),
                    'modified': datetime.datetime.fromtimestamp(stats.st_mtime).isoformat(),
                    'accessed': datetime.datetime.fromtimestamp(stats.st_atime).isoformat()
                }
                self.db.log_move(file_metadata, file_path, destination_path)
            except Exception as db_e:
                print(f"DB Kayıt Hatası: {db_e}")

            # --- Raporu Güncelle (Kullanıcı İsteği) ---
            try:
                generate_report()
            except Exception as e:
                print(f"Rapor güncellenemedi: {e}")
                
            return True
            
        except PermissionError:
            self.logger.error(f"ERİŞİM HATASI | {file_path.name} dosyası kullanımda.")
        except Exception as e:
            self.logger.error(f"HATA | {file_path.name} taşınamadı: {e}")
        
        return False

    def organize_folder(self, folder_path):
        """Klasörleri organize eder."""
        folder_path = Path(folder_path)
        
        # Klasör kontrolü
        if not folder_path.exists() or not folder_path.is_dir():
            print(f"Atlandı (Dosya veya Yok): {folder_path}")
            return False
        
        # JSON'daki tanımlı kategorileri al
        defined_categories = set(self.extensions_map.keys())
        defined_categories.add("Others")  # Others kategorisi de dahil
        
        # Eğer klasör adı tanımlı kategorilerden biriyse, atla
        if folder_path.name in defined_categories or folder_path.name == "folders":
            print(f"Atlandı (Tanımlı Kategori): {folder_path.name}")
            return False
        
        # Hedef klasör: folders
        target_folder = self.dest_dir / "folders"
        target_folder.mkdir(parents=True, exist_ok=True)
        
        # Hedef yol
        destination_path = target_folder / folder_path.name
        
        # Eğer aynı isimde klasör varsa, benzersiz isim oluştur
        if destination_path.exists():
            counter = 1
            while True:
                new_name = f"{folder_path.name}_{counter}"
                candidate_path = target_folder / new_name
                if not candidate_path.exists():
                    destination_path = candidate_path
                    break
                counter += 1
        
        # Taşıma
        try:
            shutil.move(str(folder_path), str(destination_path))
            
            log_msg = f"KLASÖR TASINDI | folders | {folder_path.name} -> {destination_path.name}"
            self.logger.info(log_msg)
            print(f"✔ [OK] Klasör: {destination_path.name}")
            
            # --- DB'YE KAYDET ---
            try:
                stats = os.stat(destination_path)
                file_metadata = {
                    'name': destination_path.name,
                    'ext': '[FOLDER]',
                    'mime': 'directory',
                    'size': 0, # Klasör boyutu hesaplaması pahalı olduğu için 0
                    'created': datetime.datetime.fromtimestamp(stats.st_ctime).isoformat(),
                    'modified': datetime.datetime.fromtimestamp(stats.st_mtime).isoformat(),
                    'accessed': datetime.datetime.fromtimestamp(stats.st_atime).isoformat()
                }
                self.db.log_move(file_metadata, folder_path, destination_path)
            except Exception as db_e:
                print(f"DB Kayıt Hatası: {db_e}")

            # Raporu güncelle
            try:
                generate_report()
            except Exception as e:
                print(f"Rapor güncellenemedi: {e}")
            
            return True
            
        except PermissionError:
            self.logger.error(f"ERİŞİM HATASI | {folder_path.name} klasörü kullanımda.")
        except Exception as e:
            self.logger.error(f"HATA | {folder_path.name} klasörü taşınamadı: {e}")
        
        return False

    async def move_specific_files(self, to_move_list, custom_dest=None):
        """Selected files move with DB logging."""
        count = 0
        dest_root = Path(custom_dest) if custom_dest else self.dest_dir
        
        for item in to_move_list:
            try:
                src_path = Path(item["path"])
                target_folder = dest_root / item["target_folder"]
                target_folder.mkdir(parents=True, exist_ok=True)
                
                # Sanitize name if needed (This is a simplified version, real one should check app_state/config)
                # But here we use the name provided in preview or sanitize it
                clean_name = self.sanitize_filename(src_path.name)
                final_dest = self._get_unique_path(target_folder, clean_name)
                
                # Yedekleme
                if self.config.get("backup_enabled", False):
                    self._handle_backup(src_path)
                    
                shutil.move(str(src_path), str(final_dest))
                
                # DB LOG
                stats = os.stat(final_dest)
                mime_type, _ = mimetypes.guess_type(str(final_dest))
                file_metadata = {
                    'name': final_dest.name,
                    'ext': final_dest.suffix.lower(),
                    'mime': mime_type or 'unknown',
                    'size': stats.st_size,
                    'created': datetime.datetime.fromtimestamp(stats.st_ctime).isoformat(),
                    'modified': datetime.datetime.fromtimestamp(stats.st_mtime).isoformat(),
                    'accessed': datetime.datetime.fromtimestamp(stats.st_atime).isoformat()
                }
                self.db.log_move(file_metadata, src_path, final_dest)
                count += 1
            except Exception as e:
                self.logger.error(f"Toplu taşıma hatası {item['path']}: {e}")
        
        if count > 0:
            generate_report()
        return count

    def get_preview(self, source, dest=None, same_folder=True):
        """Prepares a list of movements without actually moving."""
        source_path = Path(source)
        dest_path = Path(dest) if dest else source_path
        
        preview = []
        if not source_path.exists():
            return preview

        for item in source_path.iterdir():
            if item.is_file():
                # Ignore report files
                if item.name == "report.txt" or item.name.startswith("report_"):
                    continue
                
                # Logic to find target category (Copying from organize_file logic)
                file_extension = item.suffix.lower()
                found_category = None
                
                # Models
                custom_models = self.config.get("models", [])
                import fnmatch
                for model in custom_models:
                    if not model.get("active", True): continue
                    patterns = [p.strip() for p in model.get("pattern", "").split(",")]
                    for pattern in patterns:
                        if fnmatch.fnmatch(item.name, pattern):
                            found_category = model.get("target")
                            break
                    if found_category: break
                
                if not found_category:
                    found_category = "Others"
                    for category, extensions in self.extensions_map.items():
                        if file_extension in extensions:
                            found_category = category
                            break
                
                # Sanitize name for display
                clean_name = self.sanitize_filename(item.name)
                
                preview.append({
                    "filename": clean_name,
                    "original_name": item.name,
                    "path": str(item),
                    "target_folder": found_category,
                    "type": "file"
                })
        return preview

    def scan_directory(self):
        """Main.py seçeneği için toplu tarama."""
        print(f"📂 Klasör Taranıyor: {self.source_dir}")
        print("-" * 50)
        
        if not self.source_dir.exists():
            print("HATA: Kaynak klasör bulunamadı!")
            return

        file_count = 0
        folder_count = 0
        
        for item in self.source_dir.iterdir():
            if item.is_file():
                if self.organize_file(item):
                    file_count += 1
            elif item.is_dir():
                if self.organize_folder(item):
                    folder_count += 1
                
        print("-" * 50)
        print(f"✨ Tarama Bitti. Dosya: {file_count}, Klasör: {folder_count}")

# Backward compatibility (Main.py veya Watcher.py uyumu)
if __name__ == "__main__":
    organizer = Organizer()
    organizer.scan_directory()
