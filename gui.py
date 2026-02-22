"""
File Organizer Pro - Nihai Modern Arayüz
Versiyon: 2.2.0 - Ultra Kontrast & Stabilite Gücellemesi
"""

import flet as ft
import os
import datetime
import asyncio
from organizer import Organizer


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
    page.window_width = 1100
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.DARK
    
    # State yönetimi (Yeniden yüklemelerde korunur)
    if not hasattr(page, "app_state"):
        page.app_state = {
            "is_dark": True,
            "source_path": os.path.join(os.path.expanduser("~"), "Downloads"),
            "dest_path": "",
            "same_folder": True,
            "selected_tab": 0,
            "is_monitoring": False,
            "models": [
                {"id": 1, "name": "Resim Düzenleyici", "pattern": "*.jpg, *.png", "target": "Resimler", "active": True},
                {"id": 2, "name": "Belge Tasnifi", "pattern": "*.pdf, *.docx", "target": "Belgeler", "active": True},
                {"id": 3, "name": "Video Arşivi", "pattern": "*.mp4, *.mkv", "target": "Videolar", "active": False},
            ],
            "logs": [],
            "stats": {
                "total": 0,
                "organized": 0,
                "time": "0sn"
            }
        }

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
            preview_files = org.get_preview(source, dest)
            
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

            file_list_container = ft.Column(scroll="always", max_height=400, spacing=10)

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
                moved_count = org.move_specific_files(to_move, dest)
                
                now = datetime.datetime.now().strftime("%H:%M:%S")
                if moved_count > 0:
                    show_notification(f"{moved_count} dosya başarıyla taşındı!", "success")
                    page.app_state["logs"].append({"time": now, "type": "success", "msg": f"{moved_count} dosya preview üzerinden taşındı."})
                    page.app_state["stats"]["organized"] += moved_count
                
                await build_ui()

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
                    ft.ElevatedButton("Onayla ve Taşı", bgcolor=COLOR_SUCCESS, color="white", on_click=confirm_move)
                ],
                bgcolor=c["surface"]
            )

            page.overlay.append(dlg)
            dlg.open = True
            page.update()

        except Exception as ex:
            show_notification(f"Hata oluştu: {str(ex)}", "error")

    def on_close_click(_):
        page.window_close()
    
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
                    content=ft.Text(str(count), size=12, weight="w500", color=c["text"]),
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
        return ft.Column([
            # Organizasyon İlerlemesi
            ft.Container(
                bgcolor=c["surface"],
                padding=25,
                border_radius=15,
                border=ft.Border.all(1, c["border"]),
                content=ft.Column([
                    ft.Text("Organizasyon İlerlemesi", size=18, weight="bold", color=c["text"]),
                    ft.Text(f"{page.app_state['stats']['organized']} dosya organize edildi", size=13, color=c["secondary"]),
                    ft.Container(height=10),
                    ft.ProgressBar(value=1.0 if (page.app_state['stats']['total'] or 0) <= 0 else page.app_state['stats']['organized'] / page.app_state['stats']['total'], color=COLOR_SUCCESS, bgcolor=c["border"], height=10, border_radius=5),
                    ft.Text(f"%{(0.0 if (page.app_state['stats']['total'] or 0) <= 0 else page.app_state['stats']['organized'] / page.app_state['stats']['total'] * 100):.1f} tamamlandı", size=12, italic=True, color=c["secondary"]),
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
                            ft.Text("124 Dosya", size=12, color=c["secondary"]),
                            ft.Text("2.4 GB", size=16, weight="bold")
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
                            ft.Text("18 Dosya", size=12, color=c["secondary"]),
                            ft.Text("8.7 GB", size=16, weight="bold")
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
                    ft.Row([
                        ft.Row([ft.Container(width=10, height=10, bgcolor=COLOR_SUCCESS, border_radius=5), 
                               ft.Text("vacation_photo.jpg", color=c["text"], weight="w500")]),
                        ft.Text("14:32:18", size=12, color=c["secondary"])
                    ], alignment="spaceBetween"),
                    ft.Divider(color=c["border"], height=20),
                    ft.Row([
                        ft.Row([ft.Container(width=10, height=10, bgcolor=COLOR_SUCCESS, border_radius=5), 
                               ft.Text("project_backup.zip", color=c["text"], weight="w500")]),
                        ft.Text("14:31:42", size=12, color=c["secondary"])
                    ], alignment="spaceBetween"),
                ])
            )
        ], spacing=20, expand=True, scroll="auto")

    def build_models_view():
        c = get_colors()
        
        async def toggle_model(model_id):
            for m in page.app_state["models"]:
                if m["id"] == model_id:
                    m["active"] = not m["active"]
                    break
            await build_ui()

        async def delete_model(model_id):
            page.app_state["models"] = [m for m in page.app_state["models"] if m["id"] != model_id]
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
        return ft.Column([
            ft.Text("İşlem Geçmişi", size=18, weight="bold", color=c["text"]),
            ft.ListView(
                expand=True,
                spacing=10,
                controls=[
                    ft.ListTile(
                        leading=ft.Icon(ft.Icons.INSERT_DRIVE_FILE, color=COLOR_ACCENT),
                        title=ft.Text(f"Dosya_{i}.txt", color=c["text"]),
                        subtitle=ft.Text("Taşındı: /Arşiv | 10.02.2026 14:30", color=c["secondary"]),
                        trailing=ft.IconButton(ft.Icons.UNDO, icon_color=COLOR_WARNING, tooltip="Geri Al"),
                        bgcolor=c["surface"],
                        shape=ft.RoundedRectangleBorder(radius=8)
                    ) for i in range(10)
                ]
            )
        ], expand=True)

    def build_logs_view():
        c = get_colors()
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
                ], scroll="always")
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
                
                ft.Divider(height=20, color=c["border"]),
                ft.Text("DOSYA KATEGORİLERİ", size=11, weight="bold", color=c["secondary"], opacity=0.7),
                create_category_item("Görseller", ft.Icons.IMAGE, 124, "blue500"),
                create_category_item("Videolar", ft.Icons.VIDEO_FILE, 18, "purple500"),
                create_category_item("Müzik", ft.Icons.MUSIC_NOTE, 342, "green500"),
                create_category_item("Arşivler", ft.Icons.FOLDER_ZIP, 45, "yellow700"),
                create_category_item("Kod Dosyaları", ft.Icons.CODE, 89, "red500"),
                create_category_item("Belgeler", ft.Icons.DESCRIPTION, 156, "blue700"),
                create_category_item("Diğer", ft.Icons.INSERT_DRIVE_FILE, 67, "grey500"),
                
                ft.Container(height=20),
                ft.Row([ft.Text("Otomatik Organize", size=12, color=c["text"]), ft.Switch(value=True, scale=0.8, active_color=COLOR_ACCENT)], alignment="spaceBetween"),
                ft.Row([ft.Text("Dosya Yeniden Adlandır", size=12, color=c["text"]), ft.Switch(value=True, scale=0.8, active_color=COLOR_ACCENT)], alignment="spaceBetween"),
                ft.Row([ft.Text("Yedek Oluştur", size=12, color=c["text"]), ft.Switch(value=False, scale=0.8, active_color=COLOR_ACCENT)], alignment="spaceBetween"),
            ], spacing=5, scroll="auto")
        )

        # 🟠 ANA İÇERİK
        
        # Sekmeye göre içerik oluştur
        tab_views = {
            0: build_dashboard,
            1: build_history_view,
            2: build_logs_view,
            3: build_models_view
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
    await build_ui()

if __name__ == "__main__":
    ft.run(main)
