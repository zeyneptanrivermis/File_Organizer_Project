from flask import Flask, request, jsonify
import sys
from pathlib import Path

# Ensure src on path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'src'))

try:
    from filter_engine import FilterEngine
except Exception as e:
    FilterEngine = None

app = Flask(__name__)

@app.route('/api/run-filter', methods=['POST'])
def run_filter():
    if not FilterEngine:
        return jsonify({'error': 'FilterEngine not available'}), 500

    payload = request.get_json(force=True)
    # Basic normalization
    payload.setdefault('extensions', [])
    payload.setdefault('categories', [])
    payload.setdefault('use_category_folders', True)

    # sizes
    try:
        min_mb = float(payload.get('size_min_mb', 0) or 0)
    except Exception:
        min_mb = 0
    try:
        max_val = payload.get('size_max_mb')
        max_mb = float(max_val) if (max_val is not None and str(max_val).strip() != '') else float('inf')
    except Exception:
        max_mb = float('inf')

    payload['size_min_mb'] = min_mb
    payload['size_max_mb'] = max_mb

    mode = request.args.get('mode') or payload.get('organize_mode', 'organize')

    engine = FilterEngine()
    try:
        results = engine.execute(payload, organize_mode=mode)
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
