from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.repositories.learning import LearningRepository
from app.repositories.post import PostRepository
from app.schemas.post import PostResponse, PostUpdate
from app.services.media_service import MediaService, MediaValidationError
from app.services.post import PostService

router = APIRouter(prefix="/posts", tags=["Posts"])


@router.post(
    "/generate/{learning_id}",
    response_model=PostResponse
)
def generate_post(
    learning_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post_repository = PostRepository(db)
    learning_repository = LearningRepository(db)
    service = PostService(post_repository, learning_repository)
    post = service.generate_post(current_user.id, learning_id)
    if not post:
        raise HTTPException(
            status_code=404,
            detail="Learning entry not found"
        )
    return post


@router.get("/", response_model=list[PostResponse])
def get_all_posts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post_repository = PostRepository(db)
    learning_repository = LearningRepository(db)
    service = PostService(post_repository, learning_repository)
    return service.get_all_posts(current_user.id)


@router.get("/{post_id}", response_model=PostResponse)
def get_post_by_id(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post_repository = PostRepository(db)
    learning_repository = LearningRepository(db)
    service = PostService(post_repository, learning_repository)
    post = service.get_post(current_user.id, post_id)
    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )
    return post


@router.put("/{post_id}", response_model=PostResponse)
def update_post(
    post_id: int,
    data: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post_repository = PostRepository(db)
    learning_repository = LearningRepository(db)
    service = PostService(post_repository, learning_repository)
    post = service.update_post(current_user.id, post_id, data.content, data.image_url)
    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )
    return post


@router.post("/{post_id}/image", response_model=PostResponse)
def upload_post_image(
    post_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post_repository = PostRepository(db)
    learning_repository = LearningRepository(db)
    service = PostService(post_repository, learning_repository)

    post = service.get_post(current_user.id, post_id)
    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    file_bytes = file.file.read()
    media_service = MediaService()
    try:
        relative_url, _ = media_service.validate_and_save_image(
            file_bytes=file_bytes,
            filename=file.filename or "image.png",
            content_type=file.content_type
        )
    except MediaValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    updated = service.attach_image_to_post(current_user.id, post_id, relative_url)
    return updated


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post_repository = PostRepository(db)
    learning_repository = LearningRepository(db)
    service = PostService(post_repository, learning_repository)
    deleted = service.delete_post(current_user.id, post_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )
    return {
        "message": "Post deleted successfully"
    }


@router.get("/health/status")
def health_status():
    return {
        "status": "healthy"
    }
