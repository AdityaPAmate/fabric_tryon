"""Install the optional border orientation control in the separate Desktop tester."""
import argparse
from pathlib import Path
import shutil

parser=argparse.ArgumentParser()
parser.add_argument('--tester-root',type=Path,required=True)
args=parser.parse_args()
root=args.tester_root.resolve(strict=True)
html_path,js_path=root/'index.html',root/'js'/'app.js'
html,js=html_path.read_text(encoding='utf-8'),js_path.read_text(encoding='utf-8')
marker='saree-border-rotation'
if marker in html and marker in js:
    print('Border orientation is already installed.');raise SystemExit(0)
if marker in html or marker in js:
    raise SystemExit('Partial installation detected; no files changed.')
anchor='              <div id="saree-region-fields" class="field field-wide hidden">'
if html.count(anchor)!=1:
    raise SystemExit('Install Saree region fields first; no files changed.')
fields='''
                <label class="field">Saree border orientation
                  <select id="saree-border-rotation">
                    <option value="auto">Auto (outer edge on left)</option>
                    <option value="0">Keep source direction</option>
                    <option value="180">Rotate 180 degrees</option>
                  </select>
                </label>'''
html=html.replace(anchor,anchor+fields,1)
mode="document.querySelectorAll('#saree-region-fields input')"
if js.count(mode)!=1:
    raise SystemExit('Cannot locate region mode handling; no files changed.')
js=js.replace(mode,"document.querySelectorAll('#saree-region-fields input, #saree-region-fields select')",1)
anchor="  payload.append('options', JSON.stringify(options));"
if js.count(anchor)!=1:
    raise SystemExit('Cannot locate options serialization; no files changed.')
js=js.replace(anchor,'''  if (isCatalog && usesFabric && garmentType.value === 'saree') {
    const rotation = document.querySelector('#saree-border-rotation').value;
    if (rotation !== 'auto') options.fabric_border_rotation = Number(rotation);
  }
'''+anchor,1)
backup=Path(__file__).resolve().parents[1]/'tmp'/'tester_border_orientation_backup'
backup.mkdir(parents=True,exist_ok=True)
for path in (html_path,js_path):
    saved=backup/path.name
    if not saved.exists():shutil.copy2(path,saved)
html_path.write_text(html,encoding='utf-8');js_path.write_text(js,encoding='utf-8')
print('Installed orientation control; refresh the tester page. Backups:',backup)
