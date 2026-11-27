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
    try:
        post = service.generate_post(current_user.id, learning_id)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"AI post generation failed: {str(exc)}"
        )

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
    post = service.update_post(
        user_id=current_user.id,
        post_id=post_id,
        content=data.content,
        image_url=data.image_url,
        image_urls=data.image_urls
    )
    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )
    return post


@router.post("/{post_id}/images", response_model=PostResponse)
def upload_post_images(
    post_id: int,
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Uploads one or multiple images and attaches them to the post."""
    post_repository = PostRepository(db)
    learning_repository = LearningRepository(db)
    service = PostService(post_repository, learning_repository)

    post = service.get_post(current_user.id, post_id)
    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files provided for upload."
        )

    media_service = MediaService()
    saved_urls: list[str] = []

    for f in files:
        file_bytes = f.file.read()
        try:
            relative_url, _ = media_service.validate_and_save_image(
                file_bytes=file_bytes,
                filename=f.filename or "image.png",
                content_type=f.content_type
            )
            saved_urls.append(relative_url)
        except MediaValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Image upload validation failed for '{f.filename}': {str(e)}"
            )

    updated = service.attach_images_to_post(current_user.id, post_id, saved_urls)
    return updated


@router.post("/{post_id}/image", response_model=PostResponse)
def upload_post_image(
    post_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Backwards-compatible single-image upload endpoint."""
    return upload_post_images(
        post_id=post_id,
        files=[file],
        current_user=current_user,
        db=db
    )


@router.delete("/{post_id}/images/{image_index}", response_model=PostResponse)
def delete_post_image(
    post_id: int,
    image_index: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes an attached image by its zero-based index."""
    post_repository = PostRepository(db)
    learning_repository = LearningRepository(db)
    service = PostService(post_repository, learning_repository)

    updated = service.delete_post_image(current_user.id, post_id, image_index)
    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Post or image index not found."
        )
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
