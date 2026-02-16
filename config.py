# ===============================
# CONFIGURAÇÕES DO SISTEMA
# ===============================

# Colunas da planilha (ajuste só se mudar os nomes no Excel)

COL_STATUS = "STATUS"
COL_VENDEDOR = "VENDEDOR"
COL_UF_CLIENTE = "UF"
COL_CIDADE_CLIENTE = "CIDADE"

# Coluna com múltiplas cidades atendidas
# Formato: Cidade/UF; Cidade/UF|peso; ...
COL_CIDADES_ATENDIDAS = "CIDADES_ATENDIDAS"


# ===============================
# ARQUIVO PADRÃO DA PLANILHA
# ===============================

# Agora vamos usar somente XLSX (mais estável)
DEFAULT_SPREADSHEET_PATH = "planilha.xlsx"


# ===============================
# COORDENADAS# Ajuste aqui se sua planilha tiver nomes de colunas diferentes.
# Se uma coluna não existir, o app simplesmente ignora filtros dela.
import pandas as pd
from pathlib import Path
# ===============================# ===============================
# CONFIGURAÇÕES DO SISTEMA
# ===============================

# Colunas da planilha (ajuste só se mudar os nomes no Excel)

COL_STATUS = "STATUS"
COL_VENDEDOR = "VENDEDOR"
COL_UF_CLIENTE = "UF"
COL_CIDADE_CLIENTE = "CIDADE"

# Coluna com múltiplas cidades atendidas
# Formato: Cidade/UF; Cidade/UF|peso; ...
COL_CIDADES_ATENDIDAS = "CIDADES_ATENDIDAS"


# ===============================
# ARQUIVO PADRÃO DA PLANILHA
# ===============================

# Agora vamos usar somente XLSX (mais estável)
DEFAULT_SPREADSHEET_PATH = "planilha_provedores_com_cidades.xlsx"


# ===============================
# COORDENADAS
# ===============================

# (Opcional) Arquivo com lat/lon pronto
CIDADES_CSV = "cidades.csv"

# Cache automático de geocoding
CIDADES_CACHE_CSV = "cidades_cache.csv"

# CONFIGURAÇÕES DO SISTEMA
# ===============================

# Colunas da planilha (ajuste só se mudar os nomes no Excel)

COL_STATUS = "STATUS"
COL_VENDEDOR = "VENDEDOR"
COL_UF_CLIENTE = "UF"
COL_CIDADE_CLIENTE = "CIDADE"

# Coluna com múltiplas cidades atendidas
# Formato: Cidade/UF; Cidade/UF|peso; ...
COL_CIDADES_ATENDIDAS = "CIDADES_ATENDIDAS"


# ===============================
# ARQUIVO PADRÃO DA PLANILHA
# ===============================

# Agora vamos usar somente XLSX (mais estável)
DEFAULT_SPREADSHEET_PATH = "planilha_provedores_com_cidades.xlsx"


# ===============================
# COORDENADAS
# ===============================

# (Opcional) Arquivo com lat/lon pronto
CIDADES_CSV = "cidades.csv"

# Cache automático de geocoding
CIDADES_CACHE_CSV = "cidades_cache.csv"

def read_spreadsheet(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    suf = p.suffix.lower()

    if suf == ".xls":
        return pd.read_excel(p, engine="xlrd")
    elif suf in [".xlsx", ".xlsm"]:
        return pd.read_excel(p, engine="openpyxl")
    else:
        raise ValueError(f"Formato não suportado: {suf}")

COL_VENDEDOR = "VENDEDOR"
COL_UF_CLIENTE = "UF"
COL_CIDADE_CLIENTE = "CIDADE"

# coluna com múltiplas cidades atendidas (opção 2)
COL_CIDADES_ATENDIDAS = "CIDADES_ATENDIDAS"

# caminho padrão da planilha (pode subir no app também)
DEFAULT_SPREADSHEET_PATH = "planilha.xlsx"


# fontes de coordenadas
CIDADES_CSV = "cidades.csv"          # opcional (recomendado)
CIDADES_CACHE_CSV = "cidades_cache.csv"  # gerado automaticamente ao geocodificar

# ===============================

# (Opcional) Arquivo com lat/lon pronto
CIDADES_CSV = "cidades.csv"

# Cache automático de geocoding
CIDADES_CACHE_CSV = "cidades_cache.csv"
