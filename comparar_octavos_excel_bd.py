"""
Compara puntajes por item (H/I/J/K/L/M/N/O) entre Excel TBL MASTER y BD
para los partidos P089 y P090 (Ronda de 16 - octavos).

Ejecutar con el venv del backend activo y uvicorn NO necesario.
Requiere: pip install psycopg2-binary openpyxl tabulate (ya instalados en venv)

Uso:
    cd "C:\\proyecto FAST API"
    backend\\.venv\\Scripts\\activate
    python comparar_octavos_excel_bd.py
"""

import psycopg2
import json, sys
from tabulate import tabulate

# ── Conexión BD ───────────────────────────────────────────────────────────────
BECBUC_DSN = dict(host='localhost', port=5432, dbname='becbuc',
                  user='app_user', password='superpassword')
APP_DSN    = dict(host='localhost', port=5432, dbname='app_db',
                  user='app_user', password='superpassword')

# ── Datos Excel embebidos (extraídos de TBL MASTER hoja 50-) ─────────────────
EXCEL_DATA = {
  "P089": {
    "@BS": {"pred_local": 0, "pred_vis": 0, "pred_j": 4, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 35, "pred_o1": 5, "pred_o2": 4, "H": 0, "I": 0, "J": 0, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 4},
    "AAA": {"pred_local": 1, "pred_vis": 0, "pred_j": 3, "pred_k": 0, "pred_l": 0, "pred_m": 1, "pred_n": 45, "pred_o1": 4, "pred_o2": 5, "H": 0, "I": 0, "J": 2, "K": 2, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 4},
    "ALEJANDROLEGUI": {"pred_local": 1, "pred_vis": 0, "pred_j": 3, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 20, "pred_o1": 5, "pred_o2": 3, "H": 0, "I": 0, "J": 2, "K": 2, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 4},
    "ALEVO": {"pred_local": 1, "pred_vis": 2, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 2, "pred_n": 30, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "ALFAORION 99": {"pred_local": 0, "pred_vis": 2, "pred_j": 4, "pred_k": 1, "pred_l": 1, "pred_m": 1, "pred_n": 40, "pred_o1": 5, "pred_o2": 3, "H": 16, "I": 0, "J": 0, "K": 0, "L": 2, "M": 2, "N": 0, "O1": 0, "O2": 0, "TOTAL": 20},
    "CAFICHO": {"pred_local": 0, "pred_vis": 1, "pred_j": 2, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 30, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 0, "K": 2, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 18},
    "CAYETANO": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 1, "pred_n": 25, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 2, "N": 0, "O1": 0, "O2": 0, "TOTAL": 24},
    "CHECHO": {"pred_local": 1, "pred_vis": 2, "pred_j": 4, "pred_k": 0, "pred_l": 2, "pred_m": 1, "pred_n": 12, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 0, "K": 2, "L": 0, "M": 2, "N": 0, "O1": 0, "O2": 0, "TOTAL": 20},
    "CHEREM": {"pred_local": 1, "pred_vis": 0, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 0, "pred_o1": 5, "pred_o2": 4, "H": 0, "I": 0, "J": 0, "K": 2, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 2},
    "COCO": {"pred_local": 0, "pred_vis": 2, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 55, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "COTO": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 1, "pred_l": 0, "pred_m": 0, "pred_n": 45, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 2, "K": 0, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 18},
    "DECANITA": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 45, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "EDGAR": {"pred_local": 1, "pred_vis": 0, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 30, "pred_o1": 5, "pred_o2": 4, "H": 0, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 6},
    "ELIASMAJUL": {"pred_local": 1, "pred_vis": 0, "pred_j": 4, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 30, "pred_o1": 5, "pred_o2": 4, "H": 0, "I": 0, "J": 0, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 4},
    "ESYL": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 27, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 2, "K": 2, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 20},
    "FIDELYOLI": {"pred_local": 0, "pred_vis": 2, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 1, "pred_n": 35, "pred_o1": 5, "pred_o2": 3, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 2, "N": 0, "O1": 0, "O2": 0, "TOTAL": 24},
    "FSCC": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 12, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "GBC": {"pred_local": 0, "pred_vis": 2, "pred_j": 3, "pred_k": 0, "pred_l": 0, "pred_m": 2, "pred_n": 37, "pred_o1": 5, "pred_o2": 3, "H": 16, "I": 0, "J": 2, "K": 2, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 20},
    "GH1S": {"pred_local": 1, "pred_vis": 2, "pred_j": 4, "pred_k": 0, "pred_l": 1, "pred_m": 1, "pred_n": 35, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 0, "K": 2, "L": 2, "M": 2, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "GRILLITO": {"pred_local": 0, "pred_vis": 2, "pred_j": 4, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 68, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 0, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 20},
    "GUSTAV TOTHELIGHTHOUSE": {"pred_local": 0, "pred_vis": 1, "pred_j": 2, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 45, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 0, "K": 2, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 18},
    "HAKEMBO": {"pred_local": 0, "pred_vis": 1, "pred_j": 4, "pred_k": 0, "pred_l": 0, "pred_m": 1, "pred_n": 15, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 0, "K": 2, "L": 0, "M": 2, "N": 0, "O1": 0, "O2": 0, "TOTAL": 20},
    "HS": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 24, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "JUANE": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 1, "pred_n": 25, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 2, "N": 0, "O1": 0, "O2": 0, "TOTAL": 24},
    "KIKAO": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 45, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "LAV": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 25, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "LUDIE-Z": {"pred_local": 0, "pred_vis": 2, "pred_j": 4, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 45, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 0, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 20},
    "LUISMA": {"pred_local": 0, "pred_vis": 2, "pred_j": 4, "pred_k": 0, "pred_l": 1, "pred_m": 1, "pred_n": 45, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 0, "K": 2, "L": 2, "M": 2, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "MONKEY": {"pred_local": 0, "pred_vis": 2, "pred_j": 4, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 55, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 0, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 20},
    "MORO": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 37, "pred_o1": 5, "pred_o2": 3, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "MOÑO": {"pred_local": 0, "pred_vis": 2, "pred_j": 5, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 65, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 0, "K": 2, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 18},
    "OTI": {"pred_local": 1, "pred_vis": 0, "pred_j": 4, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 39, "pred_o1": 5, "pred_o2": 4, "H": 0, "I": 0, "J": 0, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 4},
    "PATITO": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 45, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 2, "K": 2, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 20},
    "PATO": {"pred_local": 0, "pred_vis": 1, "pred_j": 4, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 15, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 0, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 20},
    "PINGUERO": {"pred_local": 0, "pred_vis": 1, "pred_j": 4, "pred_k": 0, "pred_l": 1, "pred_m": 1, "pred_n": 35, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 0, "K": 2, "L": 2, "M": 2, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "PUCHETA": {"pred_local": 1, "pred_vis": 0, "pred_j": 3, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 45, "pred_o1": 5, "pred_o2": 4, "H": 0, "I": 0, "J": 2, "K": 2, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 4},
    "QUIROGA": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 27, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "SAJANO FREDDY": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 27, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "SANBIE": {"pred_local": 1, "pred_vis": 2, "pred_j": 4, "pred_k": 1, "pred_l": 2, "pred_m": 1, "pred_n": 35, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 0, "K": 0, "L": 0, "M": 2, "N": 0, "O1": 0, "O2": 0, "TOTAL": 18},
    "SEBA": {"pred_local": 1, "pred_vis": 2, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 35, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "SONI": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 7, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "TIM PAYNE": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 1, "pred_n": 35, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 2, "N": 0, "O1": 0, "O2": 0, "TOTAL": 24},
    "TONY": {"pred_local": 0, "pred_vis": 1, "pred_j": 3, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 9, "pred_o1": 5, "pred_o2": 4, "H": 16, "I": 0, "J": 2, "K": 2, "L": 2, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22},
    "VITRA": {"pred_local": 0, "pred_vis": 1, "pred_j": 4, "pred_k": 0, "pred_l": 1, "pred_m": 1, "pred_n": 35, "pred_o1": 4, "pred_o2": 5, "H": 16, "I": 0, "J": 0, "K": 2, "L": 2, "M": 2, "N": 0, "O1": 0, "O2": 0, "TOTAL": 22}
  },
  "P090": {
    "@BS": {"pred_local": 0, "pred_vis": 3, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 10, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "AAA": {"pred_local": 0, "pred_vis": 2, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 35, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "ALEJANDROLEGUI": {"pred_local": 0, "pred_vis": 2, "pred_j": 2, "pred_k": 1, "pred_l": 0, "pred_m": 0, "pred_n": 33, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 0, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 8},
    "ALEVO": {"pred_local": 1, "pred_vis": 0, "pred_j": 1, "pred_k": 1, "pred_l": 0, "pred_m": 0, "pred_n": 22, "pred_o1": 4, "pred_o2": 5, "H": 0, "I": 0, "J": 0, "K": 0, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 0},
    "ALFAORION 99": {"pred_local": 0, "pred_vis": 2, "pred_j": 2, "pred_k": 1, "pred_l": 0, "pred_m": 1, "pred_n": 40, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 0, "L": 0, "M": 1, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "CAFICHO": {"pred_local": 0, "pred_vis": 1, "pred_j": 1, "pred_k": 1, "pred_l": 0, "pred_m": 0, "pred_n": 30, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 0, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 8},
    "CAYETANO": {"pred_local": 0, "pred_vis": 3, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 25, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "CHECHO": {"pred_local": 0, "pred_vis": 2, "pred_j": 2, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 11, "pred_o1": 4, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "CHEREM": {"pred_local": 0, "pred_vis": 1, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 0, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "COCO": {"pred_local": 0, "pred_vis": 3, "pred_j": 0, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 55, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 1, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 10},
    "COTO": {"pred_local": 0, "pred_vis": 2, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 45, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "DECANITA": {"pred_local": 0, "pred_vis": 3, "pred_j": 0, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 45, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 1, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 10},
    "EDGAR": {"pred_local": 0, "pred_vis": 2, "pred_j": 1, "pred_k": 1, "pred_l": 0, "pred_m": 0, "pred_n": 30, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 0, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 8},
    "ELIASMAJUL": {"pred_local": 0, "pred_vis": 3, "pred_j": 2, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 30, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "ESYL": {"pred_local": 0, "pred_vis": 1, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 27, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "FIDELYOLI": {"pred_local": 0, "pred_vis": 2, "pred_j": 2, "pred_k": 0, "pred_l": 0, "pred_m": 1, "pred_n": 35, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 1, "N": 0, "O1": 0, "O2": 0, "TOTAL": 10},
    "FSCC": {"pred_local": 0, "pred_vis": 3, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 12, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "GBC": {"pred_local": 0, "pred_vis": 3, "pred_j": 1, "pred_k": 1, "pred_l": 1, "pred_m": 1, "pred_n": 37, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 16, "J": 0, "K": 0, "L": 1, "M": 1, "N": 0, "O1": 0, "O2": 0, "TOTAL": 26},
    "GH1S": {"pred_local": 0, "pred_vis": 3, "pred_j": 1, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 35, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 1, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 10},
    "GRILLITO": {"pred_local": 1, "pred_vis": 0, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 68, "pred_o1": 4, "pred_o2": 5, "H": 0, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 1, "O1": 0, "O2": 0, "TOTAL": 2},
    "GUSTAV TOTHELIGHTHOUSE": {"pred_local": 0, "pred_vis": 1, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 45, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "HAKEMBO": {"pred_local": 0, "pred_vis": 1, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 1, "pred_n": 15, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 1, "N": 0, "O1": 0, "O2": 0, "TOTAL": 10},
    "HS": {"pred_local": 0, "pred_vis": 2, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 24, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "JUANE": {"pred_local": 0, "pred_vis": 2, "pred_j": 2, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 25, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 1, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 10},
    "KIKAO": {"pred_local": 0, "pred_vis": 1, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 45, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "LAV": {"pred_local": 0, "pred_vis": 2, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 25, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "LUDIE-Z": {"pred_local": 0, "pred_vis": 3, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 45, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "LUISMA": {"pred_local": 0, "pred_vis": 3, "pred_j": 2, "pred_k": 0, "pred_l": 0, "pred_m": 1, "pred_n": 45, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 1, "N": 0, "O1": 0, "O2": 0, "TOTAL": 10},
    "MONKEY": {"pred_local": 0, "pred_vis": 2, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 55, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "MORO": {"pred_local": 0, "pred_vis": 3, "pred_j": 1, "pred_k": 0, "pred_l": 1, "pred_m": 0, "pred_n": 37, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 1, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 10},
    "MOÑO": {"pred_local": 0, "pred_vis": 3, "pred_j": 0, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 65, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 1, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 10},
    "OTI": {"pred_local": 0, "pred_vis": 2, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 39, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "PATITO": {"pred_local": 0, "pred_vis": 1, "pred_j": 2, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 45, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "PATO": {"pred_local": 0, "pred_vis": 2, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 15, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "PINGUERO": {"pred_local": 0, "pred_vis": 1, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 35, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "PUCHETA": {"pred_local": 1, "pred_vis": 0, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 45, "pred_o1": 3, "pred_o2": 5, "H": 0, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 1},
    "QUIROGA": {"pred_local": 0, "pred_vis": 3, "pred_j": 2, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 27, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "SAJANO FREDDY": {"pred_local": 0, "pred_vis": 3, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 27, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "SANBIE": {"pred_local": 0, "pred_vis": 2, "pred_j": 2, "pred_k": 0, "pred_l": 0, "pred_m": 1, "pred_n": 35, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 1, "N": 0, "O1": 0, "O2": 0, "TOTAL": 10},
    "SEBA": {"pred_local": 0, "pred_vis": 2, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 35, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "SONI": {"pred_local": 0, "pred_vis": 2, "pred_j": 0, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 7, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 1, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 10},
    "TIM PAYNE": {"pred_local": 0, "pred_vis": 3, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 35, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "TONY": {"pred_local": 0, "pred_vis": 2, "pred_j": 1, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 9, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9},
    "VITRA": {"pred_local": 0, "pred_vis": 2, "pred_j": 2, "pred_k": 0, "pred_l": 0, "pred_m": 0, "pred_n": 35, "pred_o1": 3, "pred_o2": 5, "H": 8, "I": 0, "J": 0, "K": 1, "L": 0, "M": 0, "N": 0, "O1": 0, "O2": 0, "TOTAL": 9}
  }
}

# ── Mapeo alias Excel → username BD (normalizado a minúscula) ─────────────────
# Algunos alias del Excel no coinciden exactamente con el username en BD.
# El script intenta match automático case-insensitive; esta tabla es para casos especiales.
ALIAS_MAP = {
    "@bs"                    : "@bs",
    "alfaorion 99"           : "alfaorion 99",
    "alejandrolegui"         : "alejandrolegui",
    "gustav tothelighthouse" : "gustav tothelighthouse",
    "sajano freddy"          : "sajano freddy",
    "tim payne"              : "tim payne",
}

ITEMS = ['H', 'I', 'J', 'K', 'L', 'M', 'N', 'O']

def get_bd_data(partido_nums):
    """Consulta puntaje_detalle para los partidos dados (por numero_fifa)."""
    becbuc = psycopg2.connect(**BECBUC_DSN)
    app    = psycopg2.connect(**APP_DSN)

    # 1) Obtener partido_ids por numero_fifa
    cur = becbuc.cursor()
    cur.execute("""
        SELECT id, numero_fifa
        FROM partido
        WHERE numero_fifa = ANY(%s)
    """, (partido_nums,))
    partido_map = {row[1]: row[0] for row in cur.fetchall()}  # {numero_fifa: partido_id}

    if not partido_map:
        print("ERROR: no se encontraron partidos con esos numero_fifa en BD")
        sys.exit(1)

    for num, pid in partido_map.items():
        print(f"  P{num:03d} → partido_id={pid}")

    # 2) Obtener aliases desde app_db
    cur2 = app.cursor()
    cur2.execute("SELECT id, username FROM users WHERE id BETWEEN 9 AND 60")
    user_map = {row[0]: row[1].upper() for row in cur2.fetchall()}  # {id: USERNAME}
    user_map_rev = {v: k for k, v in user_map.items()}              # {USERNAME: id}

    # 3) Obtener puntaje_detalle
    partido_ids = list(partido_map.values())
    cur.execute("""
        SELECT
            pd.apostador_id,
            pd.partido_id,
            COALESCE(pd.pts_resultado,       0) AS H,
            COALESCE(pd.pts_marcador,        0) AS I,
            COALESCE(pd.pts_amarillas,       0) AS J,
            COALESCE(pd.pts_rojas,           0) AS K,
            COALESCE(pd.pts_var,             0) AS L,
            COALESCE(pd.pts_penales_partido, 0) AS M,
            COALESCE(pd.pts_minuto,          0) AS N,
            COALESCE(pd.pts_penales_tanda,   0) AS O
        FROM puntaje_detalle pd
        WHERE pd.partido_id = ANY(%s)
    """, (partido_ids,))

    # Estructura: {numero_fifa: {apostador_id: {H,I,J,K,L,M,N,O}}}
    result = {}
    pid_to_num = {v: k for k, v in partido_map.items()}  # {partido_id: numero_fifa}
    for row in cur.fetchall():
        aid, pid, h, i, j, k, l, m, n, o = row
        num = pid_to_num[pid]
        if num not in result:
            result[num] = {}
        result[num][aid] = dict(H=h, I=i, J=j, K=k, L=l, M=m, N=n, O=o)

    cur.close(); cur2.close()
    becbuc.close(); app.close()
    return result, user_map, user_map_rev, partido_map

def compare_partido(partido_label, excel_apos, bd_apos_map, user_map):
    """
    Compara Excel vs BD para un partido.
    Devuelve lista de diffs y totales por columna.
    """
    COLS = ITEMS  # H I J K L M N O
    totals_excel = {c: 0 for c in COLS + ['TOTAL']}
    totals_bd    = {c: 0 for c in COLS + ['TOTAL']}
    diffs = []
    unmatched = []

    for alias_upper, ex_data in sorted(excel_apos.items()):
        # Buscar apostador_id por alias
        alias_lo = alias_upper.lower()
        aid = None
        for uid, uname in user_map.items():
            if uname.lower() == alias_lo:
                aid = uid; break
        # Si no encontró, buscar substring
        if aid is None:
            for uid, uname in user_map.items():
                if alias_lo in uname.lower() or uname.lower() in alias_lo:
                    aid = uid; break

        if aid is None:
            unmatched.append(alias_upper)
            continue

        bd_data = bd_apos_map.get(aid, {})
        if not bd_data:
            unmatched.append(f"{alias_upper} (sin puntaje_detalle en BD)")
            continue

        ex_total = ex_data['H'] + ex_data['I'] + ex_data['J'] + ex_data['K'] + \
                   ex_data['L'] + ex_data['M'] + ex_data['N'] + ex_data['O1'] + ex_data['O2']
        bd_o     = bd_data['O']  # O = O1+O2 en BD
        bd_total = bd_data['H'] + bd_data['I'] + bd_data['J'] + bd_data['K'] + \
                   bd_data['L'] + bd_data['M'] + bd_data['N'] + bd_o

        # Acumular totales
        for c in COLS:
            if c == 'O':
                totals_excel[c] += ex_data['O1'] + ex_data['O2']
                totals_bd[c]    += bd_o
            else:
                totals_excel[c] += ex_data[c]
                totals_bd[c]    += bd_data[c]
        totals_excel['TOTAL'] += ex_total
        totals_bd['TOTAL']    += bd_total

        # Detectar diferencias por item
        item_diffs = []
        for c in COLS:
            ex_val = ex_data['O1'] + ex_data['O2'] if c == 'O' else ex_data[c]
            bd_val = bd_data[c] if c == 'O' else bd_data[c]
            if ex_val != bd_val:
                item_diffs.append(f"{c}: Excel={ex_val} BD={bd_val} (Δ{bd_val-ex_val:+d})")
        if ex_total != bd_total:
            item_diffs.append(f"TOTAL: Excel={ex_total} BD={bd_total} (Δ{bd_total-ex_total:+d})")
        if item_diffs:
            diffs.append((alias_upper, item_diffs))

    return diffs, totals_excel, totals_bd, unmatched

def main():
    print("=" * 70)
    print("COMPARACION EXCEL vs BD — Octavos de Final (R16)")
    print("P089: Paraguay 0-1 France | P090: Canada 0-3 Morocco")
    print("=" * 70)

    print("\n→ Conectando a BD y obteniendo datos...")
    bd_result, user_map, user_map_rev, partido_map = get_bd_data([89, 90])

    for num_str, label, real in [
        (89, "P089 · Paraguay 0-1 France",   "(R16 — Octavos)"),
        (90, "P090 · Canada 0-3 Morocco",     "(R16 — Octavos)"),
    ]:
        excel_apos = EXCEL_DATA.get(f"P{num_str:03d}", {})
        bd_apos    = bd_result.get(num_str, {})

        print(f"\n{'─'*70}")
        print(f"  {label}  {real}")
        print(f"{'─'*70}")
        print(f"  Apostadores en Excel: {len(excel_apos)} | En BD: {len(bd_apos)}")

        diffs, tot_ex, tot_bd, unmatched = compare_partido(
            label, excel_apos, bd_apos, user_map)

        if unmatched:
            print(f"\n  ⚠ Sin match en BD: {', '.join(unmatched)}")

        # Tabla totales por columna
        print("\n  TOTALES POR ÍTEM:")
        headers = ['Fuente', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'TOTAL']
        rows = [
            ['Excel'] + [tot_ex[c] for c in ITEMS] + [tot_ex['TOTAL']],
            ['BD']    + [tot_bd[c] for c in ITEMS] + [tot_bd['TOTAL']],
            ['Δ(BD-Ex)'] + [tot_bd[c]-tot_ex[c] for c in ITEMS] + [tot_bd['TOTAL']-tot_ex['TOTAL']],
        ]
        print(tabulate(rows, headers=headers, tablefmt='simple'))

        if not diffs:
            print("\n  ✅ Sin diferencias individuales.")
        else:
            print(f"\n  ⚠ {len(diffs)} apostador(es) con diferencias:")
            for alias, items in diffs:
                print(f"    {alias}:")
                for d in items:
                    print(f"      • {d}")

    print("\n" + "=" * 70)
    print("FIN")

if __name__ == '__main__':
    main()
