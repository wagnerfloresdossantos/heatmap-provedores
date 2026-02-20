import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from pathlib import Path
import streamlit.components.v1 as components
import unicodedata


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


def _norm_text_basic(s: str) -> str:
    """Normaliza texto (remove acentos, lowercase, trim, espaços)."""
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = " ".join(s.split())
    return s


def _norm_uf(uf: str) -> str:
    uf = _norm_text_basic(uf).upper()
    return uf[:2] if uf else ""


# -----------------------------
# App
# -----------------------------
st.set_page_config(page_title="Mapa de calor - Provedores", layout="wide")

# Sidebar header
if LOGO_PATH.exists():
    st.sidebar.image(str(LOGO_PATH), width=180)

st.sidebar.title("Mapa de calor")

st.title("Mapa de calor de clientes/provedores")


from io import BytesIO

# Upload (Cloud-friendly)
up = st.file_uploader(
    "Envie a planilha (.xls/.xlsx) (no Streamlit Cloud isso é obrigatório)",
    type=["xls", "xlsx", "xlsm"],
)

if up is None:
    # tenta usar padrão local (funciona localmente, mas no Cloud geralmente não existe)
    if getattr(config, "DEFAULT_SPREADSHEET_PATH", None) and Path(config.DEFAULT_SPREADSHEET_PATH).exists():
        df = read_spreadsheet(config.DEFAULT_SPREADSHEET_PATH)
        st.caption(f"Planilha carregada: `{config.DEFAULT_SPREADSHEET_PATH}` | Linhas: {len(df)}")
    else:
        st.info("Envie uma planilha para começar (no Cloud não existe arquivo padrão local).")
        st.stop()
else:
    # ✅ NÃO salva no disco: evita conflito entre usuários/sessões no Cloud
    data = BytesIO(up.getvalue())
    df = read_spreadsheet(data)
    st.caption(f"Planilha carregada: `{up.name}` | Linhas: {len(df)}")


# Normaliza nomes das colunas (resolve VALOR\nMENSAL etc.)
df.columns = [_norm_col(c) for c in df.columns]

# Coluna datetime para filtro (ASSINATURA CONTRATO)
if col_exists(df, "ASSINATURA CONTRATO"):
    df["ASSINATURA_DT"] = pd.to_datetime(df["ASSINATURA CONTRATO"], errors="coerce", dayfirst=True)
else:
    df["ASSINATURA_DT"] = pd.NaT

#st.caption(f"Planilha carregada: `{planilha_path}` | Linhas: {len(df)}")

# -----------------------------
# Filtros (cliente)
# -----------------------------
st.sidebar.subheader("Filtros (cliente)")

df_f = df.copy()

# Filtro por nome do cliente (contém)
st.sidebar.markdown("---")
st.sidebar.subheader("Buscar Cliente")
busca_nome = st.sidebar.text_input("Nome do cliente", placeholder="Digite parte do nome...")

if busca_nome and col_exists(df_f, "NOME FANTASIA"):
    df_f = df_f[
        df_f["NOME FANTASIA"]
        .astype(str)
        .str.contains(busca_nome, case=False, na=False)
    ]

# Filtro por período (slider) - sem RangeError quando min==max
st.sidebar.markdown("---")
st.sidebar.subheader("Período de Ativação (Assinatura)")

datas_validas = df_f["ASSINATURA_DT"].dropna() if col_exists(df_f, "ASSINATURA_DT") else pd.Series([], dtype="datetime64[ns]")

data_inicio, data_fim = None, None
if not datas_validas.empty:
    dmin = datas_validas.min().date()
    dmax = datas_validas.max().date()

    if dmin == dmax:
        st.sidebar.caption(f"Apenas 1 data no filtro atual: **{dmin.strftime('%d/%m/%Y')}**")
        data_inicio, data_fim = dmin, dmax
    else:
        data_inicio, data_fim = st.sidebar.slider(
            "Selecione o período",
            min_value=dmin,
            max_value=dmax,
            value=(dmin, dmax),
            format="DD/MM/YYYY",
        )

    # aplica filtro
    df_f = df_f[df_f["ASSINATURA_DT"].notna()].copy()
    df_f = df_f[
        (df_f["ASSINATURA_DT"].dt.date >= data_inicio) &
        (df_f["ASSINATURA_DT"].dt.date <= data_fim)
    ]
else:
    st.sidebar.caption("Sem datas válidas para filtrar (ASSINATURA CONTRATO).")

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
# Como mostrar as bolinhas
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("Bolinhas (pontos clicáveis)")

modo_bolinhas = st.sidebar.radio(
    "Mostrar bolinhas por:",
    ["Cidades atendidas", "Cidade base do cliente", "Ambos"],
    index=0,
)

MOSTRAR_PONTOS = st.sidebar.checkbox("Mostrar pontos clicáveis", True)
SEMPRE_TODAS = st.sidebar.checkbox("Sempre mostrar todas", True)

# -----------------------------
# Coordenadas (cache)
# -----------------------------
if Path(config.CIDADES_CSV).exists():
    coords_df = load_city_coords_csv(config.CIDADES_CSV)
else:
    coords_df = load_cache(config.CIDADES_CACHE_CSV)

# Geocoding opcional
st.sidebar.markdown("---")
st.sidebar.subheader("Geocoding (opcional)")
allow_geocode = st.sidebar.checkbox("Geocodificar cidades faltantes (precisa internet)", value=False)

# -----------------------------
# Montar dataset de mapa (heatmap + bolinhas)
# -----------------------------
# A) Cidades atendidas (explode)
df_att = None
if modo_bolinhas in ("Cidades atendidas", "Ambos"):
    if not col_exists(df_f, config.COL_CIDADES_ATENDIDAS):
        st.error(f"Coluna `{config.COL_CIDADES_ATENDIDAS}` não encontrada.")
        st.stop()

    df_exp = explode_cidades(df_f, col=config.COL_CIDADES_ATENDIDAS)

    # filtros (atendimento)
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

    # geocode opcional (atendidas)
    if allow_geocode:
        unique = df_exp_f[["cidade_norm", "uf_norm", "CIDADE_ATENDIDA", "UF_ATENDIDA"]].drop_duplicates()
        coords_df = geocode_missing(unique, coords_df)
        save_cache(config.CIDADES_CACHE_CSV, coords_df)
        st.sidebar.success("Cache atualizado")

    df_att = df_exp_f.merge(coords_df, on=["cidade_norm", "uf_norm"], how="left")
    if "PESO" not in df_att.columns:
        df_att["PESO"] = 1

# B) Cidade base do cliente (CIDADE/UF do cadastro)
df_base = None
if modo_bolinhas in ("Cidade base do cliente", "Ambos"):
    df_base = df_f.copy()

    # tenta pegar colunas padrão
    col_uf = config.COL_UF_CLIENTE if col_exists(df_base, config.COL_UF_CLIENTE) else "UF"
    col_cidade = "CIDADE" if col_exists(df_base, "CIDADE") else None

    if not col_cidade or not col_exists(df_base, col_uf):
        st.warning("Não encontrei colunas de cidade/UF do cliente (CIDADE e UF). Vou ignorar 'Cidade base'.")
        df_base = None
    else:
        df_base["uf_norm"] = df_base[col_uf].apply(_norm_uf)
        df_base["cidade_norm"] = df_base[col_cidade].apply(_norm_text_basic)

        # geocode opcional (base)
        if allow_geocode:
            unique = df_base[["cidade_norm", "uf_norm"]].drop_duplicates().copy()
            unique["CIDADE_ATENDIDA"] = unique["cidade_norm"]
            unique["UF_ATENDIDA"] = unique["uf_norm"]
            coords_df = geocode_missing(unique, coords_df)
            save_cache(config.CIDADES_CACHE_CSV, coords_df)
            st.sidebar.success("Cache atualizado")

        df_base = df_base.merge(coords_df, on=["cidade_norm", "uf_norm"], how="left")
        df_base["PESO"] = 1

# Combina para mapa/heat
dfs = [d for d in [df_att, df_base] if d is not None]
if not dfs:
    st.info("Nenhum dado para exibir com os filtros atuais.")
    st.stop()

df_geo = pd.concat(dfs, ignore_index=True)

faltando = int(df_geo["lat"].isna().sum())
st.write(f"Registros: **{len(df_geo)}** | Sem coordenada: **{faltando}**")

if faltando > 0:
    st.subheader("Cidades sem coordenada")
    sem_coord_cols = []
    if "CIDADE_ATENDIDA" in df_geo.columns and "UF_ATENDIDA" in df_geo.columns:
        sem_coord_cols = ["CIDADE_ATENDIDA", "UF_ATENDIDA"]
    elif "CIDADE" in df_geo.columns and "UF" in df_geo.columns:
        sem_coord_cols = ["CIDADE", "UF"]

    if sem_coord_cols:
        sem_coord = df_geo[df_geo["lat"].isna()][sem_coord_cols].drop_duplicates()
        st.dataframe(sem_coord, use_container_width=True)

# -----------------------------
# Ranking / Gráficos (mantém por atendidas se existir, senão base)
# -----------------------------
st.markdown("### Rankings e gráficos")

rank_source = df_att if df_att is not None else df_base
rank_base = rank_source.dropna(subset=["lat", "lon"]).copy()

# se tiver UF_ATENDIDA usa isso, senão usa UF do cadastro
uf_rank_col = "UF_ATENDIDA" if "UF_ATENDIDA" in rank_base.columns else ("UF" if "UF" in rank_base.columns else None)

# Top 10 cidades (se atendida, usa CIDADE_ATENDIDA; senão CIDADE)
st.markdown("#### Top 10 cidades (por quantidade)")
cidade_rank_col = "CIDADE_ATENDIDA" if "CIDADE_ATENDIDA" in rank_base.columns else ("CIDADE" if "CIDADE" in rank_base.columns else None)

if uf_rank_col and cidade_rank_col:
    top10_cidades = (
        rank_base.groupby([uf_rank_col, cidade_rank_col], as_index=False)
        .size()
        .sort_values("size", ascending=False)
        .head(10)
        .rename(columns={"size": "QTDE", uf_rank_col: "UF", cidade_rank_col: "CIDADE"})
    )
    st.dataframe(top10_cidades[["UF", "CIDADE", "QTDE"]], use_container_width=True)
else:
    st.caption("Sem colunas suficientes para Top 10 cidades.")

# Gráfico por UF
st.markdown("#### Atendimentos por UF (quantidade)")
if uf_rank_col:
    por_uf = (
        rank_base.groupby(uf_rank_col, as_index=False)
        .size()
        .sort_values("size", ascending=False)
        .rename(columns={"size": "QTDE", uf_rank_col: "UF"})
    )
    st.bar_chart(por_uf.set_index("UF")["QTDE"])
else:
    st.caption("Sem coluna UF para gráfico.")

# Gráfico por Região
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

if uf_rank_col:
    tmp = rank_base.copy()
    tmp["REGIAO"] = tmp[uf_rank_col].astype(str).str.upper().map(UF_PARA_REGIAO).fillna("Desconhecida")
    por_regiao = (
        tmp.groupby("REGIAO", as_index=False)
        .size()
        .sort_values("size", ascending=False)
        .rename(columns={"size": "QTDE"})
    )
    st.bar_chart(por_regiao.set_index("REGIAO")["QTDE"])
else:
    st.caption("Sem coluna UF para região.")

# -----------------------------
# MAPA
# -----------------------------
st.markdown("### Mapa")

df_map = df_geo.dropna(subset=["lat", "lon"]).copy()

zoom = st.sidebar.slider("Zoom inicial", 3, 12, 4)

# limite opcional (performance)
if not SEMPRE_TODAS:
    LIMITE_PONTOS = st.sidebar.slider("Limite de bolinhas", 100, 5000, 800, 100)
else:
    LIMITE_PONTOS = len(df_map)

m = folium.Map(
    location=[-14.2, -51.9],
    zoom_start=zoom,
    tiles="OpenStreetMap",
    control_scale=True,
)

folium.TileLayer("CartoDB positron", show=False).add_to(m)

# Panes
folium.map.CustomPane("heatmap", z_index=200).add_to(m)
folium.map.CustomPane("markers", z_index=650).add_to(m)

# Heatmap
pontos_heat = df_map[["lat", "lon", "PESO"]].values.tolist()
st.caption(f"Pontos no heatmap: {len(pontos_heat)}")

if pontos_heat:
    HeatMap(
        pontos_heat,
        radius=18,
        blur=22,
        min_opacity=0.35,
        pane="heatmap",
    ).add_to(m)

# Bolinhas com popup
if MOSTRAR_PONTOS and not df_map.empty:

    df_tt = df_map.head(LIMITE_PONTOS).copy()
    layer = folium.FeatureGroup("Pontos")

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
                  <span><b>Valor mensal:</b> {valor}</span><br>
                  <span>Vendedor: {vendedor}</span><br>
                  <span><b>Assinatura:</b> {assinatura}</span><br>
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

# Enquadrar
if not df_map.empty:
    m.fit_bounds(df_map[["lat", "lon"]].values.tolist())

folium.LayerControl().add_to(m)

# Render
html_path = "mapa.html"
m.save(html_path)

with open(html_path, "r", encoding="utf-8") as f:
    components.html(f.read(), height=650, scrolling=True)
