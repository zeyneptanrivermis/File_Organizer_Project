import re
import os

def sanitize_filename(filename):
    """Dosya adlarını temizler: küçük harf, özel karakterleri temizle, boşlukları '_' yap."""
    name, ext = os.path.splitext(filename)
    
    # Küçük harfe çevir ve Türkçe karakterleri/özel karakterleri temizle
    name = name.lower()
    
    # Sadece harf, rakam, tire ve alt çizgiyi tut
    # (Bu basit bir versiyondur, gerekirse genişletilebilir)
    name = re.sub(r'[^\w\s-]', '', name)
    
    # Boşlukları ve tekrarlayan işaretleri temizle
    name = re.sub(r'[-\s]+', '_', name)
    name = name.strip('_')
    
    if not name:
        name = "unnamed_file"
        
    return f"{name}{ext}"
