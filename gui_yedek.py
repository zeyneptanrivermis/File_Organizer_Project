import sys
import os
import logging
import threading
import customtkinter as ctk

# Proje klasörünü ve src klasörünü Python yoluna ekle
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
sys.path.append(src_dir)

from src.organizer import Organizer
from src.watcher import Watcher
from src.reporter import generate_report
from src.config_loader import load_config
from src.logger import get_logger

class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.insert("end", msg + "\n")
            self.text_widget.see("end")
        self.text_widget.after(0, append)

class OrganizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Smart File Organizer v2.0")
        self.geometry("700x850") # Daha geniş bir alan için genişlik artırıldı
        ctk.set_appearance_mode("dark")
        
        self.config = load_config()
        self.selected_path = self.config.get("source_directory")
        self.is_watching = False
        self.watcher_instance = None

        # --- UI ELEMANLARI ---
        self.header = ctk.CTkLabel(self, text="📁 İndirilenler Düzenleyici", font=("Segoe UI", 28, "bold"))
        self.header.pack(pady=(30, 5))
        
        self.path_label = ctk.CTkLabel(self, text=f"Hedef: {self.selected_path}", text_color="gray")
        self.path_label.pack(pady=(0, 20))

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10, padx=30, fill="x")

        self.scan_btn = ctk.CTkButton(self.btn_frame, text="Hemen Organize Et", 
                                      fg_color="#1f538d", hover_color="#14375e",
                                      command=self.run_scan)
        self.scan_btn.grid(row=0, column=0, padx=5, sticky="ew")

        self.watch_btn = ctk.CTkButton(self.btn_frame, text="Otomatik İzle", 
                                       fg_color="#2c8558", hover_color="#1e5c3d",
                                       command=self.toggle_watcher)
        self.watch_btn.grid(row=0, column=1, padx=5, sticky="ew")
        
        self.btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.tabview = ctk.CTkTabview(self, width=640, height=550)
        self.tabview.pack(pady=10, padx=30, fill="both", expand=True)
        self.tabview.add("Sistem Günlüğü")
        self.tabview.add("Son Analiz Raporu")

        self.log_box = ctk.CTkTextbox(self.tabview.tab("Sistem Günlüğü"), font=("Consolas", 12))
        self.log_box.pack(fill="both", expand=True)

        self.report_box = ctk.CTkTextbox(self.tabview.tab("Son Analiz Raporu"), font=("Consolas", 12))
        self.report_box.pack(fill="both", expand=True)

        self.status_bar = ctk.CTkLabel(self, text="Hazır", font=("Arial", 11), text_color="gray")
        self.status_bar.pack(side="bottom", pady=5)

        self.setup_logging()

    def setup_logging(self):
        logger = get_logger()
        formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
        text_handler = TextHandler(self.log_box)
        text_handler.setFormatter(formatter)
        logger.addHandler(text_handler)

    def run_scan(self):
        self.status_bar.configure(text="Tarama yapılıyor...", text_color="orange")
        def task():
            org = Organizer()
            org.scan_directory()
            self.after(0, lambda: self.status_bar.configure(text="Tarama Tamamlandı", text_color="green"))
            self.after(0, lambda: self.show_report())
        threading.Thread(target=task, daemon=True).start()

    def toggle_watcher(self):
        if not self.is_watching:
            self.watcher_instance = Watcher(self.selected_path)
            threading.Thread(target=self.watcher_instance.start, daemon=True).start()
            self.is_watching = True
            self.watch_btn.configure(text="İzlemeyi Durdur", fg_color="red")
            self.status_bar.configure(text="Gözcü Aktif", text_color="#2c8558")
        else:
            if self.watcher_instance:
                self.watcher_instance.stop()
            self.is_watching = False
            self.watch_btn.configure(text="Otomatik İzle", fg_color="#2c8558")
            self.status_bar.configure(text="Gözcü Durduruldu", text_color="gray")

    def show_report(self):
        generate_report()
        # Yol normalizasyonu: Sadece klasör adını baz alarak daha güvenli eşleşme sağlarız
        current_folder_name = os.path.basename(os.path.normpath(self.selected_path))
        
        config = load_config()
        log_path = config.get("log_file_path", "organizer.log")
        
        from collections import Counter
        local_categories = Counter()
        global_categories = Counter()
        local_total = 0
        global_total = 0

        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if "TASINDI" in line:
                        parts = line.split("|")
                        if len(parts) >= 2:
                            cat = parts[1].strip()
                            global_categories[cat] += 1
                            global_total += 1
                            
                            # Eğer satırda seçili klasörün adı geçiyorsa yerel olarak say
                            if current_folder_name in line:
                                local_categories[cat] += 1
                                local_total += 1

        self.report_box.delete("1.0", "end")
        
        # --- BÖLÜM 1: GENEL RAPOR ---
        self.report_box.insert("end", f"🌍 SİSTEM GENELİ TOPLAM\n")
        self.report_box.insert("end", "="*45 + "\n")
        for cat, val in global_categories.most_common():
            bar_len = int((val / global_total) * 15) if global_total > 0 else 0
            bar = "█" * bar_len + "░" * (15 - bar_len)
            self.report_box.insert("end", f"{cat:<15} | {bar} | {val} dosya\n")
        
        self.report_box.insert("end", "\n" + "="*45 + "\n\n")
        
        # --- BÖLÜM 2: ÖZEL RAPOR ---
        self.report_box.insert("end", f"📂 {current_folder_name.upper()} ÖZEL RAPORU\n")
        self.report_box.insert("end", "-"*45 + "\n")
        
        if local_total > 0:
            for cat, val in local_categories.most_common():
                perc = (val / local_total) * 100
                bar_len = int(perc / 6.6) # Yaklaşık 15 karakterlik bar
                bar = "█" * bar_len + "░" * (15 - bar_len)
                self.report_box.insert("end", f"{cat:<15} | {bar} | {val} dosya (%{perc:.1f})\n")
            self.report_box.insert("end", f"\nBU KLASÖRDE TOPLAM İŞLEM: {local_total}")
        else:
            # Backend loglarında klasör yolu tam yazılmadığı için en azından genel rapora bakılabilir
            self.report_box.insert("end", "⚠️ Bu klasör için yeni işlem kaydı bulunamadı.\n")
            self.report_box.insert("end", "Genel raporu yukarıdan kontrol edebilirsiniz.")

        self.tabview.set("Son Analiz Raporu")
        self.status_bar.configure(text="Rapor Görselleştirildi", text_color="cyan")

if __name__ == "__main__":
    app = OrganizerApp()
    app.mainloop()