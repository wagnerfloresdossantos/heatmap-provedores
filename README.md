python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py


# 📍 Mapa de Calor de Provedores – OléTV

Sistema web desenvolvido em Python para visualização geográfica dos provedores/clientes atendidos pela OléTV, com mapa interativo, filtros, gráficos e controle de acesso.

---

## 👨‍💻 Autor

**Wagner Flores dos Santos**  
Projeto desenvolvido para uso interno e apoio à gestão comercial da OléTV.

---

## 🎯 Objetivo do Projeto

Este sistema permite:

- Visualizar provedores por cidade no mapa
- Identificar concentração regional (heatmap)
- Consultar dados completos ao clicar no ponto
- Analisar rankings e gráficos
- Acessar remotamente com login e senha

É uma ferramenta de apoio para tomada de decisão comercial.

---

## 🚀 Funcionalidades

### 🔐 Autenticação
- Login com usuário e senha
- Controle via `st.secrets` (para nuvem) ou local

### 🗺️ Mapa Interativo
- Heatmap por densidade
- Pontos clicáveis
- Agrupamento automático por cidade
- Popup com múltiplos provedores

### 📊 Dashboards
- Top 10 cidades atendidas
- Gráfico por UF
- Gráfico por região
- Listagem de cidades sem coordenada

### 📄 Informações por Cliente
Ao clicar no ponto:

- Nome fantasia
- UF / Cidade
- Valor mensal (formato BR)
- Vendedor
- Data de assinatura
- Tempo de contrato
- Cidades atendidas

### 🖼️ Identidade Visual
- Logo na tela de login
- Logo na sidebar

---
