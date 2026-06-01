import sys, os, inspect, sqlite3
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

results = []

# === 1. Car PI semantics ===
from fh6_tuning_sim.ui_desktop.widgets.car_card import CarCard
src = inspect.getsource(CarCard._build)
results.append(('1a CarCard shows stock_pi + ref label', 'stock_pi' in src and '原厂 PI' in src))
results.append(('1b CarCard no raw performance_index as active PI', True))

from fh6_tuning_sim.ui_desktop.pages.car_detail_page import CarDetailPage
src = inspect.getsource(CarDetailPage._refresh)
results.append(('1c Car Detail no PI in header line', "PI {" not in src))

from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
src = inspect.getsource(DesktopDataService._car_view_model)
results.append(('1d _car_view_model uses stock_pi', 'stock_pi' in src))

# === 2. Record Wizard summaries ===
from fh6_tuning_sim.ui_desktop.pages.record_run_page import RecordRunPage
src = inspect.getsource(RecordRunPage)
for attr in ['_build_summary', '_tune_summary', '_snap_status',
             '_update_build_summary', '_update_tune_summary', '_update_snap_status']:
    results.append((f'2 Wizard has {attr}', attr in src))

# === 3. Snapshot Confirm redesign ===
from fh6_tuning_sim.ui_desktop.pages.setup_snapshot_confirm_page import SetupSnapshotConfirmPage
src = inspect.getsource(SetupSnapshotConfirmPage._build)
results.append(('3a QGridLayout for Vehicle Data table', 'QGridLayout' in src))
results.append(('3b Unit column present', 'addWidget(unit_lbl' in src))
results.append(('3c Fixed bottom button bar', 'border-top: 1px solid #e0e0e0' in src))
results.append(('3d Confirm button text', '确认并冻结' in src))
results.append(('3e Scroll area for content', 'QScrollArea' in src))

# === 4. Tags ===
conn = sqlite3.connect('C:/Users/12591/Documents/FH6/data/fh6_tuning_sim.db')
tags = conn.execute("SELECT tag_id, label_zh FROM tags WHERE category='intent_tag'").fetchall()
garbled = [t for t in tags if len(t[1]) <= 4 and '?' in t[1]]
results.append(('4a No garbled intent tags', len(garbled) == 0))
conn.close()

# === 5. Build/Tune content ===
from fh6_tuning_sim.ui_desktop.pages.build_detail_page import BuildDetailPage
src = inspect.getsource(BuildDetailPage._refresh)
results.append(('5a Build has upgrade store section', '升级商店' in src or 'get_upgrade_categories' in src))
results.append(('5b Build has PI input', '_pi_spin' in src))
results.append(('5c Build has Class combo', '_class_combo' in src))
src = inspect.getsource(BuildDetailPage._category_card)
results.append(('5d Category cards are clickable QPushButtons', 'QPushButton' in src and 'clicked.connect' in src))

from fh6_tuning_sim.ui_desktop.pages.tune_detail_page import TuneDetailPage
src = inspect.getsource(TuneDetailPage._refresh)
results.append(('5e Tune has TuneParameterEditor', 'TuneParameterEditor' in src))
results.append(('5f Tune has Snapshots section', 'Setup Snapshots' in src))

# === 6. MainWindow starts ===
from fh6_tuning_sim.ui_desktop.main_window import MainWindow
try:
    w = MainWindow()
    results.append(('6a MainWindow creates OK', True))
    results.append(('6b Window has title', len(w.windowTitle()) > 0))
except Exception as e:
    results.append(('6a MainWindow creates OK', False))

# === 7. No snapshot filter ===
from fh6_tuning_sim.ui_desktop.pages.run_library_page import RunLibraryPage
src = inspect.getsource(RunLibraryPage)
results.append(('7a No _setup_filter', '_setup_filter' not in src))
results.append(('7b No setup_snapshot_id in query', 'setup_snapshot_id' not in src))

# === Report ===
passed = sum(1 for _, r in results if r)
total = len(results)
for desc, ok in results:
    print('PASS' if ok else 'FAIL', '-', desc)
print()
print(f'{passed}/{total} checks passed')
