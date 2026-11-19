import secrets
from datetime import datetime, timedelta, timezone

from app.core.security import encrypt_token, decrypt_token
from app.models.linkedin_account import LinkedInAccount
from app.models.oauth_state import OAuthState
from app.repositories.linkedin_account import LinkedInAccountRepository
from app.repositories.oauth_state import OAuthStateRepository
from app.services.linkedin_client import LinkedInClient, LinkedInAPIError


class LinkedInService:

    def __init__(
        self,
        account_repo: LinkedInAccountRepository,
        state_repo: OAuthStateRepository,
        client: LinkedInClient | None = None
    ):
        self.account_repo = account_repo
        self.state_repo = state_repo
        self.client = client or LinkedInClient()

    def generate_authorization_url(self, user_id: int) -> tuple[str, str]:
        """Generates a secure, user-bound, short-lived CSRF state and authorization URL."""
        state_token = secrets.token_hex(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

        oauth_state = OAuthState(
            state=state_token,
            user_id=user_id,
            expires_at=expires_at,
            used=False
        )
        self.state_repo.create(oauth_state)

        auth_url = self.client.build_authorization_url(state=state_token)
        return auth_url, state_token

    def connect_account_from_callback(
        self,
        user_id: int,
        code: str,
        state: str
    ) -> LinkedInAccount:
        """Validates OAuth state, exchanges code for access token, fetches profile, and stores encrypted credentials."""
        # 1. State validation (single-use, bound to user, unexpired)
        valid_state = self.state_repo.get_valid_state(state, user_id)
        if not valid_state:
            raise ValueError("Invalid, expired, or already-used OAuth state.")

        # Invalidate state immediately
        self.state_repo.mark_as_used(valid_state)

        # 2. Token exchange
        token_data = self.client.exchange_code_for_token(code)
        raw_access_token = token_data.get("access_token")
        if not raw_access_token:
            raise ValueError("No access token returned from LinkedIn.")

        expires_in = token_data.get("expires_in")
        token_expires_at = None
        if expires_in:
            token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

        scopes = token_data.get("scope", "w_member_social,openid,profile,email")

        # 3. Retrieve user profile
        profile = self.client.get_user_profile(raw_access_token)
        sub = profile.get("sub")
        if not sub:
            raise ValueError("LinkedIn profile response missing member identifier.")

        member_urn = f"urn:li:person:{sub}"
        name = profile.get("name", "LinkedIn Member")
        email = profile.get("email")
        picture = profile.get("picture")

        # 4. Encrypt access token at rest
        encrypted_token = encrypt_token(raw_access_token)

        # 5. Check if connection already exists for this user and member
        existing = self.account_repo.get_by_member_urn(user_id, member_urn)
        if existing:
            existing.name = name
            existing.email = email
            existing.profile_picture_url = picture
            existing.encrypted_access_token = encrypted_token
            existing.token_expires_at = token_expires_at
            existing.scopes = scopes
            return self.account_repo.update(existing)

        # Create new connection
        account = LinkedInAccount(
            user_id=user_id,
            linkedin_member_urn=member_urn,
            name=name,
            email=email,
            profile_picture_url=picture,
            encrypted_access_token=encrypted_token,
            token_expires_at=token_expires_at,
            scopes=scopes
        )
        return self.account_repo.create(account)

    def get_accounts(self, user_id: int) -> list[LinkedInAccount]:
        return self.account_repo.get_all(user_id)

    def disconnect_account(self, user_id: int, account_id: int) -> bool:
        account = self.account_repo.get_by_id(account_id, user_id)
        if not account:
            return False
        self.account_repo.delete(account)
        return True
