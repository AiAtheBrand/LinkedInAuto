from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.repositories.learning import LearningRepository
from app.schemas.learning import LearningCreate, LearningResponse
from app.services.learning import LearningService

router = APIRouter(
    prefix="/learning",
    tags=["Learning"]
)


@router.post("/", response_model=LearningResponse)
def create_learning(
    data: LearningCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repository = LearningRepository(db)
    service = LearningService(repository)
    return service.create_learning(current_user.id, data)


@router.get("/", response_model=list[LearningResponse])
def get_learning(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repository = LearningRepository(db)
    service = LearningService(repository)
    return service.get_all_learning(current_user.id)


@router.get("/{learning_id}", response_model=LearningResponse)
def get_learning_by_id(
    learning_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repository = LearningRepository(db)
    service = LearningService(repository)
    learning = service.get_learning(current_user.id, learning_id)
    if not learning:
        raise HTTPException(
            status_code=404,
            detail="Learning entry not found"
        )
    return learning


@router.put("/{learning_id}", response_model=LearningResponse)
def update_learning(
    learning_id: int,
    data: LearningCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repository = LearningRepository(db)
    service = LearningService(repository)
    learning = service.update_learning(current_user.id, learning_id, data)
    if not learning:
        raise HTTPException(
            status_code=404,
            detail="Learning entry not found"
        )
    return learning


@router.delete("/{learning_id}")
def delete_learning(
    learning_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    repository = LearningRepository(db)
    service = LearningService(repository)
    deleted = service.delete_learning(current_user.id, learning_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Learning entry not found"
        )
    return {
        "message": "Learning entry deleted successfully"
    }
