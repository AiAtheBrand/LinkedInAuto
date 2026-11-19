from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserRegister


class UserService:

    def __init__(self, repository: UserRepository):
        self.repository = repository

    def register_user(self, data: UserRegister) -> User:
        normalized_email = data.email.strip().lower()
        existing = self.repository.get_by_email(normalized_email)
        if existing:
            raise ValueError("Email already registered")

        hashed_pwd = hash_password(data.password)
        user = User(
            email=normalized_email,
            hashed_password=hashed_pwd,
            full_name=data.full_name
        )
        return self.repository.create(user)

    def authenticate_user(self, email: str, password: str) -> User | None:
        normalized_email = email.strip().lower()
        user = self.repository.get_by_email(normalized_email)
        if not user or not user.is_active:
            return None

        if not verify_password(password, user.hashed_password):
            return None

        return user

    def create_token_for_user(self, user: User) -> str:
        return create_access_token({
            "sub": user.id,
            "email": user.email
        })
