from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.repositories.linkedin_account import LinkedInAccountRepository
from app.repositories.oauth_state import OAuthStateRepository
from app.schemas.linkedin import (
    LinkedInAccountResponse,
    OAuthCallbackRequest,
    OAuthUrlResponse,
)
from app.services.linkedin import LinkedInService

router = APIRouter(prefix="/linkedin", tags=["LinkedIn Integration"])


@router.get("/oauth/authorize", response_model=OAuthUrlResponse)
def get_oauth_authorize_url(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account_repo = LinkedInAccountRepository(db)
    state_repo = OAuthStateRepository(db)
    service = LinkedInService(account_repo, state_repo)

    auth_url, state = service.generate_authorization_url(current_user.id)
    return OAuthUrlResponse(authorization_url=auth_url, state=state)


@router.get("/oauth/callback", response_class=HTMLResponse)
def oauth_callback_browser(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    account_repo = LinkedInAccountRepository(db)
    state_repo = OAuthStateRepository(db)
    service = LinkedInService(account_repo, state_repo)

    valid_state = state_repo.get_valid_state_by_token(state)
    if not valid_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid, expired, or already-used OAuth state."
        )

    try:
        account = service.connect_account_from_callback(
            user_id=valid_state.user_id,
            code=code,
            state=state
        )
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>LinkedIn Connected</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f3f2ef; }}
                .card {{ background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); text-align: center; max-width: 420px; }}
                h2 {{ color: #0a66c2; margin-top: 0; }}
                p {{ color: #555; line-height: 1.5; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>Account Connected!</h2>
                <p>Successfully connected LinkedIn account: <strong>{account.name}</strong>.</p>
                <p>You can close this browser tab and return to the application.</p>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LinkedIn integration failure: {str(e)}"
        )


@router.post("/oauth/callback", response_model=LinkedInAccountResponse)
def oauth_callback(
    data: OAuthCallbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account_repo = LinkedInAccountRepository(db)
    state_repo = OAuthStateRepository(db)
    service = LinkedInService(account_repo, state_repo)

    try:
        account = service.connect_account_from_callback(
            user_id=current_user.id,
            code=data.code,
            state=data.state
        )
        return account
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LinkedIn integration failure: {str(e)}"
        )


@router.get("/accounts", response_model=list[LinkedInAccountResponse])
def get_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account_repo = LinkedInAccountRepository(db)
    state_repo = OAuthStateRepository(db)
    service = LinkedInService(account_repo, state_repo)
    return service.get_accounts(current_user.id)


@router.delete("/accounts/{account_id}")
def disconnect_account(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    account_repo = LinkedInAccountRepository(db)
    state_repo = OAuthStateRepository(db)
    service = LinkedInService(account_repo, state_repo)

    disconnected = service.disconnect_account(current_user.id, account_id)
    if not disconnected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LinkedIn account connection not found"
        )
    return {"message": "LinkedIn account disconnected successfully"}
