import io
import unittest
from unittest.mock import patch
from fastapi import HTTPException, UploadFile

from app.models.learning import Learning
from app.models.post import Post
from app.models.user import User
from app.repositories.learning import LearningRepository
from app.repositories.post import PostRepository
from app.repositories.user import UserRepository
from app.routers.post import upload_post_image, upload_post_images, delete_post_image, generate_post
from app.schemas.post import PostResponse
from app.services.post import PostService
from tests.test_base import BaseTestCase


class TestMultiImage(BaseTestCase):

    def setUp(self):
        super().setUp()
        user_repo = UserRepository(self.db)
        self.user = user_repo.create(
            User(email="photo.author@example.com", hashed_password="pwd", full_name="Photo Author")
        )

        learning_repo = LearningRepository(self.db)
        self.learning = learning_repo.create(
            Learning(
                user_id=self.user.id,
                topic="Multi-image uploads",
                category="Full-Stack",
                what_i_learned="Implementing multi-image galleries for social media automation"
            )
        )

        post_repo = PostRepository(self.db)
        self.post = post_repo.create(
            Post(
                user_id=self.user.id,
                learning_id=self.learning.id,
                content="Exploring multi-image support for our social media posts.",
                status="draft"
            )
        )

    def _create_fake_png(self, name: str = "img.png") -> UploadFile:
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        return UploadFile(
            filename=name,
            file=io.BytesIO(png_bytes),
            headers={"content-type": "image/png"}
        )

    def test_upload_multiple_images_at_once(self):
        file1 = self._create_fake_png("slide1.png")
        file2 = self._create_fake_png("slide2.png")

        updated = upload_post_images(
            self.post.id,
            files=[file1, file2],
            current_user=self.user,
            db=self.db
        )

        self.assertIsNotNone(updated.image_url)
        self.assertEqual(len(updated.image_urls), 2)
        self.assertEqual(updated.image_url, updated.image_urls[0])
        self.assertTrue(updated.image_urls[0].endswith(".png"))
        self.assertTrue(updated.image_urls[1].endswith(".png"))
        self.assertNotEqual(updated.image_urls[0], updated.image_urls[1])

    def test_upload_images_appends_to_existing(self):
        file1 = self._create_fake_png("img1.png")
        upload_post_images(self.post.id, files=[file1], current_user=self.user, db=self.db)

        # Upload second image
        file2 = self._create_fake_png("img2.png")
        updated = upload_post_images(self.post.id, files=[file2], current_user=self.user, db=self.db)

        self.assertEqual(len(updated.image_urls), 2)
        self.assertEqual(updated.image_url, updated.image_urls[0])

    def test_delete_individual_image(self):
        file1 = self._create_fake_png("first.png")
        file2 = self._create_fake_png("second.png")
        upload_post_images(self.post.id, files=[file1, file2], current_user=self.user, db=self.db)

        # Delete the first image (index 0)
        updated = delete_post_image(
            post_id=self.post.id,
            image_index=0,
            current_user=self.user,
            db=self.db
        )

        self.assertEqual(len(updated.image_urls), 1)
        self.assertEqual(updated.image_url, updated.image_urls[0])

    def test_delete_image_out_of_bounds(self):
        with self.assertRaises(HTTPException) as ctx:
            delete_post_image(
                post_id=self.post.id,
                image_index=99,
                current_user=self.user,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.services.post.AIService.generate_linkedin_post")
    def test_ai_generation_error_returns_clean_http_exception(self, mock_ai):
        mock_ai.side_effect = RuntimeError("Groq rate limit exceeded: please retry in 10s")

        with self.assertRaises(HTTPException) as ctx:
            generate_post(self.learning.id, current_user=self.user, db=self.db)

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("AI post generation failed", ctx.exception.detail)
        self.assertIn("rate limit exceeded", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
