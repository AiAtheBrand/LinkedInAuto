from app.models.post import Post
from app.repositories.learning import LearningRepository
from app.repositories.post import PostRepository
from app.services.ai_service import AIService


class PostService:

    def __init__(
        self,
        post_repository: PostRepository,
        learning_repository: LearningRepository
    ):
        self.post_repository = post_repository
        self.learning_repository = learning_repository
        self.ai_service = AIService()

    def generate_post(self, user_id: int, learning_id: int) -> Post | None:
        # Cross-user isolation: user can only generate posts from their own learning items
        learning = self.learning_repository.get_by_id(learning_id, user_id)
        if not learning:
            return None

        content = self.ai_service.generate_linkedin_post(
            topic=learning.topic,
            category=learning.category,
            problem=learning.problem,
            what_i_learned=learning.what_i_learned,
            project=learning.project,
            lesson=learning.lesson
        )

        post = Post(
            user_id=user_id,
            learning_id=learning.id,
            content=content,
            status="draft"
        )
        return self.post_repository.create(post)

    def get_all_posts(self, user_id: int) -> list[Post]:
        return self.post_repository.get_all(user_id)

    def get_post(self, user_id: int, post_id: int) -> Post | None:
        return self.post_repository.get_by_id(post_id, user_id)

    def update_post(
        self,
        user_id: int,
        post_id: int,
        content: str,
        image_url: str | None = None,
        image_urls: list[str] | None = None
    ) -> Post | None:
        post = self.post_repository.get_by_id(post_id, user_id)
        if not post:
            return None

        post.content = content
        if image_urls is not None:
            post.set_image_urls(image_urls)
        elif image_url is not None:
            post.set_image_urls([image_url] if image_url != "" else [])

        return self.post_repository.update(post)

    def attach_image_to_post(self, user_id: int, post_id: int, image_url: str) -> Post | None:
        post = self.post_repository.get_by_id(post_id, user_id)
        if not post:
            return None

        images = post.get_image_urls()
        if image_url not in images:
            images.append(image_url)
        post.set_image_urls(images)
        return self.post_repository.update(post)

    def attach_images_to_post(self, user_id: int, post_id: int, new_image_urls: list[str]) -> Post | None:
        post = self.post_repository.get_by_id(post_id, user_id)
        if not post:
            return None

        images = post.get_image_urls()
        for url in new_image_urls:
            if url not in images:
                images.append(url)
        post.set_image_urls(images)
        return self.post_repository.update(post)

    def delete_post_image(self, user_id: int, post_id: int, image_index: int) -> Post | None:
        post = self.post_repository.get_by_id(post_id, user_id)
        if not post:
            return None

        images = post.get_image_urls()
        if 0 <= image_index < len(images):
            images.pop(image_index)
            post.set_image_urls(images)
            return self.post_repository.update(post)

        return None

    def delete_post(self, user_id: int, post_id: int) -> bool:
        post = self.post_repository.get_by_id(post_id, user_id)
        if not post:
            return False

        self.post_repository.delete(post)
        return True
