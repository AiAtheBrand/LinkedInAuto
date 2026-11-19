from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.oauth_state import OAuthState


class OAuthStateRepository:

    def __init__(self, db: Session):
        self.db = db

    def create(self, oauth_state: OAuthState) -> OAuthState:
        self.db.add(oauth_state)
        self.db.commit()
        self.db.refresh(oauth_state)
        return oauth_state

    def get_valid_state(self, state_str: str, user_id: int) -> OAuthState | None:
        now = datetime.now(timezone.utc)
        return (
            self.db.query(OAuthState)
            .filter(
                OAuthState.state == state_str,
                OAuthState.user_id == user_id,
                OAuthState.used.is_(False),
                OAuthState.expires_at > now
            )
            .first()
        )

    def get_valid_state_by_token(self, state_str: str) -> OAuthState | None:
        now = datetime.now(timezone.utc)
        return (
            self.db.query(OAuthState)
            .filter(
                OAuthState.state == state_str,
                OAuthState.used.is_(False),
                OAuthState.expires_at > now
            )
            .first()
        )

    def mark_as_used(self, oauth_state: OAuthState) -> None:
        oauth_state.used = True
        self.db.commit()
        self.db.refresh(oauth_state)
