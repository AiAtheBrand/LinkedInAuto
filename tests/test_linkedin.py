import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from app.core.security import decrypt_token
from app.models.user import User
from app.repositories.user import UserRepository
from app.routers.linkedin import (
    get_oauth_authorize_url,
    oauth_callback,
    oauth_callback_browser,
    get_accounts,
    disconnect_account,
)
from app.schemas.linkedin import OAuthCallbackRequest
from tests.test_base import BaseTestCase


class TestLinkedIn(BaseTestCase):

    def setUp(self):
        super().setUp()
        user_repo = UserRepository(self.db)
        self.user_a = user_repo.create(
            User(email="alice.li@example.com", hashed_password="hash_a", full_name="Alice LinkedIn")
        )
        self.user_b = user_repo.create(
            User(email="bob.li@example.com", hashed_password="hash_b", full_name="Bob LinkedIn")
        )

    def test_get_oauth_authorize_url(self):
        res = get_oauth_authorize_url(current_user=self.user_a, db=self.db)
        self.assertIn("https://www.linkedin.com/oauth/v2/authorization", res.authorization_url)
        self.assertIn("response_type=code", res.authorization_url)
        self.assertIn(res.state, res.authorization_url)
        self.assertTrue(len(res.state) >= 32)

    @patch("app.services.linkedin.LinkedInClient.get_user_profile")
    @patch("app.services.linkedin.LinkedInClient.exchange_code_for_token")
    def test_oauth_callback_success(self, mock_exchange, mock_profile):
        # 1. Generate auth URL to record valid state
        auth_res = get_oauth_authorize_url(current_user=self.user_a, db=self.db)
        state = auth_res.state

        # Mock LinkedIn external responses
        mock_exchange.return_value = {
            "access_token": "AQV_live_access_token_12345",
            "expires_in": 5184000,
            "scope": "openid profile email w_member_social"
        }
        mock_profile.return_value = {
            "sub": "abcd1234ef",
            "name": "Alice Engineer",
            "email": "alice.linkedin@example.com",
            "picture": "https://media.licdn.com/dms/image/alice.jpg"
        }

        # 2. Complete callback
        cb_req = OAuthCallbackRequest(code="auth_code_xyz", state=state)
        account = oauth_callback(cb_req, current_user=self.user_a, db=self.db)

        self.assertIsNotNone(account.id)
        self.assertEqual(account.user_id, self.user_a.id)
        self.assertEqual(account.linkedin_member_urn, "urn:li:person:abcd1234ef")
        self.assertEqual(account.name, "Alice Engineer")

        # Crucial security assertion: Token MUST be encrypted at rest in DB
        self.assertNotEqual(account.encrypted_access_token, "AQV_live_access_token_12345")
        decrypted = decrypt_token(account.encrypted_access_token)
        self.assertEqual(decrypted, "AQV_live_access_token_12345")

        # Verify listing accounts
        accounts = get_accounts(current_user=self.user_a, db=self.db)
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].id, account.id)

    @patch("app.services.linkedin.LinkedInClient.get_user_profile")
    @patch("app.services.linkedin.LinkedInClient.exchange_code_for_token")
    def test_oauth_callback_browser_success(self, mock_exchange, mock_profile):
        auth_res = get_oauth_authorize_url(current_user=self.user_a, db=self.db)
        state = auth_res.state

        mock_exchange.return_value = {
            "access_token": "AQV_browser_access_token_67890",
            "expires_in": 3600,
            "scope": "openid profile email w_member_social"
        }
        mock_profile.return_value = {
            "sub": "browser_sub_123",
            "name": "Browser User",
            "email": "browser@example.com"
        }

        html_response = oauth_callback_browser(code="browser_code", state=state, db=self.db)
        self.assertIn("Account Connected!", html_response)
        self.assertIn("Browser User", html_response)

        # Verify account was saved in DB
        accounts = get_accounts(current_user=self.user_a, db=self.db)
        self.assertEqual(len(accounts), 1)
        self.assertEqual(accounts[0].linkedin_member_urn, "urn:li:person:browser_sub_123")

    def test_oauth_callback_invalid_or_reused_state(self):
        auth_res = get_oauth_authorize_url(current_user=self.user_a, db=self.db)
        valid_state = auth_res.state

        # Invalid state
        with self.assertRaises(HTTPException) as ctx:
            oauth_callback(
                OAuthCallbackRequest(code="code", state="tampered_state"),
                current_user=self.user_a,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 400)

        # State belonging to User A cannot be used by User B
        with self.assertRaises(HTTPException) as ctx:
            oauth_callback(
                OAuthCallbackRequest(code="code", state=valid_state),
                current_user=self.user_b,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 400)

    @patch("app.services.linkedin.LinkedInClient.get_user_profile")
    @patch("app.services.linkedin.LinkedInClient.exchange_code_for_token")
    def test_multi_account_and_isolation(self, mock_exchange, mock_profile):
        # User A connects account
        auth_a = get_oauth_authorize_url(current_user=self.user_a, db=self.db)
        mock_exchange.return_value = {"access_token": "token_a", "expires_in": 3600}
        mock_profile.return_value = {"sub": "member_a", "name": "Alice A"}
        acc_a = oauth_callback(
            OAuthCallbackRequest(code="c_a", state=auth_a.state),
            current_user=self.user_a,
            db=self.db
        )

        # User B should NOT see User A's account
        user_b_accounts = get_accounts(current_user=self.user_b, db=self.db)
        self.assertEqual(len(user_b_accounts), 0)

        # User B cannot disconnect User A's account
        with self.assertRaises(HTTPException) as ctx:
            disconnect_account(acc_a.id, current_user=self.user_b, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

        # User A disconnects account
        res = disconnect_account(acc_a.id, current_user=self.user_a, db=self.db)
        self.assertEqual(res["message"], "LinkedIn account disconnected successfully")

        # Verify it is gone
        self.assertEqual(len(get_accounts(current_user=self.user_a, db=self.db)), 0)


if __name__ == "__main__":
    unittest.main()
