import pandas as pd
from pathlib import Path
from typing import Union, IO, Any

def read_spreadsheet(source: Union[str, Path, IO[bytes], Any]) -> pd.DataFrame:
    """
    Lê planilha a partir de:
      - caminho (str/Path)
      - arquivo em memória (BytesIO)
      - UploadedFile do Streamlit (tem .name e .getvalue())
      - file-like (tem .read)

    Suporta .xlsx/.xlsm com openpyxl e .xls com xlrd.
    """
    name = None

    # Caso seja caminho
    if isinstance(source, (str, Path)):
        p = Path(source)
        if not p.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {p}")
        name = p.name.lower()
        if name.endswith(".xls") and not name.endswith(".xlsx"):
            return pd.read_excel(p, engine="xlrd")
        return pd.read_excel(p, engine="openpyxl")

    # Caso seja UploadedFile do Streamlit
    if hasattr(source, "name") and hasattr(source, "getvalue"):
        name = str(source.name).lower()
        data = source.getvalue()
        if name.endswith(".xls") and not name.endswith(".xlsx"):
            return pd.read_excel(data, engine="xlrd")
        return pd.read_excel(data, engine="openpyxl")

    # Caso seja BytesIO / file-like
    if hasattr(source, "read"):
        # tenta usar .name se existir (nem sempre existe)
        if hasattr(source, "name"):
            name = str(getattr(source, "name")).lower()

        if name and name.endswith(".xls") and not name.endswith(".xlsx"):
            return pd.read_excel(source, engine="xlrd")
        return pd.read_excel(source, engine="openpyxl")

    raise TypeError("Formato de entrada inválido para read_spreadsheet().")
