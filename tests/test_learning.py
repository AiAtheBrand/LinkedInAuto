import unittest
from fastapi import HTTPException

from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.learning import LearningCreate
from app.routers.learning import (
    create_learning,
    get_learning,
    get_learning_by_id,
    update_learning,
    delete_learning,
)
from tests.test_base import BaseTestCase


class TestLearning(BaseTestCase):

    def setUp(self):
        super().setUp()
        user_repo = UserRepository(self.db)
        self.user_a = user_repo.create(
            User(email="usera@example.com", hashed_password="hash_a", full_name="User A")
        )
        self.user_b = user_repo.create(
            User(email="userb@example.com", hashed_password="hash_b", full_name="User B")
        )

    def test_create_and_get_learning(self):
        payload = LearningCreate(
            topic="FastAPI Dependency Injection",
            category="Backend",
            problem="Understanding Depends",
            what_i_learned="How FastAPI resolves dependencies hierarchically",
            project="LinkedIn Automation",
            lesson="Cleaner code with Depends"
        )
        created = create_learning(payload, current_user=self.user_a, db=self.db)
        self.assertIsNotNone(created.id)
        self.assertEqual(created.user_id, self.user_a.id)
        self.assertEqual(created.topic, "FastAPI Dependency Injection")

        # Get by ID
        fetched = get_learning_by_id(created.id, current_user=self.user_a, db=self.db)
        self.assertEqual(fetched.id, created.id)
        self.assertEqual(fetched.topic, created.topic)

        # Get all
        all_entries = get_learning(current_user=self.user_a, db=self.db)
        self.assertEqual(len(all_entries), 1)
        self.assertEqual(all_entries[0].id, created.id)

    def test_multi_tenant_isolation_learning(self):
        # User A creates a learning entry
        created = create_learning(
            LearningCreate(
                topic="User A Private Topic",
                category="Confidential",
                what_i_learned="User A secrets"
            ),
            current_user=self.user_a,
            db=self.db
        )

        # User B lists learnings -> must NOT see User A's item
        user_b_entries = get_learning(current_user=self.user_b, db=self.db)
        self.assertEqual(len(user_b_entries), 0)

        # User B attempts to access User A's learning by ID -> 404
        with self.assertRaises(HTTPException) as ctx:
            get_learning_by_id(created.id, current_user=self.user_b, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

        # User B attempts to update User A's learning -> 404
        with self.assertRaises(HTTPException) as ctx:
            update_learning(
                created.id,
                LearningCreate(topic="Hacked", category="Hacked", what_i_learned="Hacked"),
                current_user=self.user_b,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 404)

        # User B attempts to delete User A's learning -> 404
        with self.assertRaises(HTTPException) as ctx:
            delete_learning(created.id, current_user=self.user_b, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

        # Verify User A's learning is untouched
        user_a_check = get_learning_by_id(created.id, current_user=self.user_a, db=self.db)
        self.assertEqual(user_a_check.topic, "User A Private Topic")

    def test_get_learning_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            get_learning_by_id(99999, current_user=self.user_a, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Learning entry not found")

    def test_update_learning(self):
        initial = create_learning(
            LearningCreate(
                topic="Initial Topic",
                category="General",
                what_i_learned="Initial Notes"
            ),
            current_user=self.user_a,
            db=self.db
        )

        update_payload = LearningCreate(
            topic="Updated Topic",
            category="Refined Category",
            problem="Identified edge case",
            what_i_learned="Refined Notes",
            project="Project X",
            lesson="Always test edge cases"
        )
        updated = update_learning(initial.id, update_payload, current_user=self.user_a, db=self.db)
        self.assertEqual(updated.topic, "Updated Topic")
        self.assertEqual(updated.category, "Refined Category")
        self.assertEqual(updated.problem, "Identified edge case")

    def test_update_learning_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            update_learning(
                99999,
                LearningCreate(topic="T", category="C", what_i_learned="W"),
                current_user=self.user_a,
                db=self.db
            )
        self.assertEqual(ctx.exception.status_code, 404)

    def test_delete_learning(self):
        item = create_learning(
            LearningCreate(
                topic="To Delete",
                category="Temporary",
                what_i_learned="Temporary knowledge"
            ),
            current_user=self.user_a,
            db=self.db
        )

        res = delete_learning(item.id, current_user=self.user_a, db=self.db)
        self.assertEqual(res["message"], "Learning entry deleted successfully")

        # Verify it cannot be retrieved
        with self.assertRaises(HTTPException) as ctx:
            get_learning_by_id(item.id, current_user=self.user_a, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)

    def test_delete_learning_not_found(self):
        with self.assertRaises(HTTPException) as ctx:
            delete_learning(99999, current_user=self.user_a, db=self.db)
        self.assertEqual(ctx.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
