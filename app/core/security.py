import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone

SECRET_KEY = os.getenv("SECRET_KEY", "linkedin-automation-secure-dev-key-2026")
ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


# -------------------------------------------------------------
# Password Hashing using PBKDF2-HMAC-SHA256 (Constant-time, salted)
# -------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hashes a password with a random 16-byte salt using PBKDF2-HMAC-SHA256."""
    salt = secrets.token_bytes(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2:sha256:{iterations}${base64.b64encode(salt).decode('ascii')}${base64.b64encode(derived).decode('ascii')}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a stored PBKDF2 hash using constant-time comparison."""
    try:
        method, salt_b64, hash_b64 = hashed_password.split("$")
        algo, iterations_str = method.split(":")[-2], method.split(":")[-1]
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_hash = base64.b64decode(hash_b64.encode("ascii"))
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt, iterations
        )
        return hmac.compare_digest(expected_hash, computed_hash)
    except Exception:
        return False


# -------------------------------------------------------------
# Signed Authentication Tokens (JWT-compatible HS256)
# -------------------------------------------------------------

def _b64_url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64_url_decode(data_str: str) -> bytes:
    padding = "=" * (4 - len(data_str) % 4) if len(data_str) % 4 != 0 else ""
    return base64.urlsafe_b64decode(data_str + padding)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Generates an HMAC-SHA256 signed bearer token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = int(expire.timestamp())
    to_encode["iat"] = int(now.timestamp())

    header = {"alg": ALGORITHM, "typ": "JWT"}
    header_json = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_json = json.dumps(to_encode, separators=(",", ":")).encode("utf-8")

    header_b64 = _b64_url_encode(header_json)
    payload_b64 = _b64_url_encode(payload_json)

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    sig_b64 = _b64_url_encode(signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def decode_access_token(token: str) -> dict | None:
    """Validates signature and expiry of a signed bearer token, returning the payload if valid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts

        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        provided_sig = _b64_url_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload_bytes = _b64_url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Verify expiration
        exp = payload.get("exp")
        if exp is not None:
            now_ts = int(datetime.now(timezone.utc).timestamp())
            if now_ts > exp:
                return None

        return payload
    except Exception:
        return None


# -------------------------------------------------------------
# Token Encryption at Rest for LinkedIn OAuth Tokens
# -------------------------------------------------------------

def encrypt_token(raw_token: str) -> str:
    """Encrypts an external provider token at rest using XOR with HMAC keystream and integrity tag."""
    if not raw_token:
        return ""
    nonce = secrets.token_bytes(16)
    # Derive encryption key and auth key from SECRET_KEY
    k_enc = hashlib.sha256(SECRET_KEY.encode("utf-8") + b":enc").digest()
    k_auth = hashlib.sha256(SECRET_KEY.encode("utf-8") + b":auth").digest()

    token_bytes = raw_token.encode("utf-8")
    # Generate keystream from nonce + k_enc
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(token_bytes):
        block = hashlib.sha256(k_enc + nonce + counter.to_bytes(4, "big")).digest()
        keystream.extend(block)
        counter += 1

    ciphertext = bytes(a ^ b for a, b in zip(token_bytes, keystream[:len(token_bytes)]))
    auth_tag = hmac.new(k_auth, nonce + ciphertext, hashlib.sha256).digest()

    package = nonce + auth_tag + ciphertext
    return base64.b64encode(package).decode("ascii")


def decrypt_token(encrypted_package: str) -> str:
    """Decrypts and verifies integrity of an encrypted provider token."""
    if not encrypted_package:
        return ""
    try:
        package = base64.b64decode(encrypted_package.encode("ascii"))
        if len(package) < 48:  # 16 nonce + 32 tag + at least 0 ciphertext
            return ""
        nonce = package[:16]
        auth_tag = package[16:48]
        ciphertext = package[48:]

        k_enc = hashlib.sha256(SECRET_KEY.encode("utf-8") + b":enc").digest()
        k_auth = hashlib.sha256(SECRET_KEY.encode("utf-8") + b":auth").digest()

        expected_tag = hmac.new(k_auth, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(auth_tag, expected_tag):
            return ""

        keystream = bytearray()
        counter = 0
        while len(keystream) < len(ciphertext):
            block = hashlib.sha256(k_enc + nonce + counter.to_bytes(4, "big")).digest()
            keystream.extend(block)
            counter += 1

        plaintext = bytes(a ^ b for a, b in zip(ciphertext, keystream[:len(ciphertext)]))
        return plaintext.decode("utf-8")
    except Exception:
        return ""
