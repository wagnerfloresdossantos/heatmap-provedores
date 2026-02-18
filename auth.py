import json
from pathlib import Path
from passlib.hash import pbkdf2_sha256
import streamlit as st

USERS_FILE = Path("users.json")
LOGO_PATH = Path("assets/logo_oletv.png")


def _load_users_from_users_json() -> dict:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _load_users_from_secrets() -> dict:
    """
    Lê usuários do Streamlit Secrets.
    Aceita dois formatos:

    (A) Um único usuário:
      app_user = "teste"
      app_password_hash = "$pbkdf2-sha256$...."

    (B) Vários usuários:
      [users]
      teste = { hash = "$pbkdf2-sha256$...." }
      admin = { hash = "$pbkdf2-sha256$...." }
    """
    try:
        # se não existir secrets.toml local, o Streamlit pode lançar FileNotFoundError
        _ = st.secrets  # força leitura
    except Exception:
        return {}

    # Formato A (um usuário)
    try:
        user = st.secrets.get("app_user", None)
        h = st.secrets.get("app_password_hash", None)
        if user and h:
            return {str(user): {"hash": str(h)}}
    except Exception:
        pass

    # Formato B (múltiplos)
    try:
        users = st.secrets.get("users", {})
        if isinstance(users, dict) and users:
            out = {}
            for k, v in users.items():
                if isinstance(v, dict) and v.get("hash"):
                    out[str(k)] = {"hash": str(v["hash"])}
            return out
    except Exception:
        pass

    return {}


def load_users() -> dict:
    """
    Prioridade:
      1) st.secrets (nuvem)
      2) users.json (local)
    """
    users = _load_users_from_secrets()
    if users:
        return users
    return _load_users_from_users_json()


def verify_password(username: str, password: str, users: dict) -> bool:
    entry = users.get(username)
    if not entry:
        return False
    hashed = entry.get("hash")
    if not hashed:
        return False
    try:
        return pbkdf2_sha256.verify(password, hashed)
    except Exception:
        return False


def require_login():
    # sessão
    if "auth" not in st.session_state:
        st.session_state.auth = {"logged_in": False, "user": None}

    if st.session_state.auth.get("logged_in"):
        return

    users = load_users()

    # Logo no login
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=180)

    st.title("Acesso restrito")
    st.caption("Faça login para acessar o mapa.")

    if not users:
        st.warning(
            "Nenhum usuário configurado.\n\n"
            "Local: crie um `users.json` (use `python tools/create_user.py`).\n"
            "Nuvem: configure `app_user` e `app_password_hash` em Settings > Secrets."
        )

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
