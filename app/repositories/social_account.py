from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.social_account import SocialAccount


class SocialAccountRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, account: SocialAccount) -> SocialAccount:
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def get_by_id(self, account_id: int, user_id: int) -> SocialAccount | None:
        stmt = select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.user_id == user_id
        )
        return self.db.scalars(stmt).first()

    def get_all(self, user_id: int, platform: str | None = None) -> list[SocialAccount]:
        stmt = select(SocialAccount).where(SocialAccount.user_id == user_id)
        if platform:
            stmt = stmt.where(SocialAccount.platform == platform)
        stmt = stmt.order_by(SocialAccount.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def delete(self, account: SocialAccount) -> None:
        self.db.delete(account)
        self.db.commit()
