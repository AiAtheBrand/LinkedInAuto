import unittest
from fastapi import HTTPException

from app.core.dependencies import get_current_user
from app.core.security import create_access_token
from app.models.user import User
from app.repositories.user import UserRepository
from app.routers.auth import get_me, login, register
from app.schemas.user import UserLogin, UserRegister
from tests.test_base import BaseTestCase


class TestAuth(BaseTestCase):

    def test_register_success(self):
        payload = UserRegister(
            email="alice@example.com",
            password="StrongPassword123!",
            full_name="Alice Developer"
        )
        user = register(payload, db=self.db)

        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, "alice@example.com")
        self.assertEqual(user.full_name, "Alice Developer")
        # Ensure password is not plain text in DB
        self.assertNotEqual(user.hashed_password, "StrongPassword123!")
        self.assertTrue(user.hashed_password.startswith("pbkdf2:sha256:"))

    def test_register_duplicate_email(self):
        payload = UserRegister(
            email="alice@example.com",
            password="StrongPassword123!"
        )
        register(payload, db=self.db)

        # Attempt to register same email again (even with different case)
        dup_payload = UserRegister(
            email="ALICE@EXAMPLE.COM",
            password="AnotherPassword123!"
        )
        with self.assertRaises(HTTPException) as ctx:
            register(dup_payload, db=self.db)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Email already registered")

    def test_login_success(self):
        register(
            UserRegister(email="bob@example.com", password="SecretPassword999!"),
            db=self.db
        )

        res = login(
            UserLogin(email="bob@example.com", password="SecretPassword999!"),
            db=self.db
        )
        self.assertEqual(res.token_type, "bearer")
        self.assertTrue(len(res.access_token) > 20)
        self.assertEqual(res.user.email, "bob@example.com")

    def test_login_wrong_password(self):
        register(
            UserRegister(email="carol@example.com", password="CorrectPassword123!"),
            db=self.db
        )

        with self.assertRaises(HTTPException) as ctx:
            login(
                UserLogin(email="carol@example.com", password="WrongPassword!"),
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, "Incorrect email or password")

    def test_login_user_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            login(
                UserLogin(email="nonexistent@example.com", password="Password123!"),
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 401)

    def test_get_current_user_dependency(self):
        user = register(
            UserRegister(email="dave@example.com", password="Password123!"),
            db=self.db
        )
        token = create_access_token({"sub": user.id, "email": user.email})

        # Test valid header
        current_user = get_current_user(authorization=f"Bearer {token}", db=self.db)
        self.assertEqual(current_user.id, user.id)

        # Test get_me router function
        me_res = get_me(current_user=current_user)
        self.assertEqual(me_res.id, user.id)

    def test_get_current_user_missing_or_invalid_header(self):
        # Missing header
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(authorization=None, db=self.db)
        self.assertEqual(ctx.exception.status_code, 401)

        # Invalid scheme
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(authorization="Basic dXNlcjpwYXNz", db=self.db)
        self.assertEqual(ctx.exception.status_code, 401)

        # Invalid token signature
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(authorization="Bearer bad.token.here", db=self.db)
        self.assertEqual(ctx.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
