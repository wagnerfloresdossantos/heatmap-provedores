import streamlit as st
from passlib.hash import pbkdf2_sha256
from pathlib import Path

LOGO_PATH = Path("assets/logo_oletv.png")

def _get_users() -> dict:
    # Espera algo assim em secrets:
    # [users]
    # test = "<hash>"
    users = {}
    if "users" in st.secrets:
        users = dict(st.secrets["users"])
    return users

def verify_password(username: str, password: str, users: dict) -> bool:
    hashed = users.get(username)
    if not hashed:
        return False
    try:
        return pbkdf2_sha256.verify(password, hashed)
    except Exception:
        return False

def require_login():
    if "auth" not in st.session_state:
        st.session_state.auth = {"logged_in": False, "user": None}

    if st.session_state.auth["logged_in"]:
        return

    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=180)

    st.title("Acesso restrito")
    st.caption("Faça login para acessar o mapa.")

    users = _get_users()

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        if verify_password(username, password, users):
            st.session_state.auth = {"logged_in": True, "user": username}
            st.success("Login ok.")
            st.rerun()
        else:
            st.error("Usuário ou senha inválidos.")
    st.stop()

def logout_button():
    if st.session_state.get("auth", {}).get("logged_in"):
        if st.sidebar.button("Sair"):
            st.session_state.auth = {"logged_in": False, "user": None}
            st.rerun()
