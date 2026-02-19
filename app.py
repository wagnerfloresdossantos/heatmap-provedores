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
        val = float(str(v).replace(".", "").replace(",", "."))
        return f"{val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return str(v)


def _format_date(v) -> str:
    """Formata data para dd/mm/aaaa"""
    if pd.isna(v) or v == "":
        return ""
    try:
        d = pd.to_datetime(v, errors="coerce", dayfirst=True)
        if pd.isna(d):
            return ""
        return d.strftime("%d/%m/%Y")
    except Exception:
        return str(v)


def _format_tempo_contrato(dt_value) -> str:
    """Retorna tempo desde a assinatura (ex: 1a 3m, 2m 12d)."""
    if pd.isna(dt_value) or dt_value == "":
        return ""
    try:
        dt = pd.to_datetime(dt_value, errors="coerce", dayfirst=True)
        if pd.isna(dt):
            return ""

        today = pd.Timestamp.today().normalize()
        dt = pd.Timestamp(dt).normalize()

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
# Cache (evita recarregar a planilha a cada rerun)
# -----------------------------
@st.cache_data(show_spinner=False)
def _load_df_from_uploaded(uploaded_file) -> pd.DataFrame:
    df = read_spreadsheet(uploaded_file)
    df.columns = [_norm_col(c) for c in df.columns]
    if col_exists(df, "ASSINATURA CONTRATO"):
        df["ASSINATURA_DT"] = pd.to_datetime(
            df["ASSINATURA CONTRATO"], errors="coerce", dayfirst=True
        )
    else:
        df["ASSINATURA_DT"] = pd.NaT
    return df


@st.cache_data(show_spinner=False)
def _load_df_from_path(path: str) -> pd.DataFrame:
    df = read_spreadsheet(path)
    df.columns = [_norm_col(c) for c in df.columns]
    if col_exists(df, "ASSINATURA CONTRATO"):
        df["ASSINATURA_DT"] = pd.to_datetime(
            df["ASSINATURA CONTRATO"], errors="coerce", dayfirst=True
        )
    else:
        df["ASSINATURA_DT"] = pd.NaT
    return df


# -----------------------------
# App
# -----------------------------
st.set_page_config(page_title="Mapa de calor - Provedores", layout="wide")
#require_login()

# Logo na sidebar
if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), width=180)

st.sidebar.title("Mapa de calor")
st.sidebar.caption(f'Logado como: {st.session_state.auth.get("user")}')
logout_button()

st.title("Mapa de calor de clientes/provedores")

# Upload (recomendado)
up = st.file_uploader(
    "Envie a planilha (.xls/.xlsx) — recomendado para uso na nuvem",
    type=["xls", "xlsx", "xlsm"],
)

# ✅ NÃO salva no disco com nome fixo (evita conflito Cloud)
if up is not None:
    try:
        df = _load_df_from_uploaded(up)
        st.caption(f"Planilha carregada via upload: **{up.name}** | Linhas: {len(df)}")
    except Exception as e:
        st.error(f"Não consegui ler a planilha enviada: {e}")
        st.stop()
else:
    # fallback local (se existir)
    planilha_path = config.DEFAULT_SPREADSHEET_PATH
    try:
        df = _load_df_from_path(planilha_path)
        st.caption(f"Planilha carregada: `{planilha_path}` | Linhas: {len(df)}")
    except Exception as e:
        st.warning("Envie uma planilha para continuar (modo nuvem).")
        st.caption(f"Detalhe do erro ao tentar usar arquivo padrão: {e}")
        st.stop()


# -----------------------------
# Filtros (cliente)
# -----------------------------
df_f = df.copy()

st.sidebar.subheader("Filtros (cliente)")

# Filtro por nome
if col_exists(df_f, "NOME FANTASIA"):
    st.sidebar.markdown("---")
    st.sidebar.subheader("Buscar Cliente")
    busca_nome = st.sidebar.text_input(
        "Nome do cliente", placeholder="Digite parte do nome..."
    )
    if busca_nome:
        df_f = df_f[
            df_f["NOME FANTASIA"]
            .astype(str)
            .str.contains(busca_nome, case=False, na=False)
        ]

# Filtro por período (com proteção RangeError)
st.sidebar.markdown("---")
st.sidebar.subheader("Período de Ativação")

datas = df_f["ASSINATURA_DT"].dropna()

if datas.empty:
    st.sidebar.caption("Sem datas válidas na coluna ASSINATURA CONTRATO.")
else:
    data_min = datas.min().date()
    data_max = datas.max().date()

    if data_min >= data_max:
        st.sidebar.caption(f"Data única no filtro: {data_min.strftime('%d/%m/%Y')}")
        data_ini, data_fim = data_min, data_max
    else:
        data_ini, data_fim = st.sidebar.slider(
            "Selecione o período",
            min_value=data_min,
            max_value=data_max,
            value=(data_min, data_max),
            format="DD/MM/YYYY",
        )

    df_f = df_f[df_f["ASSINATURA_DT"].notna()].copy()
    df_f = df_f[
        (df_f["ASSINATURA_DT"].dt.date >= data_ini)
        & (df_f["ASSINATURA_DT"].dt.date <= data_fim)
    ]

# Outros filtros
if col_exists(df_f, config.COL_VENDEDOR):
    vend_opts = sorted(df_f[config.COL_VENDEDOR].dropna().unique())
    vendedor = st.sidebar.multiselect("VENDEDOR", vend_opts)
    if vendedor:
        df_f = df_f[df_f[config.COL_VENDEDOR].isin(vendedor)]

if col_exists(df_f, config.COL_UF_CLIENTE):
    uf_opts = sorted(df_f[config.COL_UF_CLIENTE].dropna().unique())
    uf_cli = st.sidebar.multiselect("UF (cadastro)", uf_opts)
    if uf_cli:
        df_f = df_f[df_f[config.COL_UF_CLIENTE].isin(uf_cli)]


# -----------------------------
# Opção: bolinha por cidade base ou cidades atendidas
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("Tipo de ponto (bolinhas)")

op_ponto = st.sidebar.radio(
    "Mostrar bolinhas por:",
    options=["Cidades atendidas", "Cidade base (cadastro)"],
    index=0,
)

# -----------------------------
# Explode / Preparação para Geo
# -----------------------------
if op_ponto == "Cidades atendidas":
    if not col_exists(df_f, config.COL_CIDADES_ATENDIDAS):
        st.error(f"Coluna `{config.COL_CIDADES_ATENDIDAS}` não encontrada.")
        st.stop()

    df_exp = explode_cidades(df_f, col=config.COL_CIDADES_ATENDIDAS)

    # Filtros (atendimento)
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

    df_para_geo = df_exp_f.copy()

else:
    if not (col_exists(df_f, "CIDADE") and col_exists(df_f, "UF")):
        st.error("Para usar 'Cidade base (cadastro)', preciso das colunas `CIDADE` e `UF`.")
        st.stop()

    df_para_geo = df_f.copy()
    df_para_geo["CIDADE_ATENDIDA"] = df_para_geo["CIDADE"]
    df_para_geo["UF_ATENDIDA"] = df_para_geo["UF"]
    df_para_geo["cidade_norm"] = df_para_geo["CIDADE_ATENDIDA"].astype(str).str.strip().str.lower()
    df_para_geo["uf_norm"] = df_para_geo["UF_ATENDIDA"].astype(str).str.strip().str.upper()

    st.sidebar.markdown("---")
    st.sidebar.caption("Filtro por UF/Cidade atendida não se aplica ao modo 'Cidade base'.")


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

allow_geocode = st.sidebar.checkbox("Geocodificar cidades faltantes (precisa internet)", value=False)

if allow_geocode:
    unique = (
        df_para_geo[["cidade_norm", "uf_norm", "CIDADE_ATENDIDA", "UF_ATENDIDA"]]
        .drop_duplicates()
    )
    coords_df = geocode_missing(unique, coords_df)
    save_cache(config.CIDADES_CACHE_CSV, coords_df)
    st.sidebar.success("Cache atualizado")

df_geo = df_para_geo.merge(coords_df, on=["cidade_norm", "uf_norm"], how="left")

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

# Por UF
st.markdown("#### Atendimentos por UF (quantidade)")
por_uf = (
    rank_base.groupby("UF_ATENDIDA", as_index=False)
    .size()
    .sort_values("size", ascending=False)
    .rename(columns={"size": "QTDE"})
)
st.bar_chart(por_uf.set_index("UF_ATENDIDA")["QTDE"])

# Por Região
st.markdown("#### Atendimentos por Região (quantidade)")
UF_PARA_REGIAO = {
    "AC": "Norte", "AP": "Norte", "AM": "Norte", "PA": "Norte",
    "RO": "Norte", "RR": "Norte", "TO": "Norte",
    "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste",
    "PB": "Nordeste", "PE": "Nordeste", "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste",
    "DF": "Centro-Oeste", "GO": "Centro-Oeste", "MT": "Centro-Oeste", "MS": "Centro-Oeste",
    "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
    "PR": "Sul", "RS": "Sul", "SC": "Sul",
}

rank_base["REGIAO"] = (
    rank_base["UF_ATENDIDA"].astype(str).str.upper().map(UF_PARA_REGIAO).fillna("Desconhecida")
)

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

# ✅ proteção para não travar no Cloud (você pode ajustar)
MAX_MARKERS = st.sidebar.slider("Limite de bolinhas", 200, 5000, 1500, 100)

m = folium.Map(
    location=[-14.2, -51.9],
    zoom_start=zoom,
    tiles="OpenStreetMap",
    control_scale=True,
)

folium.TileLayer("CartoDB positron", show=False).add_to(m)

folium.map.CustomPane("heatmap", z_index=200).add_to(m)
folium.map.CustomPane("markers", z_index=650).add_to(m)

# Heatmap (amostragem de segurança)
MAX_HEAT = 10000
df_heat = df_map
if len(df_heat) > MAX_HEAT:
    df_heat = df_heat.sample(MAX_HEAT, random_state=42)

if "PESO" in df_heat.columns:
    pontos_heat = df_heat[["lat", "lon", "PESO"]].values.tolist()
else:
    pontos_heat = df_heat[["lat", "lon"]].assign(PESO=1)[["lat", "lon", "PESO"]].values.tolist()

st.caption(f"Pontos no heatmap: {len(pontos_heat)}")

if pontos_heat:
    HeatMap(
        pontos_heat,
        radius=18,
        blur=22,
        min_opacity=0.35,
        pane="heatmap",
    ).add_to(m)

# Marcadores
if MOSTRAR_PONTOS and not df_map.empty:
    df_tt = df_map.head(MAX_MARKERS).copy()
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

            cidades_atend = _safe(row.get("CIDADES ATENDIDAS", row.get("CIDADES_ATENDIDAS", "")))

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

# Render
html_path = "mapa.html"
m.save(html_path)

with open(html_path, "r", encoding="utf-8") as f:
    components.html(f.read(), height=650, scrolling=True)
