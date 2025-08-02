import os

# BASE_DIR: azcon_match folderinin tam yolu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# PROJECT_ROOT: bir üst səviyyə (azcon_alqoritm2)
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, os.pardir))

# master_db.xlsx faylının tam yolu
MASTER_PATH = os.path.join(PROJECT_ROOT, 'data', 'master_db.xlsx')

# sütun adları
MASTER_TEXT_COL = "Malların (işlərin və xidmətlərin) adı"
MASTER_FLAG_COL = "Tip"
PRICE_COL       = "Qiymət"
UNIT_COL        = "Ölçü vahidi"

TOP_N      = 5
THRESHOLD  = 65
PRICE_AVG_MIN_SCORE = 8
MIN_COVER  = 0.50
SHOW_MATCHES = True
