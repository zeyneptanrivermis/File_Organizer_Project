import sys
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'src'))

try:
    import PySimpleGUI as sg
except Exception:
    sg = None

try:
    from filter_engine import FilterEngine
except Exception:
    FilterEngine = None

import requests

LAYOUT = [
    [sg.Text('Extensions (comma separated)'), sg.Input(key='-EXT-')],
    [sg.Text('Categories (comma separated)'), sg.Input(key='-CAT-')],
    [sg.Text('Min size MB'), sg.Input(key='-MIN-', size=(10,1)) , sg.Text('Max size MB'), sg.Input(key='-MAX-', size=(10,1))],
    [sg.Combo(['organize','archive','both'], default_value='organize', key='-MODE-')],
    [sg.Button('Preview'), sg.Button('Run'), sg.Button('Exit')],
    [sg.Output(size=(80,10))]
]

def normalize_list(s: str):
    if not s: return []
    return [p.strip() if p.strip().startswith('.') else f'.{p.strip()}' for p in s.split(',') if p.strip()]

def run_local(payload, mode):
    if not FilterEngine:
        print('Local FilterEngine not available; start Flask API and use remote mode')
        return
    engine = FilterEngine()
    res = engine.execute(payload, organize_mode=mode)
    print(res)

def post_remote(payload, mode):
    try:
        r = requests.post('http://127.0.0.1:5000/api/run-filter', json=payload, params={'mode': mode}, timeout=60)
        print(r.json())
    except Exception as e:
        print('Remote call failed:', e)

def main():
    if sg is None:
        print('PySimpleGUI not installed. Install with: pip install PySimpleGUI')
        return

    window = sg.Window('FilterEngine GUI Demo', LAYOUT)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, 'Exit'):
            break

        exts = normalize_list(values['-EXT-'])
        cats = [c.strip() for c in values['-CAT-'].split(',') if c.strip()]
        try:
            min_mb = float(values['-MIN-'] or 0)
        except Exception:
            min_mb = 0
        max_raw = values['-MAX-']
        try:
            max_mb = float(max_raw) if max_raw and max_raw.strip() != '' else float('inf')
        except Exception:
            max_mb = float('inf')

        payload = {
            'size_min_mb': min_mb,
            'size_max_mb': max_mb,
            'extensions': exts,
            'categories': cats,
            'use_category_folders': True,
            'archive_name': 'gui_archive.zip'
        }

        mode = values['-MODE-']

        if event == 'Preview':
            # Try local first, otherwise remote
            if FilterEngine:
                # For preview, call engine.scan_with_filters via execute (engine returns results)
                run_local(payload, mode='organize')
            else:
                post_remote(payload, mode)

        if event == 'Run':
            if FilterEngine:
                run_local(payload, mode)
            else:
                post_remote(payload, mode)

    window.close()

if __name__ == '__main__':
    main()
