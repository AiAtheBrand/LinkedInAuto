from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.repositories.social_account import SocialAccountRepository
from app.schemas.social import SocialAccountCreate, SocialAccountResponse
from app.services.social_service import SocialAccountService

router = APIRouter(prefix="/social", tags=["Social Media Integration"])


@router.post("/accounts", response_model=SocialAccountResponse, status_code=status.HTTP_201_CREATED)
def connect_social_account(
    data: SocialAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = SocialAccountRepository(db)
    service = SocialAccountService(repo)
    try:
        account = service.connect_account(current_user.id, data)
        return account
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/accounts", response_model=list[SocialAccountResponse])
def get_social_accounts(
    platform: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = SocialAccountRepository(db)
    service = SocialAccountService(repo)
    return service.get_accounts(current_user.id, platform=platform)


@router.delete("/accounts/{account_id}")
def disconnect_social_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repo = SocialAccountRepository(db)
    service = SocialAccountService(repo)
    success = service.disconnect_account(current_user.id, account_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found"
        )
    return {"message": "Account disconnected successfully"}
