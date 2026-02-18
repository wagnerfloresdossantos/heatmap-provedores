import json
from pathlib import Path
from passlib.hash import pbkdf2_sha256
import getpass

USERS_FILE = Path("users.json")


def main():
    if USERS_FILE.exists():
        try:
            users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        except Exception:
            users = {}
    else:
        users = {}

    username = input("Usuário: ").strip()
    if not username:
        print("Usuário inválido.")
        return

    password = getpass.getpass("Senha: ")
    if not password:
        print("Senha inválida.")
        return

    hashed = pbkdf2_sha256.hash(password)
    users[username] = {"hash": hashed}

    USERS_FILE.write_text(
        json.dumps(users, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"OK! Usuário '{username}' salvo em {USERS_FILE} (hash PBKDF2-SHA256).")
    print("\n--- Para colocar no Streamlit Secrets (1 usuário) ---")
    print(f'app_user = "{username}"')
    print(f'app_password_hash = "{hashed}"')


if __name__ == "__main__":
    main()
