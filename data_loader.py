import pandas as pd
from pathlib import Path

def read_spreadsheet(path: str) -> pd.DataFrame:
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    return pd.read_excel(p, engine="openpyxl")
