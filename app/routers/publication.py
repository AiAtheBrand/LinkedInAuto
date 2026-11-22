from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.repositories.linkedin_account import LinkedInAccountRepository
from app.repositories.post import PostRepository
from app.repositories.publication import PublicationRepository
from app.repositories.social_account import SocialAccountRepository
from app.schemas.linkedin import PublicationCreate, PublicationResponse
from app.schemas.social import MultiPublishRequest
from app.services.publication import PublicationService

router = APIRouter(prefix="/publications", tags=["Publications"])


@router.post("/publish", response_model=PublicationResponse)
def publish_post_now(
    data: PublicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pub_repo = PublicationRepository(db)
    post_repo = PostRepository(db)
    account_repo = LinkedInAccountRepository(db)
    social_repo = SocialAccountRepository(db)
    service = PublicationService(pub_repo, post_repo, account_repo, social_account_repo=social_repo)

    try:
        pub = service.publish_post(
            user_id=current_user.id,
            post_id=data.post_id,
            linkedin_account_id=data.linkedin_account_id
        )
        return pub
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/publish-multi", response_model=list[PublicationResponse])
def publish_multi_destinations(
    data: MultiPublishRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Publishes a post to one or more user-selected destination platforms (LinkedIn, Facebook, Instagram).
    """
    pub_repo = PublicationRepository(db)
    post_repo = PostRepository(db)
    account_repo = LinkedInAccountRepository(db)
    social_repo = SocialAccountRepository(db)
    service = PublicationService(pub_repo, post_repo, account_repo, social_account_repo=social_repo)

    try:
        pubs = service.publish_multi_destinations(
            user_id=current_user.id,
            post_id=data.post_id,
            destinations=data.destinations
        )
        return pubs
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/schedule", response_model=PublicationResponse)
def schedule_post_publication(
    data: PublicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not data.scheduled_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scheduled_at timestamp is required for scheduling."
        )

    pub_repo = PublicationRepository(db)
    post_repo = PostRepository(db)
    account_repo = LinkedInAccountRepository(db)
    social_repo = SocialAccountRepository(db)
    service = PublicationService(pub_repo, post_repo, account_repo, social_account_repo=social_repo)

    try:
        pub = service.schedule_post(
            user_id=current_user.id,
            post_id=data.post_id,
            linkedin_account_id=data.linkedin_account_id,
            scheduled_at=data.scheduled_at
        )
        return pub
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=list[PublicationResponse])
def get_user_publications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pub_repo = PublicationRepository(db)
    post_repo = PostRepository(db)
    account_repo = LinkedInAccountRepository(db)
    social_repo = SocialAccountRepository(db)
    service = PublicationService(pub_repo, post_repo, account_repo, social_account_repo=social_repo)
    return service.get_user_publications(current_user.id)


@router.get("/{publication_id}", response_model=PublicationResponse)
def get_publication_by_id(
    publication_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pub_repo = PublicationRepository(db)
    post_repo = PostRepository(db)
    account_repo = LinkedInAccountRepository(db)
    social_repo = SocialAccountRepository(db)
    service = PublicationService(pub_repo, post_repo, account_repo, social_account_repo=social_repo)

    pub = service.get_publication(current_user.id, publication_id)
    if not pub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publication record not found"
        )
    return pub
