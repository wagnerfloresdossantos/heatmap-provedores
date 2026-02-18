python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py



# Heatmap de Provedores (local -> remoto)

App em **Streamlit** que lê uma planilha `.xls/.xlsx` de clientes/provedores e desenha um **mapa de calor** em cima de um mapa estilo Google Maps (OpenStreetMap/Leaflet via Folium).

✅ Suporta:  
- 1 cliente atendendo **várias cidades** via coluna `CIDADES_ATENDIDAS`  
- `Cidade/UF` e **peso opcional** `Cidade/UF|peso` (se não informar, peso=1)  
- filtros por STATUS/VENDEDOR/UF do cliente **e** por UF/Cidade atendida  
- Top 10 cidades atendidas (por quantidade e por soma de peso)  
- autenticação por **login e senha** (pronto para usar local e manter no remoto)

---

## 1) Estrutura esperada na planilha

Crie/alimente a coluna:

- `CIDADES_ATENDIDAS` com o formato:  
  - `Cuiabá/MT; Várzea Grande/MT; Rondonópolis/MT`  
  - ou com peso: `Cuiabá/MT|5; Várzea Grande/MT|3; Rondonópolis/MT|1`

O app tenta usar as colunas `STATUS`, `VENDEDOR`, `UF`, `CIDADE` se existirem (para filtros). Se sua planilha tiver nomes diferentes, você consegue ajustar no arquivo `config.py`.

---

## 2) Rodar local (sem Docker)

### Requisitos
- Python 3.10+

### Instalar dependências
```bash
pip install -r requirements.txt
```

### Criar usuário/senha (gera hash bcrypt)
```bash
python tools/create_user.py
```
Ele vai pedir usuário e senha e vai salvar em `users.json`.

### Rodar
```bash
streamlit run app.py
```

---

## 3) Coordenadas das cidades (como funciona)

O app usa uma destas opções, nesta ordem:

1. `cidades.csv` (recomendado) com colunas: `cidade,uf,lat,lon`
2. Se não existir `cidades.csv`, ele pode **geocodificar** automaticamente (precisa internet) usando Nominatim (OpenStreetMap), salva cache em `cidades_cache.csv` e reutiliza depois.

> Em produção/remoto, o ideal é manter `cidades.csv` (ou o cache pronto) para evitar dependência de geocoding.

---

## 4) Preparado para acesso remoto

Você pode subir em um VPS usando Docker (ver `Dockerfile` e `docker-compose.yml`) e colocar um proxy (Nginx/Caddy) na frente com HTTPS.

Autenticação:
- A autenticação por login/senha já está no app (`users.json` com hash).  
- Para produção, você também pode somar autenticação no proxy (Basic Auth/SSO), se quiser “dupla camada”.

---

## 5) Arquivos principais

- `app.py` -> app Streamlit (UI + mapa)
- `auth.py` -> login/sessão
- `geo.py` -> explode cidades + lat/lon (csv ou geocode)
- `config.py` -> mapeamento de colunas
- `tools/create_user.py` -> cria/atualiza `users.json`

---

## Dicas rápidas
- Padronize sempre `Cidade/UF` e separe cidades com `;`
- UF com 2 letras
- Evite acentos inconsistentes (o app normaliza, mas padronizar ajuda)
