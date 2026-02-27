import os
import shutil
from db_manager import DBManager
from logger import get_logger

class UndoManager:
    """Yalnızca son işlemleri geri almak için değil, tüm operasyon geçmişini yönetir."""
    def __init__(self):
        self.db = DBManager()
        self.logger = get_logger()

    def undo_operation(self, op_id):
        """Belirli bir işlemi ID'sine göre geri alır."""
        with self.db._get_connection() as conn:
            op = conn.execute("""
                SELECT o.id, o.file_id, o.old_path, o.new_path, t.name as op_type
                FROM operations o
                JOIN op_types t ON o.type_id = t.id
                WHERE o.id = ? AND o.status = 'SUCCESS'
            """, (op_id,)).fetchone()

            if not op:
                return False, "İşlem bulunamadı veya zaten geri alınmış."

            op_id, file_id, old_path, new_path, op_type = op
            
            if op_type not in ('MOVE', 'RENAME'):
                return False, "Yalnızca taşıma ve isim değiştirme işlemleri geri alınabilir."

            try:
                if os.path.exists(new_path):
                    os.makedirs(os.path.dirname(old_path), exist_ok=True)
                    shutil.move(new_path, old_path)
                    
                    conn.execute("UPDATE operations SET status = 'UNDONE' WHERE id = ?", (op_id,))
                    conn.execute("INSERT INTO operations (file_id, type_id, old_path, new_path, status) VALUES (?, (SELECT id FROM op_types WHERE name='UNDO'), ?, ?, 'SUCCESS')",
                                 (file_id, new_path, old_path))
                    
                    return True, f"Geri alındı: {os.path.basename(old_path)}"
                else:
                    return False, f"Dosya bulunamadı: {os.path.basename(new_path)}"
            except Exception as e:
                self.logger.error(f"Seçili geri alma hatası: {e}")
                return False, f"Hata: {str(e)}"

    def undo_last_operation(self):
        """Son işlemi veritabanından bulur ve geri alır."""
        with self.db._get_connection() as conn:
            last_op = conn.execute("""
                SELECT o.id, o.file_id, o.old_path, o.new_path 
                FROM operations o
                JOIN op_types t ON o.type_id = t.id
                WHERE o.status = 'SUCCESS' AND t.name IN ('MOVE', 'RENAME')
                ORDER BY o.timestamp DESC LIMIT 1
            """).fetchone()

            if not last_op:
                return False, "Geri alınacak taşıma işlemi bulunamadı."

            op_id, file_id, old_path, new_path = last_op
            
            try:
                if os.path.exists(new_path):
                    # Hedef klasörü gerekirse oluştur
                    os.makedirs(os.path.dirname(old_path), exist_ok=True)
                    shutil.move(new_path, old_path)
                    
                    # İşlemi veritabanında güncelle
                    conn.execute("UPDATE operations SET status = 'UNDONE' WHERE id = ?", (op_id,))
                    conn.execute("INSERT INTO operations (file_id, type_id, old_path, new_path, status) VALUES (?, (SELECT id FROM op_types WHERE name='UNDO'), ?, ?, 'SUCCESS')",
                                 (file_id, new_path, old_path))
                    
                    return True, f"Başarıyla geri alındı: {os.path.basename(old_path)}"
                else:
                    return False, "Dosya artık hedef konumda değil."
            except Exception as e:
                self.logger.error(f"Geri alma hatası: {e}")
                return False, f"Hata: {str(e)}"

    def get_recent_operations(self, limit=10):
        """Arayüzde gösterilmek üzere son işlemleri getirir."""
        with self.db._get_connection() as conn:
            rows = conn.execute("""
                SELECT o.id, o.timestamp, COALESCE(f.name, o.old_path) as name, o.old_path, o.new_path, t.name as op_type, o.status
                FROM operations o
                LEFT JOIN files f ON o.file_id = f.id
                JOIN op_types t ON o.type_id = t.id
                ORDER BY o.timestamp DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]
