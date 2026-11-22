import unittest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.security import decrypt_token
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.social import SocialAccountCreate
from tests.test_base import BaseTestCase


class TestSocialValidation(BaseTestCase):

    def setUp(self):
        super().setUp()
        user_repo = UserRepository(self.db)
        self.user = user_repo.create(
            User(email="social.user@example.com", hashed_password="hashed_pwd", full_name="Social Tester")
        )

    def test_social_account_valid_facebook(self):
        payload = SocialAccountCreate(
            platform="facebook",
            name="My Official Facebook Page",
            account_identifier="1029384756",
            email="page.admin@company.org",
            access_token="EAABsb98234token_here"
        )
        self.assertEqual(payload.platform, "facebook")
        self.assertEqual(payload.email, "page.admin@company.org")

    def test_social_account_valid_instagram(self):
        payload = SocialAccountCreate(
            platform="instagram",
            name="Dev Engineer Instagram",
            account_identifier="@code_daily",
            email="instagram@company.org",
            access_token="IGQVJ_live_token"
        )
        self.assertEqual(payload.platform, "instagram")
        self.assertEqual(payload.account_identifier, "@code_daily")

    def test_social_account_rejects_invalid_platform(self):
        with self.assertRaises(ValidationError):
            SocialAccountCreate(
                platform="twitter",
                name="Twitter Account",
                account_identifier="handle",
                access_token="token"
            )

    def test_social_account_rejects_blank_fields(self):
        # Blank name
        with self.assertRaises(ValidationError):
            SocialAccountCreate(
                platform="facebook",
                name="   ",
                account_identifier="12345",
                access_token="token"
            )

        # Blank account_identifier
        with self.assertRaises(ValidationError):
            SocialAccountCreate(
                platform="facebook",
                name="Facebook Page",
                account_identifier="   ",
                access_token="token"
            )

        # Blank access_token
        with self.assertRaises(ValidationError):
            SocialAccountCreate(
                platform="facebook",
                name="Facebook Page",
                account_identifier="12345",
                access_token="   "
            )

    def test_social_account_rejects_invalid_email(self):
        invalid_emails = ["not-an-email", "missing@tld", "@domain.com", "user@.com"]
        for email in invalid_emails:
            with self.assertRaises(ValidationError):
                SocialAccountCreate(
                    platform="instagram",
                    name="Instagram Account",
                    account_identifier="@coder",
                    email=email,
                    access_token="token"
                )

    def test_instagram_rejects_invalid_handle(self):
        invalid_handles = ["", "   ", "has spaces in it", "bad!characters$"]
        for handle in invalid_handles:
            with self.assertRaises(ValidationError):
                SocialAccountCreate(
                    platform="instagram",
                    name="Instagram Account",
                    account_identifier=handle,
                    access_token="token"
                )


if __name__ == "__main__":
    unittest.main()
