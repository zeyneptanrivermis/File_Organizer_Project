**Filter Engine UI Integration Guide**

Amaç: GUI geliştiricisinin `FilterEngine` filtrelerini seçip çalıştırabilmesi için kısa, uygulanabilir bir kılavuz ve iki örnek gösterilmektedir (HTTP API ve yerel GUI).

- Backend entrypoint: `FilterEngine.execute(filter_config, organize_mode)`
- Preview: `FilterEngine.scan_with_filters(composite_filter)`

Filter config (kullanılacak JSON):

{
  "size_min_mb": 0,
  "size_max_mb": 10,
  "extensions": [".jpg",".png"],
  "categories": [],
  "use_category_folders": true,
  "archive_name": "filtered_archive.zip"
}

organize_mode: `organize | archive | both` (veya preview için özel `preview` davranışı kullanarak sadece tarama yapılır).

Quick start (Flask API):

1. Terminalde proje kökünde çalıştırın:
```
pip install flask
python ui_examples/flask_api.py
```
2. POST isteği gönderin (örnek curl):
```
curl -X POST http://127.0.0.1:5000/api/run-filter -H "Content-Type: application/json" -d @filter.json
```

Quick start (PySimpleGUI demo):

1. Terminalde çalıştırın (local FilterEngine varsa doğrudan çağırır, yoksa HTTP API'ye POST eder):
```
pip install PySimpleGUI requests
python ui_examples/py_simple_gui.py
```

Dosyalar:
- `ui_examples/flask_api.py` — küçük Flask sunucusu örneği (POST `/api/run-filter`).
- `ui_examples/py_simple_gui.py` — PySimpleGUI demo; geliştirici için hızlı prototip.

Notlar:
- `categories` listesini GUI, `src/config_loader.py` içindeki `file_extensions` haritasından doldurmalıdır.
- `extensions` alanı frontend'de normalize edilmelidir (örn. "jpg" → ".jpg").
- `size_max_mb` boşsa backend `float('inf')` ile ele alacak şekilde mapping yapın.

İsterseniz ben bu örnekleri sunucuya uygun hale getirip daha ayrıntılı test senaryoları da ekleyebilirim.
