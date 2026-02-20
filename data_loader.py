import pandas as pd
from pathlib import Path
from typing import Union, IO

def read_spreadsheet(source: Union[str, Path, IO[bytes]]) -> pd.DataFrame:
    """
    Lê planilha a partir de:
      - caminho (str/Path)
      - arquivo-like (ex.: BytesIO do Streamlit uploader)
    """
    # Caso seja caminho
    if isinstance(source, (str, Path)):
        p = Path(source)
        if not p.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {source}")
        return pd.read_excel(p, engine="openpyxl")

    # Caso seja arquivo em memória / file-like
    # (Streamlit uploader -> BytesIO)
    try:
        source.seek(0)
    except Exception:
        pass

    return pd.read_excel(source, engine="openpyxl")