from sqlalchemy.orm import Session

from app.models.learning import Learning


class LearningRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, learning: Learning) -> Learning:
        self.db.add(learning)
        self.db.commit()
        self.db.refresh(learning)
        return learning

    def get_all(self, user_id: int) -> list[Learning]:
        return self.db.query(Learning).filter(Learning.user_id == user_id).all()

    def get_by_id(self, learning_id: int, user_id: int) -> Learning | None:
        return (
            self.db.query(Learning)
            .filter(Learning.id == learning_id, Learning.user_id == user_id)
            .first()
        )

    def update(self, learning: Learning) -> Learning:
        self.db.commit()
        self.db.refresh(learning)
        return learning

    def delete(self, learning: Learning) -> None:
        self.db.delete(learning)
        self.db.commit()
