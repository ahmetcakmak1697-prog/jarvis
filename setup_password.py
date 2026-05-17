import getpass
import hashlib
import secrets
from pathlib import Path

ITERATIONS = 300_000
ENV_PATH = Path(".env")

def make_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        ITERATIONS
    ).hex()
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest}"

def upsert_env_key(path: Path, key: str, value: str) -> None:
    lines = []
    found = False

    if path.exists():
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    out = []
    for line in lines:
        if line.startswith(key + "="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(line)

    if not found:
        if out and out[-1].strip():
            out.append("")
        out.append(f"{key}={value}")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")

def main():
    print("JARVIS password setup")
    print("Yeni erişim anahtarını girin. Yazarken ekranda görünmez.")

    p1 = getpass.getpass("Yeni şifre: ")
    p2 = getpass.getpass("Tekrar şifre: ")

    if not p1:
        raise SystemExit("Şifre boş olamaz.")

    if p1 != p2:
        raise SystemExit("Şifreler eşleşmedi.")

    if len(p1) < 8:
        raise SystemExit("Şifre en az 8 karakter olmalı.")

    password_hash = make_hash(p1)
    session_secret = secrets.token_urlsafe(48)

    upsert_env_key(ENV_PATH, "JARVIS_PASSWORD_HASH", password_hash)
    upsert_env_key(ENV_PATH, "JARVIS_SESSION_SECRET", session_secret)

    print(".env güncellendi.")
    print("JARVIS_PASSWORD_HASH=***")
    print("JARVIS_SESSION_SECRET=***")
    print("Efendim, erişim anahtarı güvenli biçimde yapılandırıldı.")

if __name__ == "__main__":
    main()
