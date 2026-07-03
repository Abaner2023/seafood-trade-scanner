from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
INPUT_DATA_PATH = BASE_DIR / "data" / "processed" / "seafood_trade_clean.csv"

FINAL_DATA_PATH = PROCESSED_DATA_DIR / "seafood_trade_clean.csv"