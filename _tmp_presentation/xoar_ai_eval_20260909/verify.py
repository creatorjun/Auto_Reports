# _tmp_presentation/xoar_ai_eval_20260909/verify.py
import json
import hashlib
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

base = Path(__file__).parent
deck = base.parents[1] / 'output/xoar_ai_eval_20260909/eyeCloudXOAR_검색기반_AI_검증결과_20260908.pptx'
evidence = json.loads((base / 'evidence.json').read_text(encoding='utf-8'))
ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main', 'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'}
with ZipFile(deck) as archive:
    for index, row in enumerate(evidence):
        slide_number = 15 + index // 2
        root = ET.fromstring(archive.read(f'ppt/slides/slide{slide_number}.xml'))
        visible = ''.join(root.itertext())
        assert row['raw'] in visible, f'Raw sample mismatch: {row["id"]}'
        note = ET.fromstring(archive.read(f'ppt/notesSlides/notesSlide{slide_number}.xml'))
        assert row['raw'] in ''.join(note.itertext()), f'Notes mismatch: {row["id"]}'
    slide_seven = ''.join(ET.fromstring(archive.read('ppt/slides/slide7.xml')).itertext())
    expected_suffixes = list(range(371, 381)) + [446,447,448,449,450,451,452,454,455,456]
    assert all(f'SR260908-AW1-{suffix:08}' in slide_seven for suffix in expected_suffixes)
    chart_path = next(name for name in archive.namelist() if name.endswith('/chart1.xml'))
    chart = ET.fromstring(archive.read(chart_path))
    values = [float(n.text) for n in chart.findall('.//c:ser/c:val//c:pt/c:v', ns)]
    assert values == [row['score'] for row in evidence], values
    original = Path('C:/Users/user/AppData/Local/Temp/codex-clipboard-b275dc3b-4de1-4eb9-9aa0-9cb439990e1d.png').read_bytes()
    assert any(archive.read(name) == original for name in archive.namelist() if '/media/' in name)
print(json.dumps({'raw_samples_verified':20,'ticket_ids_verified':20,'chart_values_verified':20,'original_image_preserved':True,'sha256':hashlib.sha256(deck.read_bytes()).hexdigest()}, ensure_ascii=False))
