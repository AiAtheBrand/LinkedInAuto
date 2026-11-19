from sqlalchemy.orm import Session

from app.models.post import Post


class PostRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, post: Post) -> Post:
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return post

    def get_all(self, user_id: int) -> list[Post]:
        return self.db.query(Post).filter(Post.user_id == user_id).all()

    def get_by_id(self, post_id: int, user_id: int) -> Post | None:
        return (
            self.db.query(Post)
            .filter(Post.id == post_id, Post.user_id == user_id)
            .first()
        )

    def update(self, post: Post) -> Post:
        self.db.commit()
        self.db.refresh(post)
        return post

    def delete(self, post: Post) -> None:
        self.db.delete(post)
        self.db.commit()
