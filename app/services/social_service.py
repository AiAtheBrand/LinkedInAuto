from app.core.security import encrypt_token, decrypt_token
from app.models.social_account import SocialAccount
from app.repositories.social_account import SocialAccountRepository
from app.schemas.social import SocialAccountCreate


class SocialAccountService:

    def __init__(self, repository: SocialAccountRepository):
        self.repository = repository

    def connect_account(self, user_id: int, data: SocialAccountCreate) -> SocialAccount:
        # Encrypt access token at rest
        encrypted = encrypt_token(data.access_token)

        account = SocialAccount(
            user_id=user_id,
            platform=data.platform,
            name=data.name.strip(),
            account_identifier=data.account_identifier.strip(),
            email=data.email.strip().lower() if data.email else None,
            profile_picture_url=data.profile_picture_url,
            encrypted_access_token=encrypted
        )
        return self.repository.create(account)

    def get_accounts(self, user_id: int, platform: str | None = None) -> list[SocialAccount]:
        return self.repository.get_all(user_id, platform=platform)

    def get_account_by_id(self, account_id: int, user_id: int) -> SocialAccount | None:
        return self.repository.get_by_id(account_id, user_id)

    def disconnect_account(self, user_id: int, account_id: int) -> bool:
        account = self.repository.get_by_id(account_id, user_id)
        if not account:
            return False
        self.repository.delete(account)
        return True
