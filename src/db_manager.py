import sqlite3
import os
from pathlib import Path

class DBManager:
    def __init__(self, db_path="organizer.db"):
        self.db_path = db_path
        self._create_tables()
        self._seed_data()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Sonuçlara isim ile erişmek için 
        return conn

    def _create_tables(self):
        """Senin istediğin 4 tablolu mimariyi kurar."""
        with self._get_connection() as conn:
            # Klasör tablosu
            conn.execute("CREATE TABLE IF NOT EXISTS folders (id INTEGER PRIMARY KEY, path TEXT UNIQUE)")
            
            # Dosya tablosu
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY, 
                    folder_id INTEGER, 
                    name TEXT, 
                    extension TEXT, 
                    mime_type TEXT, 
                    size INTEGER,
                    created_at DATETIME, 
                    last_accessed DATETIME,
                    FOREIGN KEY(folder_id) REFERENCES folders(id))""")
            
            # İşlem türleri tablosu
            conn.execute("CREATE TABLE IF NOT EXISTS op_types (id INTEGER PRIMARY KEY, name TEXT UNIQUE)")
            
            # İşlem geçmişi tablosu
            conn.execute("""
                CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY,
                    file_id INTEGER,
                    type_id INTEGER,
                    old_path TEXT,
                    new_path TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'SUCCESS',
                    FOREIGN KEY(file_id) REFERENCES files(id),
                    FOREIGN KEY(type_id) REFERENCES op_types(id))""")

    def _seed_data(self):
        with self._get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO op_types (name) VALUES ('MOVE'), ('UNDO'), ('RENAME'), ('ADMIN')")

    def log_move(self, file_metadata, old_path, new_path):
        """Bir taşıma işlemini tüm tablolara atomik olarak kaydeder."""
        with self._get_connection() as conn:
            # Klasörü kaydet
            conn.execute("INSERT OR IGNORE INTO folders (path) VALUES (?)", (str(Path(old_path).parent),))
            folder_id = conn.execute("SELECT id FROM folders WHERE path = ?", (str(Path(old_path).parent),)).fetchone()[0]
            
            # Dosyayı kaydet
            cursor = conn.execute("""
                INSERT INTO files (folder_id, name, extension, mime_type, size, created_at, last_accessed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (folder_id, file_metadata['name'], file_metadata['ext'], file_metadata['mime'], 
                  file_metadata['size'], file_metadata['created'], file_metadata['accessed']))
            file_id = cursor.lastrowid
            
            # İşlemi kaydet
            conn.execute("""
                INSERT INTO operations (file_id, type_id, old_path, new_path)
                VALUES (?, (SELECT id FROM op_types WHERE name='MOVE'), ?, ?)
            """, (file_id, str(old_path), str(new_path)))

    def log_event(self, event_name, status="SUCCESS"):
        """Genel bir yönetimsel olayı kaydeder (Model eklendi vb.)."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO operations (file_id, type_id, old_path, new_path, status)
                VALUES (NULL, (SELECT id FROM op_types WHERE name='ADMIN'), ?, '', ?)
            """, (event_name, status))

    def get_history_by_date(self, start_date, end_date):
        """Tarih aralığına göre detaylı döküm verir."""
        query = """
            SELECT o.id, f.name, f.mime_type, f.size, o.old_path, o.new_path, o.timestamp 
            FROM operations o 
            JOIN files f ON o.file_id = f.id 
            WHERE o.timestamp BETWEEN ? AND ? AND o.status = 'SUCCESS'
        """
        with self._get_connection() as conn:
            return [dict(row) for row in conn.execute(query, (f"{start_date} 00:00:00", f"{end_date} 23:59:59")).fetchall()]

    def get_category_stats(self, extension_map):
        """Kategorilere göre dosya sayısı ve toplam boyutu döndürür."""
        stats = {cat: {"count": 0, "size": 0} for cat in extension_map.keys()}
        stats["Others"] = {"count": 0, "size": 0}

        with self._get_connection() as conn:
            rows = conn.execute("SELECT extension, size FROM files").fetchall()
            for row in rows:
                ext = row["extension"]
                size = row["size"]
                found = False
                for cat, exts in extension_map.items():
                    if ext in exts:
                        stats[cat]["count"] += 1
                        stats[cat]["size"] += size
                        found = True
                        break
                if not found:
                    stats["Others"]["count"] += 1
                    stats["Others"]["size"] += size
        return stats