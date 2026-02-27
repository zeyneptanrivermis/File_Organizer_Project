"""
File Organizer Pro - Nihai Modern Arayüz
Versiyon: 2.2.0 - Ultra Kontrast & Stabilite Gücellemesi
"""

import flet as ft
import os
import datetime
import asyncio
import sys
from pathlib import Path

# Add src and src/core to sys.path
base_path = Path(__file__).parent
src_path = base_path / "src"
core_path = src_path / "core"

if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
if str(core_path) not in sys.path:
    sys.path.insert(0, str(core_path))

from config_loader import load_config, save_config
from organizer import Organizer
from db_manager import DBManager
from undo_manager import UndoManager
from watcher import Watcher
import threading


# Renk Paleti - Modern & Premium Dark
COLOR_BG = "#111827"          # Ana arka plan
COLOR_SURFACE = "#1f2937"     # Kartlar ve paneller
COLOR_BORDER = "#374151"      # Kenarlıklar
COLOR_ACCENT = "#2563eb"      # Vurgu rengi (mavi)
COLOR_SUCCESS = "#22c55e"     # Başarı (yeşil)
COLOR_WARNING = "#f59e0b"     # Uyarı (turuncu)
COLOR_ERROR = "#ef4444"       # Hata (kırmızı)
COLOR_TEXT_PRIMARY = "#ffffff"    # Ana metin
COLOR_TEXT_SECONDARY = "#9ca3af"  # İkincil metin
COLOR_INFO = "#3b82f6"        # Bilgi mavisi

async def main(page: ft.Page):
    # ========================================================================
    # AYARLAR & DURUM
    # ========================================================================
    page.title = "File Organizer Pro"
    page.padding = 0
    page.spacing = 0
    page.window.width = 1100
    page.window.height = 800
    page.theme_mode = ft.ThemeMode.DARK
    
    # State yönetimi (Yeniden yüklemelerde korunur)
    if not hasattr(page, "app_state"):
        config = load_config()
        page.app_state = {
            "is_dark": True,
            "source_path": config.get("source_directory", os.path.join(os.path.expanduser("~"), "Downloads")),
            "dest_path": config.get("destination_directory", ""),
            "same_folder": True,
            "selected_tab": 0,
            "is_monitoring": False,
            "models": config.get("models", [
                {"id": 1, "name": "Resim Düzenleyici", "pattern": "*.jpg, *.png", "target": "Resimler", "active": True},
                {"id": 2, "name": "Belge Tasnifi", "pattern": "*.pdf, *.docx", "target": "Belgeler", "active": True},
                {"id": 3, "name": "Video Arşivi", "pattern": "*.mp4, *.mkv", "target": "Videolar", "active": False},
            ]),
            "logs": [],
            "stats": {"total": 0, "organized": 0, "time": "0s"},
            "selected_history": set()
        }

    async def save_app_config():
        config = load_config()
        config["source_directory"] = page.app_state["source_path"]
        config["models"] = page.app_state["models"]
        config["clean_names"] = page.app_state.get("clean_names", True)
        config["backup_enabled"] = page.app_state.get("backup_enabled", False)
        save_config(config)

    # Watcher thread yönetimi
    if not hasattr(page, "watcher"):
        page.watcher = None
        page.watcher_thread = None

    def start_watcher():
        if page.watcher:
            stop_watcher()
        
        source = page.app_state["source_path"]
        if not os.path.exists(source):
            return
            
        def on_watcher_event(type_, msg):
            now = datetime.datetime.now().strftime("%H:%M:%S")
            page.app_state["logs"].append({"time": now, "type": type_, "msg": msg})
            
            if type_ == "success":
                page.run_task(refresh_stats)
            elif page.app_state.get("selected_tab") == 2:
                page.run_task(build_ui)

        page.watcher = Watcher(source, on_event=on_watcher_event)
        
        def watcher_worker():
            page.watcher.observer.schedule(page.watcher.handler, str(page.watcher.directory), recursive=False)
            page.watcher.observer.start()
            while page.app_state["is_monitoring"]:
                time.sleep(1)
            page.watcher.observer.stop()
            page.watcher.observer.join()

        import time
        page.watcher_thread = threading.Thread(target=watcher_worker, daemon=True)
        page.watcher_thread.start()

    def stop_watcher():
        page.app_state["is_monitoring"] = False
        if page.watcher:
            page.watcher = None

    # REFS - UI Senkronizasyonu için
    source_ref = ft.Ref[ft.TextField]()
    dest_ref = ft.Ref[ft.TextField]()
    main_layout = ft.Column(expand=True, spacing=0)

    # ========================================================================
    # YARDIMCI FOKSİYONLAR
    # ========================================================================

    # Renk Paleti - Light Mode Altyapısı
    LIGHT_BG = "#f9fafb"
    LIGHT_SURFACE = "#ffffff"
    LIGHT_BORDER = "#e5e7eb"
    LIGHT_TEXT_PRIMARY = "#111827"
    LIGHT_TEXT_SECONDARY = "#6b7280"

    def get_colors():
        if page.app_state.get("is_dark", True):
            return {
                "bg": COLOR_BG, "surface": COLOR_SURFACE, 
                "surface_variant": "#1e293b", "border": COLOR_BORDER,
                "text": COLOR_TEXT_PRIMARY, "secondary": COLOR_TEXT_SECONDARY
            }
        else:
            return {
                "bg": LIGHT_BG, "surface": LIGHT_SURFACE, 
                "surface_variant": "#f3f4f6", "border": LIGHT_BORDER,
                "text": LIGHT_TEXT_PRIMARY, "secondary": LIGHT_TEXT_SECONDARY
            }

    def show_notification(msg, type="info"):
        bgcolor = COLOR_ACCENT
        if type == "success": bgcolor = COLOR_SUCCESS
        elif type == "error": bgcolor = COLOR_ERROR
        
        snack = ft.SnackBar(
            content=ft.Text(msg, color="white", weight="bold"),
            bgcolor=bgcolor,
            duration=2000
        )
        page.overlay.append(snack)
        snack.open = True
        page.update()

    async def refresh_stats():
        """Veritabanından sayıları çekip arayüzü yeniler."""
        db = DBManager()
        conf = load_config()
        ext_map = conf.get("file_extensions", {})
        cat_stats = db.get_category_stats(ext_map)
        
        # State güncelleme
        page.app_state["category_counts"] = {cat: cat_stats.get(cat, {"count": 0})["count"] for cat in ext_map}
        page.app_state["category_counts"]["Others"] = cat_stats.get("Others", {"count": 0})["count"]
        
        with db._get_connection() as conn:
            # Toplam dosya sayısı
            total = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
            page.app_state["stats"]["organized"] = total or 0
            
            # Toplam boyut
            total_size_row = conn.execute("SELECT SUM(size) FROM files").fetchone()
            total_size = total_size_row[0] if total_size_row and total_size_row[0] else 0
            page.app_state["stats"]["total_size_gb"] = total_size / (1024**3)
            
            # Son işlem zamanını stat olarak göster
            last_op = conn.execute("SELECT timestamp FROM operations ORDER BY timestamp DESC LIMIT 1").fetchone()
            if last_op:
                page.app_state["stats"]["time"] = last_op[0].split()[-1] # Sadece saati göster
            else:
                page.app_state["stats"]["time"] = "Yok"

        await build_ui()

    async def toggle_setting(key, val):
        # Bu ayarlar şu an app_state'de tutulabilir veya config'e kaydedilebilir
        page.app_state[key] = val
        if key == "is_monitoring":
            if val:
                start_watcher()
                page.app_state["logs"].append({"time": datetime.datetime.now().strftime("%H:%M:%S"), "type": "info", "msg": "Otomatik izleme başlatıldı."})
            else:
                stop_watcher()
                page.app_state["logs"].append({"time": datetime.datetime.now().strftime("%H:%M:%S"), "type": "info", "msg": "Otomatik izleme durduruldu."})
        
        await save_app_config()
        await build_ui()

    async def select_folder_native(target_name):
        import tkinter as tk
        from tkinter import filedialog
        
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            path = filedialog.askdirectory()
            root.destroy()
            
            if path:
                if target_name == "source":
                    page.app_state["source_path"] = path
                    source_ref.current.value = path
                    show_notification(f"İzlenen klasör seçildi: {path}", "success")
                else:
                    page.app_state["dest_path"] = path
                    dest_ref.current.value = path
                    show_notification(f"Hedef klasör seçildi: {path}", "success")
            else:
                show_notification("Lütfen bir klasör seçmelisin!", "error")
        except Exception as ex:
            show_notification(f"Seçim hatası: {str(ex)}", "error")
        
        page.update()

    async def pick_source(_):
        print("Pick Source Clicked (Tkinter)")
        await select_folder_native("source")

    async def pick_dest(_):
        print("Pick Dest Clicked (Tkinter)")
        await select_folder_native("dest")

    # ========================================================================
    # EVENT HANDLERS
    # ========================================================================

    async def toggle_theme(_):
        page.theme_mode = ft.ThemeMode.DARK if page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        page.app_state["is_dark"] = page.theme_mode == ft.ThemeMode.DARK
        await build_ui()

    async def on_tab_change(index):
        page.app_state["selected_tab"] = index
        await build_ui()

    async def on_checkbox_change(e):
        page.app_state["same_folder"] = e.control.value
        await build_ui()

    async def on_source_change(e):
        page.app_state["source_path"] = e.control.value

    async def on_dest_change(e):
        page.app_state["dest_path"] = e.control.value

    async def organize_now(_):
        source = page.app_state["source_path"]
        dest = page.app_state["dest_path"] if not page.app_state["same_folder"] else None
        
        if not source or (not page.app_state["same_folder"] and not dest):
            show_notification("Lütfen klasör yollarını kontrol edin!", "error")
            return
            
        try:
            org = Organizer()
            db = DBManager()
            undo = UndoManager()
            preview_files = org.get_preview(source, dest, page.app_state["same_folder"])
            
            if not preview_files:
                show_notification("Organize edilecek dosya bulunamadı.", "warning")
                return

            # Önizleme Diyaloğu Değişkenleri
            selected_files = {f["path"]: True for f in preview_files}
            c = get_colors()

            def toggle_all(e):
                val = e.control.value
                for path in selected_files:
                    selected_files[path] = val
                # Update UI in dialog (need to rebuild rows)
                update_dialog_content()

            def toggle_item(path, val):
                selected_files[path] = val

            file_list_container = ft.Column(scroll="always", height=400, spacing=10)

            def update_dialog_content():
                file_list_container.controls.clear()
                for f in preview_files:
                    is_selected = selected_files[f["path"]]
                    file_list_container.controls.append(
                        ft.Container(
                            content=ft.Row([
                                ft.Checkbox(value=is_selected, on_change=lambda e, p=f["path"]: toggle_item(p, e.control.value)),
                                ft.Icon(ft.Icons.DESCRIPTION, color=COLOR_ACCENT, size=20),
                                ft.Column([
                                    ft.Text(f["filename"], size=14, weight="bold", color=c["text"], overflow=ft.TextOverflow.ELLIPSIS),
                                    ft.Text(f"Hedef: {f['target_folder']}", size=11, color=c["secondary"]),
                                ], spacing=2, expand=True)
                            ], alignment="start"),
                            padding=10, border_radius=8, bgcolor=c["bg"]
                        )
                    )
                page.update()

            async def confirm_move(_):
                dlg.open = False
                page.update()
                
                to_move = [f for f in preview_files if selected_files[f["path"]]]
                if not to_move:
                    show_notification("Hiç dosya seçilmedi.", "warning")
                    return
                
                show_notification(f"{len(to_move)} dosya taşınıyor...", "info")
                moved_count = await org.move_specific_files(to_move, dest)
                
                now = datetime.datetime.now().strftime("%H:%M:%S")
                if moved_count > 0:
                    show_notification(f"{moved_count} dosya başarıyla taşındı!", "success")
                    page.app_state["logs"].append({"time": now, "type": "success", "msg": f"{moved_count} dosya preview üzerinden taşındı."})
                
                await refresh_stats()

            update_dialog_content()

            dlg = ft.AlertDialog(
                title=ft.Row([ft.Icon(ft.Icons.PREVIEW, color=COLOR_ACCENT), ft.Text("Organizasyon Önizleme", color=c["text"])]),
                content=ft.Container(
                    width=600,
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"Toplam {len(preview_files)} dosya bulundu.", size=14, color=c["secondary"]),
                            ft.Checkbox(label="Tümünü Seç", value=True, on_change=toggle_all)
                        ], alignment="spaceBetween"),
                        ft.Divider(color=c["border"]),
                        file_list_container
                    ], tight=True)
                ),
                actions=[
                    ft.TextButton("İptal", on_click=lambda _: setattr(dlg, "open", False) or page.update()),
                    ft.Button("Onayla ve Taşı", bgcolor=COLOR_SUCCESS, color="white", on_click=confirm_move)
                ],
                bgcolor=c["surface"]
            )

            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        except Exception as ex:
            show_notification(f"Hata oluştu: {str(ex)}", "error")

    def on_close_click(_):
        page.window.close()
    
    # Main layout initialization
    page.add(main_layout)

    # ========================================================================
    # YARDIMCI BİLEŞENLER
    # ========================================================================

    def create_stat_card(label, value, icon, color=COLOR_ACCENT):
        c = get_colors()
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, color="white", size=20),
                    bgcolor=color,
                    padding=10,
                    border_radius=8,
                ),
                ft.Column([
                    ft.Text(label, size=12, color=c["secondary"]),
                    ft.Text(value, size=16, weight="bold", color=c["text"]),
                ], spacing=0)
            ], alignment="start"),
            bgcolor=ft.Colors.with_opacity(0.1, c["surface_variant"]),
            padding=15,
            border_radius=10,
            expand=True,
        )

    def create_category_item(name, icon, count, color):
        c = get_colors()
        return ft.Container(
            content=ft.Row([
                ft.Row([
                    ft.Container(
                        content=ft.Icon(icon, color="white", size=16),
                        bgcolor=color,
                        padding=6,
                        border_radius=5,
                    ),
                    ft.Text(name, size=14, color=c["text"]),
                ]),
                ft.Container(
                    content=ft.Text(str(count) if count > 0 else "0", size=12, weight="w500", color=c["text"]),
                    bgcolor=c["border"],
                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                    border_radius=10,
                )
            ], alignment="spaceBetween"),
            padding=8,
            border_radius=5,
            on_hover=lambda e: setattr(e.control, "bgcolor", c["border"] if e.data == "true" else None) or e.control.update(),
        )

    # ========================================================================
    # VIEW BUILDERS
    # ========================================================================

    def build_dashboard():
        c = get_colors()
        db = DBManager()
        
        # Gerçek istatistikleri çek (app_state'den alalım, refresh_stats tarafından güncellenir)
        total_files = page.app_state["stats"].get("organized", 0)
        total_size_gb = page.app_state["stats"].get("total_size_gb", 0)
        
        undo_mgr = UndoManager()
        recent_ops = undo_mgr.get_recent_operations(5)
        
        from config_loader import load_config
        conf = load_config()
        ext_map = conf.get("file_extensions", {})
        cat_stats = db.get_category_stats(ext_map)

        def get_cat_info(cat_name):
            s = cat_stats.get(cat_name, {"count": 0, "size": 0})
            return f"{s['count']} Dosya", f"{s['size']/(1024**2):.1f} MB" if s['size'] < 1024**3 else f"{s['size']/(1024**3):.1f} GB"

        return ft.Column([
            # Sistem İstatistikleri
            ft.Container(
                bgcolor=c["surface"],
                padding=25,
                border_radius=15,
                border=ft.Border.all(1, c["border"]),
                content=ft.Column([
                    ft.Text("Sistem İstatistikleri", size=18, weight="bold", color=c["text"]),
                    ft.Text(f"Toplam {total_files} dosya işlendi", size=13, color=c["secondary"]),
                    ft.Container(height=10),
                    ft.ProgressBar(value=1.0, color=COLOR_SUCCESS, bgcolor=c["border"], height=10, border_radius=5),
                    ft.Text(f"Depolama Etkisi: {total_size_gb:.2f} GB", size=12, italic=True, color=c["secondary"]),
                ], spacing=5)
            ),
            
            ft.Row([
                ft.Container(
                    bgcolor=c["surface"], padding=20, border_radius=15, expand=True,
                    border=ft.Border.all(1, c["border"]),
                    content=ft.Row([
                        ft.Container(ft.Icon(ft.Icons.IMAGE, color="white"), bgcolor="blue500", padding=12, border_radius=10),
                        ft.Column([
                            ft.Text("Görseller", weight="bold"),
                            ft.Text(get_cat_info("Images")[0], size=12, color=c["secondary"]),
                            ft.Text(get_cat_info("Images")[1], size=16, weight="bold")
                        ], spacing=2)
                    ])
                ),
                ft.Container(
                    bgcolor=c["surface"], padding=20, border_radius=15, expand=True,
                    border=ft.Border.all(1, c["border"]),
                    content=ft.Row([
                        ft.Container(ft.Icon(ft.Icons.VIDEO_FILE, color="white"), bgcolor="purple500", padding=12, border_radius=10),
                        ft.Column([
                            ft.Text("Videolar", weight="bold"),
                            ft.Text(get_cat_info("Videos")[0], size=12, color=c["secondary"]),
                            ft.Text(get_cat_info("Videos")[1], size=16, weight="bold")
                        ], spacing=2)
                    ])
                ),
            ], spacing=20),
            
            ft.Row([
                ft.Container(
                    bgcolor=c["surface"], padding=20, border_radius=15, expand=True,
                    border=ft.Border.all(1, c["border"]),
                    content=ft.Row([
                        ft.Container(ft.Icon(ft.Icons.DESCRIPTION, color="white"), bgcolor="green500", padding=12, border_radius=10),
                        ft.Column([
                            ft.Text("Belgeler", weight="bold"),
                            ft.Text(get_cat_info("Documents")[0], size=12, color=c["secondary"]),
                            ft.Text(get_cat_info("Documents")[1], size=16, weight="bold")
                        ], spacing=2)
                    ])
                ),
                ft.Container(
                    bgcolor=c["surface"], padding=20, border_radius=15, expand=True,
                    border=ft.Border.all(1, c["border"]),
                    content=ft.Row([
                        ft.Container(ft.Icon(ft.Icons.CODE, color="white"), bgcolor="red500", padding=12, border_radius=10),
                        ft.Column([
                            ft.Text("Kodlar", weight="bold"),
                            ft.Text(get_cat_info("Code")[0], size=12, color=c["secondary"]),
                            ft.Text(get_cat_info("Code")[1], size=16, weight="bold")
                        ], spacing=2)
                    ])
                ),
            ], spacing=20),

            ft.Text("Son İşlemler", size=18, weight="bold", color=c["text"]),
            ft.Container(
                expand=True,
                bgcolor=c["surface"],
                border_radius=15,
                border=ft.Border.all(1, c["border"]),
                padding=20,
                content=ft.Column([
                    ft.Column([
                        ft.Row([
                            ft.Row([
                                ft.Container(
                                    width=10, height=10, 
                                    bgcolor=COLOR_SUCCESS if op['status']=='SUCCESS' else COLOR_WARNING, 
                                    border_radius=5
                                ), 
                                ft.Text(op['name'], color=c["text"], weight="w500", size=13, overflow=ft.TextOverflow.ELLIPSIS)
                            ], expand=True),
                            ft.Text(op['timestamp'].split()[1] if ' ' in op['timestamp'] else op['timestamp'], size=12, color=c["secondary"])
                        ], alignment="spaceBetween") for op in recent_ops
                    ]),
                    ft.Divider(),
                    ft.TextButton(
                        "Tüm Geçmişi Yönet & Toplu Geri Al", 
                        icon=ft.Icons.ARROW_FORWARD, 
                        on_click=lambda _: asyncio.create_task(on_tab_change(1))
                    )
                ])
            )
        ], spacing=20, expand=True, scroll="auto")

    def build_models_view():
        c = get_colors()
        
        async def toggle_model(model_id):
            for m in page.app_state["models"]:
                if m["id"] == model_id:
                    m["active"] = not m["active"]
                    status_text = "Aktif" if m["active"] else "Pasif"
                    DBManager().log_event(f"Model Durumu Değişti: {m['name']} ({status_text})")
                    break
            await save_app_config()
            await build_ui()

        async def delete_model(model_id):
            model_name = next((m["name"] for m in page.app_state["models"] if m["id"] == model_id), "Bilinmeyen Model")
            page.app_state["models"] = [m for m in page.app_state["models"] if m["id"] != model_id]
            await save_app_config()
            DBManager().log_event(f"Model Silindi: {model_name}")
            show_notification("Model silindi.", "warning")
            await build_ui()

        async def open_add_dialog(_):
            name_ref = ft.Ref[ft.TextField]()
            pattern_ref = ft.Ref[ft.TextField]()
            target_ref = ft.Ref[ft.TextField]()

            def add_confirm(_):
                if not name_ref.current.value: return
                new_id = max([m["id"] for m in page.app_state["models"]] + [0]) + 1
                page.app_state["models"].append({
                    "id": new_id,
                    "name": name_ref.current.value,
                    "pattern": pattern_ref.current.value,
                    "target": target_ref.current.value,
                    "active": True
                })
                asyncio.create_task(save_app_config())
                DBManager().log_event(f"Yeni Model Eklendi: {name_ref.current.value}")
                dlg.open = False
                show_notification("Yeni model eklendi.", "success")
                asyncio.create_task(build_ui())

            dlg = ft.AlertDialog(
                title=ft.Text("Yeni Model Ekle", color=c["text"]),
                content=ft.Column([
                    ft.TextField(ref=name_ref, label="Model Adı", border_color=c["border"], color=c["text"]),
                    ft.TextField(ref=pattern_ref, label="Dosya Kalıbı (*.jpg vb.)", border_color=c["border"], color=c["text"]),
                    ft.TextField(ref=target_ref, label="Hedef Klasör Adı", border_color=c["border"], color=c["text"]),
                ], tight=True, spacing=10),
                actions=[
                    ft.TextButton("İptal", on_click=lambda _: setattr(dlg, "open", False) or page.update()),
                    ft.Button("Ekle", bgcolor=COLOR_SUCCESS, color="white", on_click=add_confirm)
                ]
            )
            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        return ft.Column([
            ft.Row([
                ft.Text("Organizasyon Modelleri", size=18, weight="bold", color=c["text"]),
                ft.Button("Yeni Model", icon=ft.Icons.ADD, bgcolor=COLOR_SUCCESS, color="white", on_click=open_add_dialog)
            ], alignment="spaceBetween"),
            ft.ListView(
                expand=True,
                spacing=15,
                controls=[
                    ft.Container(
                        bgcolor=c["surface"],
                        padding=20,
                        border_radius=10,
                        border=ft.Border.all(1, COLOR_SUCCESS if m["active"] else c["border"]),
                        content=ft.Row([
                            ft.Column([
                                ft.Text(m["name"], weight="bold", size=16, color=c["text"]),
                                ft.Row([
                                    ft.Text(f"Kalıp: {m['pattern']}", size=12, color=c["secondary"]),
                                    ft.Text(f"Hedef: {m['target']}", size=12, color=c["secondary"]),
                                ], spacing=20)
                            ], expand=True),
                            ft.Switch(value=m["active"], active_color=COLOR_SUCCESS, on_change=lambda e, mid=m["id"]: asyncio.create_task(toggle_model(mid))),
                            ft.IconButton(ft.Icons.DELETE, icon_color=COLOR_ERROR, on_click=lambda e, mid=m["id"]: asyncio.create_task(delete_model(mid))),
                        ])
                    ) for m in page.app_state["models"]
                ]
            )
        ], spacing=20, expand=True)

    def build_history_view():
        c = get_colors()
        undo_mgr = UndoManager()
        history = undo_mgr.get_recent_operations(20)

        async def run_undo(op_ids=None):
            if isinstance(op_ids, list):
                if not op_ids:
                    show_notification("Seçili işlem yok.", "warning")
                    return
                count = 0
                for oid in op_ids:
                    success, _ = undo_mgr.undo_operation(oid)
                    if success: count += 1
                show_notification(f"{count} işlem başarıyla geri alındı.", "success")
            elif op_ids:
                success, msg = undo_mgr.undo_operation(op_ids)
                show_notification(msg, "success" if success else "error")
            else:
                success, msg = undo_mgr.undo_last_operation()
                show_notification(msg, "success" if success else "error")
            
            page.app_state["selected_history"] = set() # Reset selection
            await refresh_stats()

        async def toggle_history_select(op_id, val):
            # Create a new set to ensure Flet/Python detects change
            current_selected = set(page.app_state["selected_history"])
            if val:
                current_selected.add(op_id)
            else:
                current_selected.discard(op_id)
            page.app_state["selected_history"] = current_selected
            await build_ui()

        async def select_all_history(val):
            current_selected = set()
            if val:
                for item in history:
                    if item['status'] == 'SUCCESS' and item['op_type'] in ('MOVE', 'RENAME'):
                        current_selected.add(item['id'])
            page.app_state["selected_history"] = current_selected
            await build_ui()

        return ft.Column([
            ft.Row([
                ft.Row([
                    ft.Text("İşlem Geçmişi", size=18, weight="bold", color=c["text"]),
                    ft.Checkbox(label="Tümünü Seç", on_change=lambda e: asyncio.create_task(select_all_history(e.control.value))) if history else ft.Container()
                ], spacing=20),
                ft.Row([
                    ft.Button(
                        "Seçilenleri Geri Al", 
                        icon=ft.Icons.REPLAY_CIRCLE_FILLED, 
                        bgcolor=COLOR_ACCENT, color="white",
                        on_click=lambda _: asyncio.create_task(run_undo(list(page.app_state["selected_history"]))),
                        visible=len(page.app_state["selected_history"]) > 0
                    ),
                    ft.Button("Son İşlemi Geri Al", icon=ft.Icons.UNDO, bgcolor=COLOR_WARNING, color="white", on_click=lambda _: asyncio.create_task(run_undo()))
                ], spacing=10)
            ], alignment="spaceBetween"),
            ft.ListView(
                expand=True,
                spacing=10,
                controls=[
                    ft.ListTile(
                        leading=ft.Checkbox(
                            value=item['id'] in page.app_state["selected_history"],
                            on_change=lambda e, oid=item['id']: asyncio.create_task(toggle_history_select(oid, e.control.value)),
                            visible=item['status'] == 'SUCCESS' and item['op_type'] in ('MOVE', 'RENAME')
                        ),
                        title=ft.Text(item['name'], color=c["text"], weight="bold" if item['id'] in page.app_state["selected_history"] else "normal"),
                        subtitle=ft.Text(f"{item['op_type']} | {item['timestamp']} | Durum: {item['status']}", color=c["secondary"]),
                        bgcolor=ft.Colors.with_opacity(0.1, COLOR_ACCENT) if item['id'] in page.app_state["selected_history"] else c["surface"],
                        hover_color=c["border"],
                        shape=ft.RoundedRectangleBorder(radius=8),
                        on_click=lambda e, oid=item['id']: asyncio.create_task(toggle_history_select(oid, not (oid in page.app_state["selected_history"]))) 
                            if item['status'] == 'SUCCESS' and item['op_type'] in ('MOVE', 'RENAME') else None,
                        trailing=ft.IconButton(
                            icon=ft.Icons.UNDO, 
                            icon_color=COLOR_WARNING,
                            tooltip="Bu İşlemi Geri Al",
                            on_click=lambda e, oid=item['id']: asyncio.create_task(run_undo(oid))
                        ) if item['status'] == 'SUCCESS' and item['op_type'] in ('MOVE', 'RENAME') else None
                    ) for item in history
                ] if history else [ft.Text("Henüz işlem geçmişi yok.", color=c["secondary"])]
            )
        ], expand=True)

    def build_logs_view():
        c = get_colors()
        # Logları log dosyasından okumayı deneyebiliriz, şimdilik state'den
        return ft.Column([
            ft.Text("Sistem Logları", size=18, weight="bold", color=c["text"]),
            ft.Container(
                expand=True,
                bgcolor=c["surface"],
                padding=15,
                border_radius=10,
                border=ft.Border.all(1, c["border"]),
                content=ft.Column([
                    ft.Text(f"[{log['time']}] {log['type'].upper()}: {log['msg']}", 
                            color=COLOR_INFO if log['type'] == 'info' else (COLOR_SUCCESS if log['type'] == 'success' else COLOR_WARNING), 
                            font_family="monospace") for log in page.app_state["logs"]
                ] if page.app_state["logs"] else [ft.Text("Henüz log kaydı yok.", color=c["secondary"])], scroll="always")
            )
        ], expand=True)

    def build_settings_view():
        c = get_colors()
        
        async def clear_db_click(_):
            db = DBManager()
            db.log_event("Veritabanı Temizleme İşlemi Başlatıldı")
            with db._get_connection() as conn:
                conn.execute("DELETE FROM operations")
                conn.execute("DELETE FROM files")
                conn.execute("DELETE FROM folders")
            show_notification("Veritabanı temizlendi.", "success")
            await build_ui()


        return ft.Column([
            ft.Text("Ayarlar", size=18, weight="bold", color=c["text"]),
            ft.Container(
                bgcolor=c["surface"],
                padding=20,
                border_radius=15,
                border=ft.Border.all(1, c["border"]),
                content=ft.Column([
                    ft.Text("Genel Ayarlar", weight="bold", size=16),
                    ft.Switch(label="Otomatik Organize (Watcher)", 
                              value=page.app_state.get("is_monitoring", False), 
                              active_color=COLOR_ACCENT,
                              on_change=lambda e: asyncio.create_task(toggle_setting("is_monitoring", e.control.value))),
                    ft.Switch(label="Dosya İsimlerini Temizle", 
                              value=page.app_state.get("clean_names", True), 
                              active_color=COLOR_ACCENT,
                              on_change=lambda e: asyncio.create_task(toggle_setting("clean_names", e.control.value))),
                    ft.Divider(),
                    ft.Text("Sistem", weight="bold", size=16),
                    ft.Button("Veritabanını Temizle", 
                                     icon=ft.Icons.DELETE_SWEEP, 
                                     bgcolor=COLOR_ERROR, 
                                     color="white",
                                     on_click=clear_db_click),
                ], spacing=15)
            )
        ], expand=True)

    # ========================================================================
    # UI BUILDER
    # ========================================================================

    async def build_ui():
        main_layout.controls.clear()
        c = get_colors()
        page.bgcolor = c["bg"]
        
        # 🟢 BAŞLIK ÇUBUĞU
        title_bar = ft.Container(
            bgcolor=c["surface"],
            padding=ft.Padding.symmetric(horizontal=15, vertical=10),
            border=ft.Border(bottom=ft.BorderSide(1, c["border"])),
            content=ft.Row([
                ft.Row([
                    ft.Icon(ft.Icons.FOLDER_COPY, color=COLOR_ACCENT, size=24),
                    ft.Text("File Organizer Pro", weight="bold", size=18, color=c["text"]),
                ], spacing=10),
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.WB_SUNNY_OUTLINED if page.theme_mode == ft.ThemeMode.DARK else ft.Icons.DARK_MODE_OUTLINED,
                        icon_color=COLOR_WARNING if page.theme_mode == ft.ThemeMode.DARK else COLOR_ACCENT,
                        tooltip="Tema Değiştir",
                        on_click=toggle_theme
                    ),
                    ft.IconButton(ft.Icons.CLOSE, icon_color=c["text"], hover_color="red600", on_click=on_close_click),
                ])
            ], alignment="spaceBetween")
        )

        # 🔵 SOL SIDEBAR
        sidebar_items = [
            ("Dashboard", ft.Icons.DASHBOARD, 0),
            ("Geçmiş", ft.Icons.HISTORY, 1),
            ("Loglar", ft.Icons.DESCRIPTION, 2),
            ("Modeller", ft.Icons.RULE, 3),
        ]
        
        from config_loader import load_config
        conf = load_config()
        ext_map = conf.get("file_extensions", {})
        db = DBManager()
        cat_stats = db.get_category_stats(ext_map)

        def s(cat): return cat_stats.get(cat, {"count": 0})["count"]

        sidebar_content = [
            ft.Divider(height=20, color=c["border"]),
            ft.Text("DOSYA KATEGORİLERİ", size=11, weight="bold", color=c["secondary"], opacity=0.7),
            create_category_item("Görseller", ft.Icons.IMAGE, s("Images"), "blue500"),
            create_category_item("Videolar", ft.Icons.VIDEO_FILE, s("Videos"), "purple500"),
            create_category_item("Müzik", ft.Icons.MUSIC_NOTE, s("Music"), "green500"),
            create_category_item("Arşivler", ft.Icons.FOLDER_ZIP, s("Archives"), "yellow700"),
            create_category_item("Kodlar", ft.Icons.CODE, s("Code"), "red500"),
            create_category_item("Belgeler", ft.Icons.DESCRIPTION, s("Documents"), "blue700"),
            create_category_item("Diğer", ft.Icons.INSERT_DRIVE_FILE, s("Others"), "grey500"),
        ]

        sidebar = ft.Container(
            width=260,
            bgcolor=c["surface"],
            padding=20,
            border=ft.Border(right=ft.BorderSide(1, c["border"])),
            content=ft.Column([
                ft.Container(height=10),
                ft.OutlinedButton(
                    content=ft.Row([ft.Icon(ft.Icons.SYNC, color=c["text"]), ft.Text("Şimdi Organize Et", color=c["text"], weight="bold")], alignment="center"),
                    width=220, height=45,
                    on_click=organize_now,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                ),

                ft.Divider(height=20, color=c["border"]),
                ft.Text("MENÜ", size=12, weight="bold", color=c["secondary"]),
                *[ft.Container(
                    content=ft.Row([ft.Icon(icon, size=20, color=COLOR_ACCENT if page.app_state["selected_tab"] == i else c["secondary"]), 
                                    ft.Text(label, weight="bold", color=c["text"] if page.app_state["selected_tab"] == i else c["secondary"])]),
                    padding=12, border_radius=8,
                    bgcolor=ft.Colors.with_opacity(0.1, COLOR_ACCENT) if page.app_state["selected_tab"] == i else None,
                    ink=True, on_click=lambda _, idx=i: asyncio.create_task(on_tab_change(idx))
                ) for label, icon, i in sidebar_items],
                
                *sidebar_content,
                
                ft.Container(height=20),
                ft.Row([
                    ft.Text("Otomatik Organize", size=12, color=c["text"]), 
                    ft.Switch(
                        value=page.app_state.get("is_monitoring", False), 
                        scale=0.8, active_color=COLOR_ACCENT,
                        on_change=lambda e: asyncio.create_task(toggle_setting("is_monitoring", e.control.value))
                    )
                ], alignment="spaceBetween"),
                ft.Row([
                    ft.Text("Dosya Yeniden Adlandır", size=12, color=c["text"]), 
                    ft.Switch(
                        value=page.app_state.get("clean_names", True), 
                        scale=0.8, active_color=COLOR_ACCENT,
                        on_change=lambda e: asyncio.create_task(toggle_setting("clean_names", e.control.value))
                    )
                ], alignment="spaceBetween"),
                ft.Row([
                    ft.Text("Yedek Oluştur", size=12, color=c["text"]), 
                    ft.Switch(
                        value=page.app_state.get("backup_enabled", False), 
                        scale=0.8, active_color=COLOR_ACCENT,
                        on_change=lambda e: asyncio.create_task(toggle_setting("backup_enabled", e.control.value))
                    )
                ], alignment="spaceBetween"),
            ], spacing=5, scroll="auto")
        )

        # 🟠 ANA İÇERİK
        
        # Sekmeye göre içerik oluştur
        tab_views = {
            0: build_dashboard,
            1: build_history_view,
            2: build_logs_view,
            3: build_models_view,
            4: build_settings_view
        }
        
        view_content = tab_views.get(page.app_state["selected_tab"], build_dashboard)()

        main_content = ft.Container(
            expand=True,
            bgcolor=c["bg"],
            padding=30,
            content=ft.Column([
                # Klasör Seçimi (Görseldeki gibi üstte tek satır)
                ft.Row([
                    ft.Text("İzlenen Klasör:", weight="bold", color=c["text"]),
                    ft.TextField(
                        ref=source_ref,
                        value=page.app_state["source_path"],
                        bgcolor=c["surface"], border_color=c["border"], expand=True,
                        color=c["text"], height=35, text_size=13,
                        content_padding=ft.Padding.symmetric(horizontal=10),
                        on_change=on_source_change
                    ),
                    ft.Button(
                        content=ft.Row([ft.Icon(ft.Icons.FOLDER_OPEN, size=16), ft.Text("Seç", weight="bold")], spacing=5),
                        bgcolor=COLOR_SUCCESS, color="white", height=38,
                        on_click=pick_source,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                    )
                ], spacing=15),
                ft.Checkbox(
                    label="İzlenen klasörde düzenle (aynı klasör içinde organize et)",
                    value=page.app_state["same_folder"],
                    on_change=on_checkbox_change,
                    fill_color=COLOR_ACCENT,
                    label_style=ft.TextStyle(size=12, color=c["secondary"])
                ),

                # Hedef Klasör Seçimi (Görseldeki gibi, aynı klasör seçili değilse çıkar)
                ft.Row([
                    ft.Text("Hedef Klasör:", weight="bold", color=c["text"]),
                    ft.TextField(
                        ref=dest_ref,
                        value=page.app_state["dest_path"],
                        bgcolor=c["surface"], border_color=c["border"], expand=True,
                        color=c["text"], height=35, text_size=13,
                        content_padding=ft.Padding.symmetric(horizontal=10),
                        hint_text="Dosyaların taşınacağı klasörü seçin...",
                        on_change=on_dest_change
                    ),
                    ft.Button(
                        content=ft.Row([ft.Icon(ft.Icons.FOLDER_OPEN, size=16), ft.Text("Seç", weight="bold")], spacing=5),
                        bgcolor=COLOR_SUCCESS, color="white", height=38,
                        on_click=pick_dest,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8))
                    )
                ], spacing=15, visible=not page.app_state["same_folder"]),

                # İstatistik Çubuğu (Görseldeki gibi Folder Selection altında)
                ft.Row([
                    create_stat_card("Toplam Dosya", str(page.app_state["stats"]["total"]), ft.Icons.INSERT_DRIVE_FILE),
                    create_stat_card("Organize Edildi", str(page.app_state["stats"]["organized"]), ft.Icons.CHECK_CIRCLE, COLOR_SUCCESS),
                    create_stat_card("İşlem Süresi", page.app_state["stats"]["time"], ft.Icons.TIMER, COLOR_INFO),
                    create_stat_card("Aktif Durum", "Hazır", ft.Icons.CHECK_CIRCLE, COLOR_SUCCESS),
                ], spacing=15),

                # Premium Tab Bar
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Row([ft.Icon(ft.Icons.DASHBOARD, size=18), ft.Text("Genel Bakış", weight="bold")], spacing=10),
                            padding=ft.Padding.symmetric(horizontal=15, vertical=10), border_radius=8,
                            bgcolor=c["border"] if page.app_state["selected_tab"] == 0 else None,
                            on_click=lambda _: asyncio.create_task(on_tab_change(0)), ink=True
                        ),
                        ft.Container(
                            content=ft.Row([ft.Icon(ft.Icons.FOLDER, size=18), ft.Text("Taşınan Dosyalar", weight="bold")], spacing=10),
                            padding=ft.Padding.symmetric(horizontal=15, vertical=10), border_radius=8,
                            bgcolor=c["border"] if page.app_state["selected_tab"] == 1 else None,
                            on_click=lambda _: asyncio.create_task(on_tab_change(1)), ink=True
                        ),
                        ft.Container(
                            content=ft.Row([ft.Icon(ft.Icons.DESCRIPTION, size=18), ft.Text("Loglar", weight="bold")], spacing=10),
                            padding=ft.Padding.symmetric(horizontal=15, vertical=10), border_radius=8,
                            bgcolor=c["border"] if page.app_state["selected_tab"] == 2 else None,
                            on_click=lambda _: asyncio.create_task(on_tab_change(2)), ink=True
                        ),
                        ft.Container(
                            content=ft.Row([ft.Icon(ft.Icons.SETTINGS, size=18), ft.Text("Ayarlar", weight="bold")], spacing=10),
                            padding=ft.Padding.symmetric(horizontal=15, vertical=10), border_radius=8,
                            bgcolor=c["border"] if page.app_state["selected_tab"] == 4 else None,
                            on_click=lambda _: asyncio.create_task(on_tab_change(4)), ink=True
                        ),
                        ft.Container(
                            content=ft.Row([ft.Icon(ft.Icons.RULE, size=18), ft.Text("Modeller", weight="bold")], spacing=10),
                            padding=ft.Padding.symmetric(horizontal=15, vertical=10), border_radius=8,
                            bgcolor=c["border"] if page.app_state["selected_tab"] == 3 else None,
                            on_click=lambda _: asyncio.create_task(on_tab_change(3)), ink=True
                        ),
                    ], spacing=10)
                ),
                
                # Dinamik Sekme İçeriği
                ft.Container(content=view_content, expand=True)
            ], spacing=25)
        )

        # Alt Bar
        bottom_bar = ft.Container(
            bgcolor=c["surface"], padding=ft.Padding.symmetric(horizontal=20, vertical=10),
            border=ft.Border(top=ft.BorderSide(1, c["border"])),
            content=ft.Row([
                ft.Row([
                    ft.Container(width=10, height=10, bgcolor=COLOR_SUCCESS, border_radius=5),
                    ft.Text("Sistem Hazır", size=12, color=COLOR_SUCCESS, weight="bold"),
                ], spacing=10),
                ft.Text("v2.2.1 | Pro Recovery Edition", size=11, color=c["secondary"])
            ], alignment="spaceBetween")
        )

        main_layout.controls.append(
            ft.Column([
                title_bar,
                ft.Row([sidebar, main_content], expand=True, spacing=0),
                bottom_bar
            ], expand=True, spacing=0)
        )
        page.update()

    # Uygulamayı başlat
    await refresh_stats()
    await build_ui()

if __name__ == "__main__":
    ft.run(main)
