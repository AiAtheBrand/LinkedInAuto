from sqlalchemy.orm import Session

from app.models.linkedin_account import LinkedInAccount


class LinkedInAccountRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, account: LinkedInAccount) -> LinkedInAccount:
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def get_by_id(self, account_id: int, user_id: int) -> LinkedInAccount | None:
        return (
            self.db.query(LinkedInAccount)
            .filter(LinkedInAccount.id == account_id, LinkedInAccount.user_id == user_id)
            .first()
        )

    def get_by_member_urn(self, user_id: int, member_urn: str) -> LinkedInAccount | None:
        return (
            self.db.query(LinkedInAccount)
            .filter(LinkedInAccount.user_id == user_id, LinkedInAccount.linkedin_member_urn == member_urn)
            .first()
        )

    def get_all(self, user_id: int) -> list[LinkedInAccount]:
        return (
            self.db.query(LinkedInAccount)
            .filter(LinkedInAccount.user_id == user_id)
            .all()
        )

    def update(self, account: LinkedInAccount) -> LinkedInAccount:
        self.db.commit()
        self.db.refresh(account)
        return account

    def delete(self, account: LinkedInAccount) -> None:
        self.db.delete(account)
        self.db.commit()
