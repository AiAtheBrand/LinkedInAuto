import asyncio
import io
import unittest
from unittest.mock import patch
from fastapi import HTTPException, UploadFile

from app.models.user import User
from app.repositories.user import UserRepository
from app.repositories.post import PostRepository
from app.schemas.learning import LearningCreate
from app.schemas.post import PostUpdate
from app.routers.learning import create_learning
from app.routers.post import (
    generate_post,
    get_all_posts,
    get_post_by_id,
    update_post,
    upload_post_image,
    delete_post,
)
from tests.test_base import BaseTestCase


class TestPost(BaseTestCase):

    def setUp(self):
        super().setUp()
        user_repo = UserRepository(self.db)
        self.user_a = user_repo.create(
            User(email="usera@example.com", hashed_password="hash_a", full_name="User A")
        )
        self.user_b = user_repo.create(
            User(email="userb@example.com", hashed_password="hash_b", full_name="User B")
        )

    def _create_learning(self, user: User):
        item = create_learning(
            LearningCreate(
                topic="Python Decorators",
                category="Python",
                what_i_learned="Decorators wrap functions and extend behavior"
            ),
            current_user=user,
            db=self.db
        )
        return item.id

    @patch("app.services.post.AIService.generate_linkedin_post")
    def test_generate_post_success(self, mock_ai):
        mock_ai.return_value = "Mastering Python Decorators: Here is what I learned today."

        learning_id = self._create_learning(self.user_a)
        post = generate_post(learning_id, current_user=self.user_a, db=self.db)

        self.assertIsNotNone(post.id)
        self.assertEqual(post.user_id, self.user_a.id)
        self.assertEqual(post.learning_id, learning_id)
        self.assertEqual(post.content, "Mastering Python Decorators: Here is what I learned today.")
        self.assertEqual(post.status, "draft")

        # Test listing all posts
        all_posts = get_all_posts(current_user=self.user_a, db=self.db)
        self.assertEqual(len(all_posts), 1)
        self.assertEqual(all_posts[0].id, post.id)

    @patch("app.services.post.AIService.generate_linkedin_post")
    def test_multi_tenant_isolation_post(self, mock_ai):
        mock_ai.return_value = "User A Private Content"
        learning_id = self._create_learning(self.user_a)
        post_a = generate_post(learning_id, current_user=self.user_a, db=self.db)

        # User B attempts to generate post using User A's learning_id -> 404
        with self.assertRaises(HTTPException) as ctx:
            generate_post(learning_id, current_user=self.user_b, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

        # User B gets all posts -> must be empty
        user_b_posts = get_all_posts(current_user=self.user_b, db=self.db)
        self.assertEqual(len(user_b_posts), 0)

        # User B attempts to get User A's post by ID -> 404
        with self.assertRaises(HTTPException) as ctx:
            get_post_by_id(post_a.id, current_user=self.user_b, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

        # User B attempts to update User A's post -> 404
        with self.assertRaises(HTTPException) as ctx:
            update_post(
                post_a.id,
                PostUpdate(content="Hacked Content"),
                current_user=self.user_b,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 404)

        # User B attempts to delete User A's post -> 404
        with self.assertRaises(HTTPException) as ctx:
            delete_post(post_a.id, current_user=self.user_b, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

        # Verify post_a is untouched
        post_check = get_post_by_id(post_a.id, current_user=self.user_a, db=self.db)
        self.assertEqual(post_check.content, "User A Private Content")

    def test_generate_post_learning_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            generate_post(99999, current_user=self.user_a, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Learning entry not found")

    @patch("app.services.post.AIService.generate_linkedin_post")
    def test_update_post(self, mock_ai):
        mock_ai.return_value = "Initial Draft"
        learning_id = self._create_learning(self.user_a)
        post = generate_post(learning_id, current_user=self.user_a, db=self.db)

        # Update the post content and image_url
        updated = update_post(
            post.id,
            PostUpdate(content="Refined LinkedIn Post with strong call-to-action.", image_url="/uploads/media/custom.png"),
            current_user=self.user_a,
            db=self.db
        )
        self.assertEqual(updated.content, "Refined LinkedIn Post with strong call-to-action.")
        self.assertEqual(updated.image_url, "/uploads/media/custom.png")

        # Verify persistence in repository
        repo = PostRepository(self.db)
        persisted = repo.get_by_id(post.id, self.user_a.id)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.content, "Refined LinkedIn Post with strong call-to-action.")
        self.assertEqual(persisted.image_url, "/uploads/media/custom.png")

    @patch("app.services.post.AIService.generate_linkedin_post")
    def test_upload_post_image_success(self, mock_ai):
        mock_ai.return_value = "Post before image"
        learning_id = self._create_learning(self.user_a)
        post = generate_post(learning_id, current_user=self.user_a, db=self.db)

        # Upload a valid PNG file
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        upload_file = UploadFile(
            filename="diagram.png",
            file=io.BytesIO(png_bytes),
            headers={"content-type": "image/png"}
        )

        updated_post = upload_post_image(
            post.id, upload_file, current_user=self.user_a, db=self.db
        )
        self.assertIsNotNone(updated_post.image_url)
        self.assertTrue(updated_post.image_url.startswith("/uploads/media/"))
        self.assertTrue(updated_post.image_url.endswith(".png"))

    @patch("app.services.post.AIService.generate_linkedin_post")
    def test_upload_post_image_invalid_magic_signature(self, mock_ai):
        mock_ai.return_value = "Post test"
        learning_id = self._create_learning(self.user_a)
        post = generate_post(learning_id, current_user=self.user_a, db=self.db)

        # Upload a non-image file (e.g. text masquerading as png)
        invalid_file = UploadFile(
            filename="fake.png",
            file=io.BytesIO(b"not an image binary payload"),
            headers={"content-type": "image/png"}
        )

        with self.assertRaises(HTTPException) as ctx:
            upload_post_image(
                post.id, invalid_file, current_user=self.user_a, db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid file format", ctx.exception.detail)

    @patch("app.services.post.AIService.generate_linkedin_post")
    def test_upload_post_image_cross_user_isolation(self, mock_ai):
        mock_ai.return_value = "Post owned by User A"
        learning_id = self._create_learning(self.user_a)
        post_a = generate_post(learning_id, current_user=self.user_a, db=self.db)

        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        upload_file = UploadFile(
            filename="test.png",
            file=io.BytesIO(png_bytes),
            headers={"content-type": "image/png"}
        )

        # User B cannot upload an image to User A's post
        with self.assertRaises(HTTPException) as ctx:
            upload_post_image(
                post_a.id, upload_file, current_user=self.user_b, db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_update_post_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            update_post(99999, PostUpdate(content="Non existent"), current_user=self.user_a, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

    @patch("app.services.post.AIService.generate_linkedin_post")
    def test_delete_post(self, mock_ai):
        mock_ai.return_value = "To be deleted"
        learning_id = self._create_learning(self.user_a)
        post = generate_post(learning_id, current_user=self.user_a, db=self.db)

        res = delete_post(post.id, current_user=self.user_a, db=self.db)
        self.assertEqual(res["message"], "Post deleted successfully")

        # Verify it cannot be deleted again
        with self.assertRaises(HTTPException) as ctx:
            delete_post(post.id, current_user=self.user_a, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_delete_post_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            delete_post(99999, current_user=self.user_a, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
