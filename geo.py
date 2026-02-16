import pandas as pd
from pathlib import Path
from geopy.geocoders import Nominatim

def explode_cidades(df: pd.DataFrame, col="CIDADES_ATENDIDAS") -> pd.DataFrame:
    df = df.copy()
    df[col] = df[col].fillna("").astype(str)

    # separa por ';' e explode em várias linhas
    df[col] = df[col].apply(lambda s: [x.strip() for x in s.split(";") if x.strip()])
    df = df.explode(col, ignore_index=True)

    # separa peso opcional: "Cidade/UF|peso"
    parte = df[col].str.split("|", n=1, expand=True)
    cidade_uf = parte[0].fillna("").str.strip()
    peso = parte[1] if parte.shape[1] > 1 else None

    # quebra Cidade/UF
    cu = cidade_uf.str.rsplit("/", n=1, expand=True)
    df["CIDADE_ATENDIDA"] = cu[0].fillna("").str.strip()
    df["UF_ATENDIDA"] = cu[1].fillna("").str.strip().str.upper()

    # peso
    if peso is None:
        df["PESO"] = 1.0
    else:
        df["PESO"] = pd.to_numeric(peso, errors="coerce").fillna(1.0).astype(float)

    # normalizações
    df["cidade_norm"] = df["CIDADE_ATENDIDA"].str.lower().str.strip()
    df["uf_norm"] = df["UF_ATENDIDA"].str.upper().str.strip()

    # remove inválidos
    df = df[(df["CIDADE_ATENDIDA"] != "") & (df["UF_ATENDIDA"] != "")]
    return df

def load_city_coords_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["cidade_norm"] = df["cidade"].astype(str).str.strip().str.lower()
    df["uf_norm"] = df["uf"].astype(str).str.strip().str.upper()
    return df[["cidade_norm","uf_norm","lat","lon"]]

def load_cache(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame(columns=["cidade_norm","uf_norm","lat","lon"])
    df = pd.read_csv(p)
    return df[["cidade_norm","uf_norm","lat","lon"]]

def save_cache(path: str, df_cache: pd.DataFrame) -> None:
    df_cache = df_cache.drop_duplicates(subset=["cidade_norm","uf_norm"]).copy()
    df_cache.to_csv(path, index=False)

def geocode_missing(unique_cities: pd.DataFrame, cache_df: pd.DataFrame, user_agent="heatmap_provedores_app"):
    # unique_cities: cidade_norm, uf_norm, CIDADE_ATENDIDA, UF_ATENDIDA
    # cache_df: cidade_norm, uf_norm, lat, lon
    geolocator = Nominatim(user_agent=user_agent, timeout=10)
    cache_key = set(zip(cache_df["cidade_norm"], cache_df["uf_norm"]))

    new_rows = []
    for _, row in unique_cities.iterrows():
        key = (row["cidade_norm"], row["uf_norm"])
        if key in cache_key:
            continue
        # consulta "Cidade, UF, Brasil"
        query = f'{row["CIDADE_ATENDIDA"]}, {row["UF_ATENDIDA"]}, Brasil'
        loc = None
        try:
            loc = geolocator.geocode(query)
        except Exception:
            loc = None
        if loc is not None:
            new_rows.append({
                "cidade_norm": row["cidade_norm"],
                "uf_norm": row["uf_norm"],
                "lat": float(loc.latitude),
                "lon": float(loc.longitude),
            })
    if new_rows:
        cache_df = pd.concat([cache_df, pd.DataFrame(new_rows)], ignore_index=True)
    return cache_df
