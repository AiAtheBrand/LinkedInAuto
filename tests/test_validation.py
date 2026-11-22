import unittest
from pydantic import ValidationError

from app.schemas.learning import LearningCreate
from app.schemas.post import PostUpdate
from app.schemas.user import UserLogin, UserRegister


class TestValidation(unittest.TestCase):

    def test_email_valid_formats(self):
        valid_emails = [
            "user@example.com",
            "first.last@domain.co.uk",
            "engineer+tag@sub.domain.org",
            "test_123@tech.io",
        ]
        for email in valid_emails:
            payload = UserRegister(
                email=email,
                password="StrongPassword123!",
                full_name="Valid User"
            )
            self.assertEqual(payload.email, email.lower().strip())

    def test_email_rejects_blank_and_whitespace(self):
        blank_emails = ["", "   ", "\t\n  "]
        for email in blank_emails:
            with self.assertRaises(ValidationError) as ctx:
                UserRegister(
                    email=email,
                    password="StrongPassword123!"
                )
            self.assertIn("email", str(ctx.exception).lower())

    def test_email_rejects_invalid_formats(self):
        invalid_emails = [
            "plainaddress",
            "@missinguser.com",
            "missingdomain@",
            "user@domain",
            "user@.com",
            "user@domain..com",
            "user@domain.c",
        ]
        for email in invalid_emails:
            with self.assertRaises(ValidationError) as ctx:
                UserRegister(
                    email=email,
                    password="StrongPassword123!"
                )
            self.assertIn("email", str(ctx.exception).lower())

    def test_password_rejects_blank_and_whitespace(self):
        invalid_passwords = [
            "",
            "        ",  # 8 spaces must still be rejected
            "   \t\n   ",
            "short",     # less than 8 chars
        ]
        for pwd in invalid_passwords:
            with self.assertRaises(ValidationError) as ctx:
                UserRegister(
                    email="valid@example.com",
                    password=pwd
                )
            self.assertIn("password", str(ctx.exception).lower())

    def test_login_validation(self):
        # Blank email
        with self.assertRaises(ValidationError):
            UserLogin(email="", password="ValidPassword123!")

        # Invalid email format
        with self.assertRaises(ValidationError):
            UserLogin(email="not-an-email", password="ValidPassword123!")

        # Blank password
        with self.assertRaises(ValidationError):
            UserLogin(email="user@example.com", password="   ")

    def test_learning_create_rejects_blanks(self):
        # Blank topic
        with self.assertRaises(ValidationError):
            LearningCreate(
                topic="   ",
                category="Backend",
                what_i_learned="Learning something"
            )

        # Blank category
        with self.assertRaises(ValidationError):
            LearningCreate(
                topic="Topic",
                category="   ",
                what_i_learned="Learning something"
            )

        # Blank what_i_learned
        with self.assertRaises(ValidationError):
            LearningCreate(
                topic="Topic",
                category="Backend",
                what_i_learned="    "
            )

    def test_post_update_rejects_blank_content(self):
        with self.assertRaises(ValidationError):
            PostUpdate(content="   ")


if __name__ == "__main__":
    unittest.main()
