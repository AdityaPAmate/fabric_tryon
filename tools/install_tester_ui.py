"""Install reviewed tester files, preserving a backup and all user outputs/reports."""
from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools/tester_ui'
TARGET = Path('C:/Users/ADMIN/Desktop/fabric_tryon_tester_ui')
FILES = ['index.html', 'js/app.js', 'js/api_options.js', 'js/catalog_client.js',
         'js/request_timer.js', 'css/style.css', 'server.py']


def main():
    if not (TARGET / 'index.html').is_file():
        raise SystemExit('Original tester UI not found; no files changed.')
    backup = ROOT / 'debug' / ('tester_ui_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    for relative in FILES:
        source, destination = SOURCE / relative, TARGET / relative
        if destination.exists():
            old = backup / relative
            old.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, old)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        if destination.read_bytes() != source.read_bytes():
            raise RuntimeError(f'Installed file mismatch: {relative}')
    print(f'Updated original tester UI: {TARGET}')
    print(f'Backup: {backup}')
    print('Existing reports and outputs preserved.')


if __name__ == '__main__':
    main()
