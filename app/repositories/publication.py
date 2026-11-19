from datetime import datetime
from sqlalchemy.orm import Session

from app.models.publication import Publication


class PublicationRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, publication: Publication) -> Publication:
        self.db.add(publication)
        self.db.commit()
        self.db.refresh(publication)
        return publication

    def get_by_id(self, publication_id: int, user_id: int) -> Publication | None:
        return (
            self.db.query(Publication)
            .filter(Publication.id == publication_id, Publication.user_id == user_id)
            .first()
        )

    def get_all(self, user_id: int) -> list[Publication]:
        return (
            self.db.query(Publication)
            .filter(Publication.user_id == user_id)
            .order_by(Publication.created_at.desc())
            .all()
        )

    def get_by_post_id(self, post_id: int, user_id: int) -> list[Publication]:
        return (
            self.db.query(Publication)
            .filter(Publication.post_id == post_id, Publication.user_id == user_id)
            .all()
        )

    def get_due_publications(self, now: datetime, limit: int = 50) -> list[Publication]:
        return (
            self.db.query(Publication)
            .filter(
                Publication.status == "scheduled",
                Publication.scheduled_at <= now
            )
            .limit(limit)
            .all()
        )

    def update(self, publication: Publication) -> Publication:
        self.db.commit()
        self.db.refresh(publication)
        return publication

    def delete(self, publication: Publication) -> None:
        self.db.delete(publication)
        self.db.commit()
