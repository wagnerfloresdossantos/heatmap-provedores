import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from pathlib import Path
import streamlit.components.v1 as components

from auth import require_login, logout_button
from data_loader import read_spreadsheet
from geo import (
    explode_cidades,
    load_city_coords_csv,
    load_cache,
    save_cache,
    geocode_missing,
)
import config

LOGO_PATH = Path("assets/logo_oletv.png")


# -----------------------------
# Helpers
# -----------------------------
def col_exists(df: pd.DataFrame, name: str) -> bool:
    return name in df.columns


def _norm_col(c: str) -> str:
    c = str(c).replace("\n", " ").replace("\r", " ")
    c = " ".join(c.split())
    return c.strip()


def _safe(v) -> str:
    if pd.isna(v):
        return ""
    return str(v).strip()


def _format_money(v) -> str:
    """Formata valor para padrão brasileiro: 3500,00"""
    if pd.isna(v) or v == "":
        return ""
    try:
        val = float(v)
        return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(v)


def _format_date(v) -> str:
    """Formata data para dd/mm/aaaa"""
    if pd.isna(v) or v == "":
        return ""
    try:
        d = pd.to_datetime(v)
        return d.strftime("%d/%m/%Y")
    except Exception:
        return str(v)


def _format_tempo_contrato(dt_value) -> str:
    """Retorna tempo desde a assinatura (ex: 1a 3m, 2m 12d)."""
    if pd.isna(dt_value) or dt_value == "":
        return ""
    try:
        dt = pd.to_datetime(dt_value)
        if pd.isna(dt):
            return ""

        today = pd.Timestamp.today().normalize()
        dt = dt.normalize()

        if dt > today:
            return "0d"

        delta_days = (today - dt).days

        years = delta_days // 365
        rem = delta_days % 365
        months = rem // 30
        days = rem % 30

        parts = []
        if years > 0:
            parts.append(f"{years}a")
        if months > 0:
            parts.append(f"{months}m")
        if years == 0 and months == 0:
            parts.append(f"{days}d")

        return " ".join(parts).strip()
    except Exception:
        return ""


# -----------------------------
# App
# -----------------------------
st.set_page_config(page_title="Mapa de calor - Provedores", layout="wide")

require_login()

# Logo na sidebar (sem use_container_width pra não quebrar)
if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), width=180)

st.sidebar.title("Mapa de calor")
st.sidebar.caption(f'Logado como: {st.session_state.auth.get("user")}')
logout_button()

st.title("Mapa de calor de clientes/provedores")

# Upload opcional
up = st.file_uploader(
    "Envie a planilha (.xls/.xlsx) ou deixe em branco para usar o arquivo padrão",
    type=["xls", "xlsx", "xlsm"],
)

if up is not None:
    is_xlsx = up.name.lower().endswith(("xlsx", "xlsm"))
    tmp_path = Path("uploaded_planilha.xlsx" if is_xlsx else "uploaded_planilha.xls")
    tmp_path.write_bytes(up.getbuffer())
    planilha_path = str(tmp_path)
else:
    planilha_path = config.DEFAULT_SPREADSHEET_PATH

# Ler planilha
try:
    df = read_spreadsheet(planilha_path)
except Exception as e:
    st.error(f"Não consegui ler a planilha: {e}")
    st.stop()

# Normaliza nomes das colunas (resolve VALOR\nMENSAL etc.)
df.columns = [_norm_col(c) for c in df.columns]

st.caption(f"Planilha carregada: `{planilha_path}` | Linhas: {len(df)}")


# -----------------------------
# Filtros (cliente)
# -----------------------------
df_f = df.copy()
st.sidebar.subheader("Filtros (cliente)")

if col_exists(df, config.COL_VENDEDOR):
    vend_opts = sorted(df[config.COL_VENDEDOR].dropna().unique())
    vendedor = st.sidebar.multiselect("VENDEDOR", vend_opts)
    if vendedor:
        df_f = df_f[df_f[config.COL_VENDEDOR].isin(vendedor)]

if col_exists(df, config.COL_UF_CLIENTE):
    uf_opts = sorted(df[config.COL_UF_CLIENTE].dropna().unique())
    uf_cli = st.sidebar.multiselect("UF (cadastro)", uf_opts)
    if uf_cli:
        df_f = df_f[df_f[config.COL_UF_CLIENTE].isin(uf_cli)]


# -----------------------------
# Explode cidades
# -----------------------------
if not col_exists(df, config.COL_CIDADES_ATENDIDAS):
    st.error(f"Coluna `{config.COL_CIDADES_ATENDIDAS}` não encontrada.")
    st.stop()

df_exp = explode_cidades(df_f, col=config.COL_CIDADES_ATENDIDAS)


# -----------------------------
# Filtros (atendimento)
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("Filtros (atendimento)")

ufs_atend = sorted(df_exp["UF_ATENDIDA"].dropna().unique())
cids_atend = sorted(df_exp["CIDADE_ATENDIDA"].dropna().unique())

uf_atendida = st.sidebar.multiselect("UF atendida", ufs_atend)
cidade_atendida = st.sidebar.multiselect("Cidade atendida", cids_atend)

df_exp_f = df_exp.copy()
if uf_atendida:
    df_exp_f = df_exp_f[df_exp_f["UF_ATENDIDA"].isin(uf_atendida)]
if cidade_atendida:
    df_exp_f = df_exp_f[df_exp_f["CIDADE_ATENDIDA"].isin(cidade_atendida)]


# -----------------------------
# Coordenadas
# -----------------------------
if Path(config.CIDADES_CSV).exists():
    coords_df = load_city_coords_csv(config.CIDADES_CSV)
else:
    coords_df = load_cache(config.CIDADES_CACHE_CSV)

# Geocoding opcional
st.sidebar.markdown("---")
st.sidebar.subheader("Geocoding (opcional)")

allow_geocode = st.sidebar.checkbox(
    "Geocodificar cidades faltantes (precisa internet)",
    value=False,
)

if allow_geocode:
    unique = (
        df_exp_f[["cidade_norm", "uf_norm", "CIDADE_ATENDIDA", "UF_ATENDIDA"]]
        .drop_duplicates()
    )
    coords_df = geocode_missing(unique, coords_df)
    save_cache(config.CIDADES_CACHE_CSV, coords_df)
    st.sidebar.success("Cache atualizado")

# Merge coordenadas
df_geo = df_exp_f.merge(coords_df, on=["cidade_norm", "uf_norm"], how="left")

faltando = int(df_geo["lat"].isna().sum())
st.write(f"Registros: **{len(df_geo)}** | Sem coordenada: **{faltando}**")

if faltando > 0:
    st.subheader("Cidades sem coordenada")
    sem_coord = (
        df_geo[df_geo["lat"].isna()][["CIDADE_ATENDIDA", "UF_ATENDIDA"]]
        .drop_duplicates()
    )
    st.dataframe(sem_coord, use_container_width=True)


# -----------------------------
# Ranking / Gráficos
# -----------------------------
st.markdown("### Rankings e gráficos")

rank_base = df_geo.dropna(subset=["CIDADE_ATENDIDA", "UF_ATENDIDA"]).copy()

st.markdown("#### Top 10 cidades atendidas (por quantidade)")
top10_cidades = (
    rank_base.groupby(["UF_ATENDIDA", "CIDADE_ATENDIDA"], as_index=False)
    .size()
    .sort_values("size", ascending=False)
    .head(10)
    .rename(columns={"size": "QTDE"})
)
st.dataframe(top10_cidades[["UF_ATENDIDA", "CIDADE_ATENDIDA", "QTDE"]], use_container_width=True)

st.markdown("#### Atendimentos por UF (quantidade)")
por_uf = (
    rank_base.groupby("UF_ATENDIDA", as_index=False)
    .size()
    .sort_values("size", ascending=False)
    .rename(columns={"size": "QTDE"})
)
st.bar_chart(por_uf.set_index("UF_ATENDIDA")["QTDE"])

st.markdown("#### Atendimentos por Região (quantidade)")
UF_PARA_REGIAO = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste",
    "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}
rank_base["REGIAO"] = rank_base["UF_ATENDIDA"].map(UF_PARA_REGIAO).fillna("Desconhecida")
por_regiao = (
    rank_base.groupby("REGIAO", as_index=False)
    .size()
    .sort_values("size", ascending=False)
    .rename(columns={"size": "QTDE"})
)
st.bar_chart(por_regiao.set_index("REGIAO")["QTDE"])


# -----------------------------
# MAPA
# -----------------------------
st.markdown("### Mapa")

df_map = df_geo.dropna(subset=["lat", "lon"]).copy()
zoom = st.sidebar.slider("Zoom inicial", 3, 12, 4)

st.sidebar.markdown("---")
st.sidebar.subheader("Pontos")
MOSTRAR_PONTOS = st.sidebar.checkbox("Mostrar pontos clicáveis", True)

# sempre mostrar todas
LIMITE_PONTOS = len(df_map)

m = folium.Map(location=[-14.2, -51.9], zoom_start=zoom, tiles="OpenStreetMap", control_scale=True)
folium.TileLayer("CartoDB positron", show=False).add_to(m)

folium.map.CustomPane("heatmap", z_index=200).add_to(m)
folium.map.CustomPane("markers", z_index=650).add_to(m)

pontos_heat = df_map[["lat", "lon", "PESO"]].values.tolist()
st.caption(f"Pontos no heatmap: {len(pontos_heat)}")

if pontos_heat:
    HeatMap(pontos_heat, radius=18, blur=22, min_opacity=0.35, pane="heatmap").add_to(m)

if MOSTRAR_PONTOS and not df_map.empty:
    df_tt = df_map.head(LIMITE_PONTOS).copy()
    layer = folium.FeatureGroup("Pontos (por cidade)")

    grupos = df_tt.groupby(["lat", "lon"])

    for (lat, lon), g in grupos:
        itens = []
        for _, row in g.iterrows():
            cliente = _safe(row.get("NOME FANTASIA", ""))
            uf = _safe(row.get("UF", ""))
            cidade = _safe(row.get("CIDADE", ""))

            valor = _format_money(row.get("VALOR MENSAL", ""))
            vendedor = _safe(row.get("VENDEDOR", ""))
            assinatura_raw = row.get("ASSINATURA CONTRATO", "")
            assinatura = _format_date(assinatura_raw)
            tempo_contrato = _format_tempo_contrato(assinatura_raw)
            cidades_atend = _safe(row.get("CIDADES_ATENDIDAS", ""))

            itens.append(
                f"""
                <div style="padding:6px 0;border-bottom:1px solid #eee;">
                  <b>{cliente}</b><br>
                  <span>UF/Cidade: {uf} / {cidade}</span><br>
                  <span>Valor mensal: {valor}</span><br>
                  <span>Vendedor: {vendedor}</span><br>
                  <span>Assinatura: {assinatura}</span><br>
                  <span>Tempo de contrato: {tempo_contrato}</span><br>
                  <span>Cidades atendidas: {cidades_atend}</span>
                </div>
                """
            )

        html = f"""
        <div style="width:360px;max-height:260px;overflow:auto;font-size:13px;line-height:1.35;">
          <div style="margin-bottom:8px;"><b>Provedores neste ponto:</b> {len(g)}</div>
          {''.join(itens)}
        </div>
        """

        n = len(g)
        radius = 2 + min(10, n)

        folium.CircleMarker(
            location=[lat, lon],
            radius=radius,
            color="#1f77b4",
            fill=True,
            fill_opacity=0.85,
            popup=folium.Popup(html, max_width=420),
            pane="markers",
        ).add_to(layer)

    layer.add_to(m)

if not df_map.empty:
    m.fit_bounds(df_map[["lat", "lon"]].values.tolist())

folium.LayerControl().add_to(m)

html_path = "mapa.html"
m.save(html_path)

with open(html_path, "r", encoding="utf-8") as f:
    components.html(f.read(), height=650, scrolling=True)
