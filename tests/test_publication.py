import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi import HTTPException

from app.core.security import encrypt_token
from app.models.linkedin_account import LinkedInAccount
from app.models.post import Post
from app.models.learning import Learning
from app.models.user import User
from app.models.publication import Publication
from app.repositories.user import UserRepository
from app.repositories.post import PostRepository
from app.repositories.learning import LearningRepository
from app.repositories.linkedin_account import LinkedInAccountRepository
from app.repositories.publication import PublicationRepository
from app.routers.publication import (
    publish_post_now,
    schedule_post_publication,
    get_user_publications,
    get_publication_by_id,
)
from app.schemas.linkedin import PublicationCreate
from app.services.linkedin_client import LinkedInAPIError
from app.services.publication import PublicationService
from tests.test_base import BaseTestCase


class TestPublication(BaseTestCase):

    def setUp(self):
        super().setUp()
        user_repo = UserRepository(self.db)
        self.user_a = user_repo.create(
            User(email="author.a@example.com", hashed_password="pwd_a", full_name="Author A")
        )
        self.user_b = user_repo.create(
            User(email="author.b@example.com", hashed_password="pwd_b", full_name="Author B")
        )

        learning_repo = LearningRepository(self.db)
        self.learning_a = learning_repo.create(
            Learning(
                user_id=self.user_a.id,
                topic="FastAPI Publishing",
                category="Backend",
                what_i_learned="Decoupling publishing from drafting"
            )
        )

        post_repo = PostRepository(self.db)
        self.post_a = post_repo.create(
            Post(
                user_id=self.user_a.id,
                learning_id=self.learning_a.id,
                content="How I decoupled drafting from publishing in LinkedIn Automation.",
                status="draft"
            )
        )

        account_repo = LinkedInAccountRepository(self.db)
        self.account_a1 = account_repo.create(
            LinkedInAccount(
                user_id=self.user_a.id,
                linkedin_member_urn="urn:li:person:author_a_1",
                name="Author A Profile 1",
                encrypted_access_token=encrypt_token("live_token_1"),
                scopes="w_member_social"
            )
        )
        self.account_a2 = account_repo.create(
            LinkedInAccount(
                user_id=self.user_a.id,
                linkedin_member_urn="urn:li:person:author_a_2",
                name="Author A Profile 2",
                encrypted_access_token=encrypt_token("live_token_2"),
                scopes="w_member_social"
            )
        )
        self.account_b = account_repo.create(
            LinkedInAccount(
                user_id=self.user_b.id,
                linkedin_member_urn="urn:li:person:author_b",
                name="Author B Profile",
                encrypted_access_token=encrypt_token("live_token_b"),
                scopes="w_member_social"
            )
        )

    @patch("app.services.publication.LinkedInClient.create_text_post")
    def test_publish_post_success(self, mock_create):
        mock_create.return_value = {"urn": "urn:li:share:1000000001"}

        req = PublicationCreate(
            post_id=self.post_a.id,
            linkedin_account_id=self.account_a1.id
        )
        pub = publish_post_now(req, current_user=self.user_a, db=self.db)

        self.assertIsNotNone(pub.id)
        self.assertEqual(pub.status, "published")
        self.assertEqual(pub.linkedin_post_urn, "urn:li:share:1000000001")
        self.assertIsNotNone(pub.published_at)
        self.assertEqual(pub.attempt_count, 1)

        # Verify parent post status is updated
        post_repo = PostRepository(self.db)
        updated_post = post_repo.get_by_id(self.post_a.id, self.user_a.id)
        self.assertEqual(updated_post.status, "published")

        # Verify get by id
        fetched = get_publication_by_id(pub.id, current_user=self.user_a, db=self.db)
        self.assertEqual(fetched.id, pub.id)

    @patch("app.services.publication.LinkedInClient.create_post")
    @patch("app.services.publication.LinkedInClient.upload_image")
    @patch("os.path.exists")
    @patch("builtins.open", unittest.mock.mock_open(read_data=b"fake_image_bytes"))
    def test_publish_post_with_image_success(self, mock_exists, mock_upload, mock_create):
        mock_exists.return_value = True
        mock_upload.return_value = "urn:li:image:test_123"
        mock_create.return_value = {"urn": "urn:li:share:img_post_999"}

        self.post_a.image_url = "/uploads/media/test.png"
        post_repo = PostRepository(self.db)
        post_repo.update(self.post_a)

        req = PublicationCreate(
            post_id=self.post_a.id,
            linkedin_account_id=self.account_a1.id
        )
        pub = publish_post_now(req, current_user=self.user_a, db=self.db)

        self.assertEqual(pub.status, "published")
        self.assertEqual(pub.linkedin_post_urn, "urn:li:share:img_post_999")
        mock_upload.assert_called_once()
        mock_create.assert_called_once()
        self.assertEqual(mock_create.call_args.kwargs.get("media_urn"), "urn:li:image:test_123")

    @patch("app.services.publication.LinkedInClient.create_text_post")
    def test_publish_one_draft_to_multiple_accounts(self, mock_create):
        mock_create.side_effect = [
            {"urn": "urn:li:share:dest1"},
            {"urn": "urn:li:share:dest2"},
        ]

        # Publish post_a to destination 1
        pub1 = publish_post_now(
            PublicationCreate(post_id=self.post_a.id, linkedin_account_id=self.account_a1.id),
            current_user=self.user_a,
            db=self.db
        )
        # Publish same post_a to destination 2
        pub2 = publish_post_now(
            PublicationCreate(post_id=self.post_a.id, linkedin_account_id=self.account_a2.id),
            current_user=self.user_a,
            db=self.db
        )

        self.assertEqual(pub1.linkedin_post_urn, "urn:li:share:dest1")
        self.assertEqual(pub2.linkedin_post_urn, "urn:li:share:dest2")
        self.assertNotEqual(pub1.id, pub2.id)

        # List user publications
        pubs = get_user_publications(current_user=self.user_a, db=self.db)
        self.assertEqual(len(pubs), 2)

    @patch("app.services.publication.LinkedInClient.create_text_post")
    def test_publish_post_linkedin_api_failure(self, mock_create):
        mock_create.side_effect = LinkedInAPIError("Rate limit reached", status_code=429)

        pub = publish_post_now(
            PublicationCreate(post_id=self.post_a.id, linkedin_account_id=self.account_a1.id),
            current_user=self.user_a,
            db=self.db
        )
        self.assertEqual(pub.status, "failed")
        self.assertIn("Rate limit reached", pub.error_message)
        self.assertEqual(pub.attempt_count, 1)

    def test_cross_user_isolation_publication(self):
        # User B cannot publish User A's post
        with self.assertRaises(HTTPException) as ctx:
            publish_post_now(
                PublicationCreate(post_id=self.post_a.id, linkedin_account_id=self.account_b.id),
                current_user=self.user_b,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 400)

        # User A cannot publish to User B's account
        with self.assertRaises(HTTPException) as ctx:
            publish_post_now(
                PublicationCreate(post_id=self.post_a.id, linkedin_account_id=self.account_b.id),
                current_user=self.user_a,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 400)

    def test_schedule_post(self):
        future_time = datetime.now(timezone.utc) + timedelta(days=2)
        pub = schedule_post_publication(
            PublicationCreate(
                post_id=self.post_a.id,
                linkedin_account_id=self.account_a1.id,
                scheduled_at=future_time
            ),
            current_user=self.user_a,
            db=self.db
        )
        self.assertEqual(pub.status, "scheduled")
        self.assertIsNotNone(pub.scheduled_at)

        # Attempt to schedule in the past -> must fail
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        with self.assertRaises(HTTPException) as ctx:
            schedule_post_publication(
                PublicationCreate(
                    post_id=self.post_a.id,
                    linkedin_account_id=self.account_a1.id,
                    scheduled_at=past_time
                ),
                current_user=self.user_a,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 400)

    @patch("app.services.publication.LinkedInClient.create_text_post")
    def test_process_due_publications_worker(self, mock_create):
        mock_create.return_value = {"urn": "urn:li:share:scheduled_123"}

        pub_repo = PublicationRepository(self.db)
        post_repo = PostRepository(self.db)
        account_repo = LinkedInAccountRepository(self.db)
        service = PublicationService(pub_repo, post_repo, account_repo)

        # Schedule a job set for 5 minutes ago (due now)
        due_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        pub_repo.create(
            Publication(
                user_id=self.user_a.id,
                post_id=self.post_a.id,
                linkedin_account_id=self.account_a1.id,
                status="scheduled",
                scheduled_at=due_time
            )
        )

        results = service.process_due_publications(now=datetime.now(timezone.utc))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "published")
        self.assertEqual(results[0].linkedin_post_urn, "urn:li:share:scheduled_123")


if __name__ == "__main__":
    unittest.main()
