import unittest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.security import encrypt_token
from app.models.learning import Learning
from app.models.linkedin_account import LinkedInAccount
from app.models.post import Post
from app.models.social_account import SocialAccount
from app.models.user import User
from app.repositories.learning import LearningRepository
from app.repositories.linkedin_account import LinkedInAccountRepository
from app.repositories.post import PostRepository
from app.repositories.publication import PublicationRepository
from app.repositories.social_account import SocialAccountRepository
from app.repositories.user import UserRepository
from app.schemas.social import MultiPublishRequest, PlatformDestination
from app.services.publication import PublicationService
from tests.test_base import BaseTestCase


class TestMultiPublish(BaseTestCase):

    def setUp(self):
        super().setUp()
        user_repo = UserRepository(self.db)
        self.user = user_repo.create(
            User(email="multi.publisher@example.com", hashed_password="pwd", full_name="Multi Publisher")
        )

        learning_repo = LearningRepository(self.db)
        self.learning = learning_repo.create(
            Learning(
                user_id=self.user.id,
                topic="Multi-Platform Publishing",
                category="Full-Stack",
                what_i_learned="Publishing to LinkedIn, Facebook, and Instagram seamlessly"
            )
        )

        post_repo = PostRepository(self.db)
        self.post_no_image = post_repo.create(
            Post(
                user_id=self.user.id,
                learning_id=self.learning.id,
                content="Text post without image",
                status="draft",
                image_url=None
            )
        )
        self.post_with_image = post_repo.create(
            Post(
                user_id=self.user.id,
                learning_id=self.learning.id,
                content="Media post with image",
                status="draft",
                image_url="/uploads/media/test_image.png"
            )
        )

        # Connected accounts
        li_repo = LinkedInAccountRepository(self.db)
        self.li_account = li_repo.create(
            LinkedInAccount(
                user_id=self.user.id,
                linkedin_member_urn="urn:li:person:multi_li",
                name="LinkedIn Profile",
                encrypted_access_token=encrypt_token("tok_li"),
                scopes="w_member_social"
            )
        )

        social_repo = SocialAccountRepository(self.db)
        self.fb_account = social_repo.create(
            SocialAccount(
                user_id=self.user.id,
                platform="facebook",
                name="Facebook Page",
                account_identifier="fb_page_123",
                email="fb@example.com",
                encrypted_access_token=encrypt_token("tok_fb")
            )
        )
        self.ig_account = social_repo.create(
            SocialAccount(
                user_id=self.user.id,
                platform="instagram",
                name="Instagram Account",
                account_identifier="@tech_daily",
                email="ig@example.com",
                encrypted_access_token=encrypt_token("tok_ig")
            )
        )

    def test_multi_publish_request_validation(self):
        # Empty destinations should be rejected
        with self.assertRaises(ValidationError):
            MultiPublishRequest(post_id=self.post_no_image.id, destinations=[])

        # Invalid platform should be rejected
        with self.assertRaises(ValidationError):
            MultiPublishRequest(
                post_id=self.post_no_image.id,
                destinations=[PlatformDestination(platform="invalid_platform", account_id=1)]
            )

    @patch("app.services.publication.LinkedInClient.create_text_post")
    @patch("app.services.publication.MetaClient.publish_facebook")
    def test_publish_to_linkedin_and_facebook_success(self, mock_fb, mock_li):
        mock_li.return_value = {"urn": "urn:li:share:11111"}
        mock_fb.return_value = {"id": "fb_post_22222"}

        pub_repo = PublicationRepository(self.db)
        post_repo = PostRepository(self.db)
        li_repo = LinkedInAccountRepository(self.db)
        social_repo = SocialAccountRepository(self.db)
        service = PublicationService(pub_repo, post_repo, li_repo, social_account_repo=social_repo)

        destinations = [
            PlatformDestination(platform="linkedin", account_id=self.li_account.id),
            PlatformDestination(platform="facebook", account_id=self.fb_account.id),
        ]

        pubs = service.publish_multi_destinations(
            user_id=self.user.id,
            post_id=self.post_no_image.id,
            destinations=destinations
        )

        self.assertEqual(len(pubs), 2)
        li_pub = next(p for p in pubs if p.platform == "linkedin")
        fb_pub = next(p for p in pubs if p.platform == "facebook")

        self.assertEqual(li_pub.status, "published")
        self.assertEqual(li_pub.linkedin_post_urn, "urn:li:share:11111")

        self.assertEqual(fb_pub.status, "published")
        self.assertEqual(fb_pub.remote_post_id, "fb_post_22222")

    @patch("app.services.publication.MetaClient.publish_instagram")
    def test_instagram_rejects_post_without_image(self, mock_ig):
        pub_repo = PublicationRepository(self.db)
        post_repo = PostRepository(self.db)
        li_repo = LinkedInAccountRepository(self.db)
        social_repo = SocialAccountRepository(self.db)
        service = PublicationService(pub_repo, post_repo, li_repo, social_account_repo=social_repo)

        destinations = [
            PlatformDestination(platform="instagram", account_id=self.ig_account.id)
        ]

        # Instagram must reject posts without images
        with self.assertRaises(ValueError) as ctx:
            service.publish_multi_destinations(
                user_id=self.user.id,
                post_id=self.post_no_image.id,
                destinations=destinations
            )
        self.assertIn("image", str(ctx.exception).lower())
        mock_ig.assert_not_called()

    @patch("app.services.publication.MetaClient.publish_instagram")
    @patch("app.services.publication.PublicationService._resolve_media_bytes")
    def test_instagram_succeeds_with_image(self, mock_resolve, mock_ig):
        mock_resolve.return_value = b"fake-image-bytes"
        mock_ig.return_value = {"id": "ig_media_33333"}

        pub_repo = PublicationRepository(self.db)
        post_repo = PostRepository(self.db)
        li_repo = LinkedInAccountRepository(self.db)
        social_repo = SocialAccountRepository(self.db)
        service = PublicationService(pub_repo, post_repo, li_repo, social_account_repo=social_repo)

        destinations = [
            PlatformDestination(platform="instagram", account_id=self.ig_account.id)
        ]

        pubs = service.publish_multi_destinations(
            user_id=self.user.id,
            post_id=self.post_with_image.id,
            destinations=destinations
        )

        self.assertEqual(len(pubs), 1)
        self.assertEqual(pubs[0].platform, "instagram")
        self.assertEqual(pubs[0].status, "published")
        self.assertEqual(pubs[0].remote_post_id, "ig_media_33333")


if __name__ == "__main__":
    unittest.main()
