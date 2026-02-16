import json
from pathlib import Path
from passlib.hash import pbkdf2_sha256
import getpass

USERS_FILE = Path("users.json")

def main():
    if USERS_FILE.exists():
        users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
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

    users[username] = {"hash": pbkdf2_sha256.hash(password)}
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Ok! Usuário '{username}' salvo em {USERS_FILE} (hash bcrypt).")

if __name__ == "__main__":
    main()
