from app.models.learning import Learning
from app.repositories.learning import LearningRepository
from app.schemas.learning import LearningCreate


class LearningService:

    def __init__(self, repository: LearningRepository):
        self.repository = repository

    def create_learning(self, user_id: int, data: LearningCreate) -> Learning:
        learning = Learning(
            user_id=user_id,
            topic=data.topic,
            category=data.category,
            problem=data.problem,
            what_i_learned=data.what_i_learned,
            project=data.project,
            lesson=data.lesson
        )
        return self.repository.create(learning)

    def get_all_learning(self, user_id: int) -> list[Learning]:
        return self.repository.get_all(user_id)

    def get_learning(self, user_id: int, learning_id: int) -> Learning | None:
        return self.repository.get_by_id(learning_id, user_id)

    def update_learning(
        self,
        user_id: int,
        learning_id: int,
        data: LearningCreate
    ) -> Learning | None:
        learning = self.repository.get_by_id(learning_id, user_id)
        if not learning:
            return None

        learning.topic = data.topic
        learning.category = data.category
        learning.problem = data.problem
        learning.what_i_learned = data.what_i_learned
        learning.project = data.project
        learning.lesson = data.lesson

        return self.repository.update(learning)

    def delete_learning(self, user_id: int, learning_id: int) -> bool:
        learning = self.repository.get_by_id(learning_id, user_id)
        if not learning:
            return False

        self.repository.delete(learning)
        return True
