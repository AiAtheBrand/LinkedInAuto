import unittest
from datetime import timedelta

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    encrypt_token,
    decrypt_token,
)


class TestSecurity(unittest.TestCase):

    def test_password_hashing(self):
        pwd = "SuperSecretPassword123!"
        h1 = hash_password(pwd)
        h2 = hash_password(pwd)

        # Salting ensures two hashes of identical passwords are distinct
        self.assertNotEqual(h1, h2)
        self.assertTrue(verify_password(pwd, h1))
        self.assertTrue(verify_password(pwd, h2))
        self.assertFalse(verify_password("WrongPassword", h1))

    def test_access_token_lifecycle(self):
        payload = {"sub": 42, "email": "test@example.com"}
        token = create_access_token(payload, expires_delta=timedelta(minutes=15))
        decoded = decode_access_token(token)

        self.assertIsNotNone(decoded)
        self.assertEqual(decoded["sub"], 42)
        self.assertEqual(decoded["email"], "test@example.com")
        self.assertIn("exp", decoded)

    def test_access_token_expired(self):
        payload = {"sub": 99}
        # Expired token in past
        token = create_access_token(payload, expires_delta=timedelta(minutes=-5))
        decoded = decode_access_token(token)
        self.assertIsNone(decoded)

    def test_access_token_tampered(self):
        token = create_access_token({"sub": 1})
        parts = token.split(".")
        # Tamper payload
        tampered_token = f"{parts[0]}.eyJhZG1pbiI6dHJ1ZX0.{parts[2]}"
        self.assertIsNone(decode_access_token(tampered_token))

    def test_token_encryption_at_rest(self):
        secret_oauth_token = "AQV1234567890_linkedin_oauth_secret_access_token"
        encrypted = encrypt_token(secret_oauth_token)

        self.assertNotEqual(encrypted, secret_oauth_token)
        decrypted = decrypt_token(encrypted)
        self.assertEqual(decrypted, secret_oauth_token)

    def test_token_encryption_tamper_detection(self):
        secret = "secret-token"
        encrypted = encrypt_token(secret)
        # Flip a character in the base64 package
        corrupted = encrypted[:-2] + ("A" if encrypted[-2] != "A" else "B") + encrypted[-1]
        self.assertEqual(decrypt_token(corrupted), "")


if __name__ == "__main__":
    unittest.main()
