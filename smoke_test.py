import sys, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from fh6_tuning_sim.ui_desktop.main_window import MainWindow
from fh6_tuning_sim.ui_desktop.services.desktop_data_service import DesktopDataService
from fh6_tuning_sim.ui_desktop.pages.run_library_page import RunLibraryPage

ds = DesktopDataService()
print('1. DataService OK')

car = ds.get_car('car_ordinal_4265')
print('2. Car stock_pi:', car.get('performance_index', 0))

cats = ds.get_upgrade_categories()
print('3. Upgrade categories:', len(cats))

secs = ds.tune_parameters.get_sections()
print('4. Tune sections:', len(secs))

rts = ds.list_record_types()
print('5. Record types:', len(rts))

results = ds.search_database_entities('run')
print('6. Search results:', len(results))

runs = ds.search_runs(car_id='car_ordinal_4265')
print('7. Runs for car:', len(runs))

# Use actual build/tune IDs from the DB
builds = ds.builds.list_by_car('car_ordinal_4265')
if builds:
    bid = builds[0]['build_id']
    tunes = ds.tunes.list_by_build(bid)
    if tunes:
        tid = tunes[0]['tune_id']
        snap = ds.snapshots.ensure_default_setup_snapshot('car_ordinal_4265', bid, tid)
        print('8. Snapshot created:', snap.get('snapshot_name', '?'))

w = MainWindow()
print('9. MainWindow:', w.windowTitle())

rlp = RunLibraryPage(ds)
print('10. Snapshot filter removed:', not hasattr(rlp, '_setup_filter'))

# Test Tune Detail shows sections
from fh6_tuning_sim.ui_desktop.pages.tune_detail_page import TuneDetailPage
tdp = TuneDetailPage(ds)
print('11. TuneDetailPage created OK')

from fh6_tuning_sim.ui_desktop.pages.build_detail_page import BuildDetailPage
bdp = BuildDetailPage(ds)
print('12. BuildDetailPage created OK')

print('ALL SMOKE TESTS PASSED')
