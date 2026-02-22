import shutil
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from config_loader import load_config
from logger import get_logger
from cleaner import sanitize_filename

class FilterRules:
    """Filtreleme kurallarını tanımlar ve valide eder."""
    
    def __init__(self):
        self.config = load_config()
        self.logger = get_logger()
        self.extensions_map = self.config.get("file_extensions", {})
    
    def get_available_extensions(self) -> Dict[str, List[str]]:
        """Mevcut kategorilere göre uzantıları döner."""
        return self.extensions_map
    
    def get_available_categories(self) -> List[str]:
        """Mevcut tüm kategorileri döner."""
        return list(self.extensions_map.keys())


class SizeFilter:
    """Dosya boyutuna göre filtreleme."""
    
    def __init__(self, min_size_mb: float = 0, max_size_mb: float = float('inf')):
        """
        min_size_mb: Minimum dosya boyutu (MB cinsinden)
        max_size_mb: Maksimum dosya boyutu (MB cinsinden)
        """
        self.min_bytes = min_size_mb * (1024 * 1024)
        self.max_bytes = max_size_mb * (1024 * 1024)
    
    def matches(self, file_path: Path) -> bool:
        """Dosyanın boyut kriterine uyup uymadığını kontrol eder."""
        if not file_path.exists():
            return False
        
        file_size = file_path.stat().st_size
        return self.min_bytes <= file_size <= self.max_bytes
    
    def __repr__(self):
        return f"SizeFilter({self.min_bytes / (1024*1024):.1f}MB - {self.max_bytes / (1024*1024):.1f}MB)"


class ExtensionFilter:
    """Dosya uzantısına göre filtreleme."""
    
    def __init__(self, extensions: List[str]):
        """
        extensions: Filtrelenecek uzantılar (örn: [".jpg", ".png"])
        """
        # Tüm uzantıları küçük harfe çevir
        self.extensions = [ext.lower() if ext.startswith('.') else f'.{ext.lower()}' 
                          for ext in extensions]
    
    def matches(self, file_path: Path) -> bool:
        """Dosyanın uzantı kriterine uyup uymadığını kontrol eder."""
        return file_path.suffix.lower() in self.extensions
    
    def __repr__(self):
        return f"ExtensionFilter({self.extensions})"


class CategoryFilter:
    """Dosya kategorisine göre filtreleme (Images, Documents, vb)."""
    
    def __init__(self, categories: List[str]):
        """
        categories: Filtrelenecek kategoriler (örn: ["Images", "Documents"])
        """
        self.categories = categories
        self.config = load_config()
        self.extensions_map = self.config.get("file_extensions", {})
    
    def matches(self, file_path: Path) -> bool:
        """Dosyanın kategori kriterine uyup uymadığını kontrol eder."""
        file_ext = file_path.suffix.lower()
        
        for category in self.categories:
            extensions = self.extensions_map.get(category, [])
            if file_ext in extensions:
                return True
        
        return False
    
    def __repr__(self):
        return f"CategoryFilter({self.categories})"


class CompositeFilter:
    """Birden fazla filtreyi birleştirir (AND mantığı)."""
    
    def __init__(self, filters: List = None):
        """
        filters: Uygulanacak filtreler listesi
        """
        self.filters = filters or []
    
    def add_filter(self, filter_obj):
        """Filtre ekle."""
        self.filters.append(filter_obj)
        return self
    
    def matches(self, file_path: Path) -> bool:
        """Tüm filtreleri kontrol et (hepsi true olmalı)."""
        if not self.filters:
            return True
        
        return all(f.matches(file_path) for f in self.filters)
    
    def __repr__(self):
        return f"CompositeFilter({self.filters})"


class FilterEngine:
    """Ana filtreleme motoru - tüm işlemleri koordine eder."""
    
    def __init__(self):
        self.config = load_config()
        self.logger = get_logger()
        self.source_dir = Path(self.config["source_directory"])
        self.dest_dir = Path(self.config["destination_directory"])
        self.extensions_map = self.config.get("file_extensions", {})
        self.sanitize = sanitize_filename
    
    def scan_with_filters(self, composite_filter: CompositeFilter) -> List[Path]:
        """
        Klasörü tara ve filtreleri uygula.
        Eşleşen dosyaların listesini döner.
        """
        if not self.source_dir.exists():
            self.logger.error(f"Kaynak klasör bulunamadı: {self.source_dir}")
            return []
        
        matching_files = []
        
        try:
            for item in self.source_dir.iterdir():
                if item.is_file():
                    # Sistem dosyalarını atla
                    if item.suffix in ['.tmp', '.crdownload', '.part']:
                        continue
                    
                    # Rapor dosyalarını atla
                    if item.name == "report.txt" or (item.name.startswith("report_") and item.suffix == ".txt"):
                        continue
                    
                    # Filtreleri uygula
                    if composite_filter.matches(item):
                        matching_files.append(item)
            
            self.logger.info(f"Filtreleme Tamamlandı: {len(matching_files)} dosya eşleşti")
            return matching_files
        
        except Exception as e:
            self.logger.error(f"Tarama sırasında hata: {e}")
            return []
    
    def _get_unique_path(self, target_folder: Path, clean_name: str) -> Path:
        """Aynı isimde dosya varsa benzersiz isim oluştur."""
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
    
    def _get_category_for_file(self, file_path: Path) -> str:
        """Dosyanın kategorisini belirle."""
        file_extension = file_path.suffix.lower()
        
        for category, extensions in self.extensions_map.items():
            if file_extension in extensions:
                return category
        
        return "Others"
    
    def organize_files(self, matching_files: List[Path], use_category_folders: bool = True) -> Dict:
        """
        Eşleşen dosyaları organize et.
        
        Args:
            matching_files: Organize edilecek dosya listesi
            use_category_folders: True ise kategoriye göre klasör oluştur, False ise tek klasöre koy
        
        Returns:
            İstatistikler (taşınan, hata vb.)
        """
        stats = {
            "moved": 0,
            "errors": 0,
            "details": []
        }
        
        for file_path in matching_files:
            try:
                # Kategori belirle
                category = self._get_category_for_file(file_path)
                
                # Hedef klasör
                if use_category_folders:
                    target_folder = self.dest_dir / category
                else:
                    target_folder = self.dest_dir / "Filtered_Files"
                
                target_folder.mkdir(parents=True, exist_ok=True)
                
                # İsim temizle
                clean_name = self.sanitize(file_path.name)
                destination_path = self._get_unique_path(target_folder, clean_name)
                
                # Taşı
                shutil.move(str(file_path), str(destination_path))
                
                log_msg = f"FİLTRE TASINDI | {category} | {file_path.name} -> {destination_path.name}"
                self.logger.info(log_msg)
                
                stats["moved"] += 1
                stats["details"].append({
                    "file": file_path.name,
                    "category": category,
                    "destination": str(destination_path)
                })
                
            except PermissionError:
                self.logger.error(f"ERİŞİM HATASI | {file_path.name}")
                stats["errors"] += 1
            except Exception as e:
                self.logger.error(f"HATA | {file_path.name}: {e}")
                stats["errors"] += 1
        
        return stats
    
    def archive_folders(self, matching_files: List[Path], archive_name: str = "archive.zip") -> Dict:
        """
        Eşleşen dosyaları ZIP dosyası içine arşivle.
        
        Args:
            matching_files: Arşivlenecek dosya listesi
            archive_name: ZIP dosyasının adı
        
        Returns:
            İstatistikler
        """
        stats = {
            "archived": 0,
            "errors": 0,
            "archive_path": None
        }
        
        if not matching_files:
            return stats
        
        try:
            # ZIP dosyasının yolu
            archive_path = self.dest_dir / archive_name
            
            with zipfile.ZipFile(str(archive_path), 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in matching_files:
                    try:
                        # ZIP içindeki dosya adı (klasör yapısı korunmaz, flat)
                        arcname = file_path.name
                        zipf.write(str(file_path), arcname=arcname)
                        
                        # Orijinal dosyayı sil (isteğe bağlı)
                        file_path.unlink()
                        
                        stats["archived"] += 1
                        
                    except Exception as e:
                        self.logger.error(f"Arşivleme hatası | {file_path.name}: {e}")
                        stats["errors"] += 1
            
            stats["archive_path"] = str(archive_path)
            self.logger.info(f"ARŞİVLEME TAMAMLANDI | {archive_name} - {stats['archived']} dosya")
            
        except Exception as e:
            self.logger.error(f"ZIP oluşturulurken hata: {e}")
        
        return stats
    
    def execute(self, filter_config: Dict, organize_mode: str = "organize") -> Dict:
        """
        Ana işlem - filtreleri uygula ve işlem yap.
        
        Args:
            filter_config: Filtreleme ayarlarını içeren sözlük
                {
                    "size_min_mb": 0,
                    "size_max_mb": float('inf'),
                    "extensions": [],
                    "categories": [],
                    "use_category_folders": True,
                    "archive_name": "archive.zip"
                }
            organize_mode: "organize" | "archive" | "both"
        
        Returns:
            İşlem sonuçları
        """
        # Filtre oluştur
        composite_filter = CompositeFilter()
        
        # Boyut filtresi
        if "size_min_mb" in filter_config or "size_max_mb" in filter_config:
            min_size = filter_config.get("size_min_mb", 0)
            max_size = filter_config.get("size_max_mb", float('inf'))
            composite_filter.add_filter(SizeFilter(min_size, max_size))
        
        # Uzantı filtresi
        if filter_config.get("extensions"):
            composite_filter.add_filter(ExtensionFilter(filter_config["extensions"]))
        
        # Kategori filtresi
        if filter_config.get("categories"):
            composite_filter.add_filter(CategoryFilter(filter_config["categories"]))
        
        # Dosyaları tara
        matching_files = self.scan_with_filters(composite_filter)
        
        if not matching_files:
            self.logger.warning("Filtrelere uygun dosya bulunamadı.")
            return {"matched": 0, "organize": None, "archive": None}
        
        results = {
            "matched": len(matching_files),
            "organize": None,
            "archive": None
        }
        
        # Organize modu
        use_categories = filter_config.get("use_category_folders", True)
        if organize_mode in ["organize", "both"]:
            results["organize"] = self.organize_files(matching_files, use_categories)
        
        # Archive modu (eğer organize yapıldıysa tekrar tarama gerekir)
        if organize_mode in ["archive", "both"]:
            # Archive için yeni liste oluştur (matching_files'daki dosyalar artık taşınmış olabilir)
            if organize_mode == "archive":
                matching_files = self.scan_with_filters(composite_filter)
            
            if matching_files:
                archive_name = filter_config.get("archive_name", "archive.zip")
                results["archive"] = self.archive_folders(matching_files, archive_name)
        
        return results


if __name__ == "__main__":
    # Test örneği
    print("=== Filter Engine Test ===\n")
    
    # FilterRules'dan kullanılabilir kategorileri al
    rules = FilterRules()
    print(f"Mevcut Kategoriler: {rules.get_available_categories()}\n")
    
    # Filter Engine oluştur
    engine = FilterEngine()
    
    # Test 1: Boyut filtresi (1MB - 100MB arası)
    print("Test 1: Boyut Filtresi (1-100 MB)")
    config_1 = {
        "size_min_mb": 1,
        "size_max_mb": 100,
        "use_category_folders": True
    }
    # results_1 = engine.execute(config_1)
    # print(f"Sonuç: {results_1}\n")
    
    # Test 2: Kategori filtresi
    print("Test 2: Kategori Filtresi (Images ve Documents)")
    config_2 = {
        "categories": ["Images", "Documents"],
        "use_category_folders": True
    }
    # results_2 = engine.execute(config_2)
    # print(f"Sonuç: {results_2}\n")
    
    # Test 3: Uzantı filtresi
    print("Test 3: Uzantı Filtresi (.jpg, .png)")
    config_3 = {
        "extensions": [".jpg", ".png"],
        "use_category_folders": False
    }
    # results_3 = engine.execute(config_3)
    # print(f"Sonuç: {results_3}\n")
    
    print("Testler hazır (execute komutlarının başında # kaldırılıp çalıştırılabilir)")
