# Heatmap de Provedores (Streamlit + Folium)

App em **Streamlit** para análise geográfica de provedores/clientes, com
mapas interativos, rankings e filtros avançados.

Desenvolvido por: **Wagner Flores dos Santos**

------------------------------------------------------------------------

## ✅ Funcionalidades

-   Upload de planilhas Excel (.xls, .xlsx, .xlsm)
-   Visualização em mapa com Heatmap e pontos clicáveis
-   Filtros por:
    -   Nome fantasia
    -   Vendedor
    -   UF
    -   Cidade atendida
    -   Período de contrato
-   Ranking por cidade, estado e região
-   Suporte a múltiplas cidades atendidas por cliente
-   Cache de coordenadas
-   Autenticação opcional

------------------------------------------------------------------------

## 📄 Estrutura da Planilha

### Coluna obrigatória

CIDADES_ATENDIDAS

Formato:

Cuiabá/MT; Várzea Grande/MT\
Cuiabá/MT\|5; Rondonópolis/MT\|2

### Colunas recomendadas

-   NOME FANTASIA
-   ASSINATURA CONTRATO
-   VENDEDOR
-   UF
-   CIDADE
-   VALOR MENSAL

------------------------------------------------------------------------

## 🌍 Coordenadas

Utilize o arquivo cidades.csv:

cidade,uf,lat,lon\
Cuiabá,MT,-15.601,-56.097

Arquivo exemplo disponível: cidades.csv.example

------------------------------------------------------------------------

## ▶️ Execução Local

### Criar ambiente virtual

python3 -m venv venv\
source venv/bin/activate

### Instalar dependências

pip install -r requirements.txt

### Executar

streamlit run app.py

------------------------------------------------------------------------

## 🐳 Execução com Docker

docker compose up -d --build

Acesse: http://localhost:8501

------------------------------------------------------------------------

## ☁️ Streamlit Cloud

O sistema aceita upload direto via interface.

Recomenda-se subir também o arquivo cidades.csv.

------------------------------------------------------------------------

## 🔐 Autenticação

Opcional via auth.py

Criar usuário:

python tools/create_user.py

------------------------------------------------------------------------

## 📁 Estrutura

-   app.py → Interface principal
-   geo.py → Geolocalização
-   data_loader.py → Leitura dos dados
-   auth.py → Autenticação
-   config.py → Configurações
-   assets/ → Imagens

------------------------------------------------------------------------

## 👨‍💻 Desenvolvedor

Wagner Flores dos Santos\
Engenharia de Telecomunicações / Consultor em Tecnologia

------------------------------------------------------------------------

## 📜 Licença

Uso livre para fins educacionais e comerciais, mediante citação do
autor.
