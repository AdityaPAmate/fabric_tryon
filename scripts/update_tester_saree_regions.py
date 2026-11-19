"""Add optional Saree catalog source controls to the separate local tester UI.

Usage: python scripts/update_tester_saree_regions.py --tester-root <tester folder>
Existing files are backed up in this project's tmp directory before changes.
"""
import argparse
from pathlib import Path
import shutil

parser = argparse.ArgumentParser()
parser.add_argument('--tester-root', required=True, type=Path)
args = parser.parse_args()
root = args.tester_root.resolve(strict=True)
html_path, js_path = root / 'index.html', root / 'js' / 'app.js'
html, js = html_path.read_text(encoding='utf-8'), js_path.read_text(encoding='utf-8')
if 'saree-region-fields' in html:
    print('Saree region fields are already installed.')
    raise SystemExit(0)
anchor = '              <label id="fabric-crop-field" class="field field-wide">'
fields = '''              <div id="saree-region-fields" class="field field-wide hidden">
                <label class="field">Saree body crop (optional)
                  <input id="saree-body-crop-box" placeholder="left, upper, right, lower">
                  <small>Original image pixels for side and pleats. Blank uses detected body cloth.</small>
                </label>
                <label class="field">Saree long-side border crop (optional)
                  <input id="saree-border-crop-box" placeholder="left, upper, right, lower">
                  <small>Include the actual side edge, not the broad pallu end. The full-fabric view uses the entire upload.</small>
                </label>
              </div>
'''
if html.count(anchor) != 1:
    raise SystemExit('Cannot locate the tester crop controls; no files changed.')
html = html.replace(anchor, fields + anchor, 1)
anchor = "  const catalog = generationMode.value === 'catalog';"
if js.count(anchor) != 1:
    raise SystemExit('Cannot locate tester mode handling; no files changed.')
js = js.replace(anchor, anchor + '''
  const sareeRegions = fabric && catalog && garmentType.value === 'saree';
  document.querySelector('#saree-region-fields').classList.toggle('hidden', !sareeRegions);
  document.querySelectorAll('#saree-region-fields input').forEach(input => input.disabled = !sareeRegions);
''', 1)
anchor = "  payload.append('options', JSON.stringify(options));"
if js.count(anchor) != 1:
    raise SystemExit('Cannot locate tester option serialization; no files changed.')
js = js.replace(anchor, '''  if (isCatalog && usesFabric && garmentType.value === 'saree') {
    for (const region of ['body', 'border']) {
      const raw = document.querySelector('#saree-' + region + '-crop-box').value.trim();
      if (!raw) continue;
      const parts = raw.split(','), box = parts.map(value => Number(value.trim()));
      if (parts.some(value => !value.trim()) || box.length !== 4 || !box.every(Number.isInteger) ||
          box[0] < 0 || box[1] < 0 || box[2] <= box[0] || box[3] <= box[1]) {
        showError('Saree ' + region + ' crop must be four integers: left, upper, right, lower.');
        generateButton.disabled = false;
        setGenerationMode();
        return;
      }
      options['fabric_' + region + '_crop_box'] = box;
    }
  }
''' + anchor, 1)
backup = Path(__file__).resolve().parents[1] / 'tmp' / 'tester_saree_region_backup'
backup.mkdir(parents=True, exist_ok=True)
for source in (html_path, js_path):
    saved = backup / source.name
    if not saved.exists():
        shutil.copy2(source, saved)
html_path.write_text(html, encoding='utf-8')
js_path.write_text(js, encoding='utf-8')
print('Updated', html_path, 'and', js_path)
print('Backups:', backup)
