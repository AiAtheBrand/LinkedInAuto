import os
from datetime import datetime, timezone

from app.core.security import decrypt_token
from app.models.publication import Publication
from app.repositories.linkedin_account import LinkedInAccountRepository
from app.repositories.post import PostRepository
from app.repositories.publication import PublicationRepository
from app.services.linkedin_client import LinkedInClient, LinkedInAPIError


class PublicationService:

    def __init__(
        self,
        publication_repo: PublicationRepository,
        post_repo: PostRepository,
        account_repo: LinkedInAccountRepository,
        linkedin_client: LinkedInClient | None = None
    ):
        self.publication_repo = publication_repo
        self.post_repo = post_repo
        self.account_repo = account_repo
        self.linkedin_client = linkedin_client or LinkedInClient()

    def _resolve_media_urn(self, post, access_token: str, author_urn: str) -> str | None:
        """Reads local post image file and uploads to LinkedIn if image_url is present."""
        if not post.image_url:
            return None

        clean_path = post.image_url.lstrip("/")
        proj_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        disk_path = os.path.join(proj_root, clean_path)

        if not os.path.exists(disk_path):
            return None

        with open(disk_path, "rb") as f:
            file_bytes = f.read()

        return self.linkedin_client.upload_image(
            access_token=access_token,
            author_urn=author_urn,
            file_bytes=file_bytes
        )

    def publish_post(
        self,
        user_id: int,
        post_id: int,
        linkedin_account_id: int
    ) -> Publication:
        # Verify ownership of post
        post = self.post_repo.get_by_id(post_id, user_id)
        if not post:
            raise ValueError("Draft post not found or not owned by user.")

        # Verify ownership of destination LinkedIn account
        account = self.account_repo.get_by_id(linkedin_account_id, user_id)
        if not account:
            raise ValueError("LinkedIn destination account not found or not owned by user.")

        # Create publication record in processing status
        pub = Publication(
            user_id=user_id,
            post_id=post.id,
            linkedin_account_id=account.id,
            status="processing",
            attempt_count=1
        )
        pub = self.publication_repo.create(pub)

        # Decrypt token
        access_token = decrypt_token(account.encrypted_access_token)
        if not access_token:
            pub.status = "failed"
            pub.error_message = "Failed to decrypt LinkedIn access token; reauthorization required."
            return self.publication_repo.update(pub)

        try:
            media_urn = self._resolve_media_urn(post, access_token, account.linkedin_member_urn)
            if media_urn:
                result = self.linkedin_client.create_post(
                    access_token=access_token,
                    author_urn=account.linkedin_member_urn,
                    commentary=post.content,
                    media_urn=media_urn
                )
            else:
                result = self.linkedin_client.create_text_post(
                    access_token=access_token,
                    author_urn=account.linkedin_member_urn,
                    commentary=post.content
                )
            pub.status = "published"
            pub.linkedin_post_urn = result.get("urn") or result.get("id")
            pub.published_at = datetime.now(timezone.utc)
            pub.error_message = None

            # Update parent post status to reflect at least one published destination
            post.status = "published"
            self.post_repo.update(post)

        except LinkedInAPIError as exc:
            pub.status = "failed"
            pub.error_message = f"LinkedIn API error ({exc.status_code}): {str(exc)}"
        except Exception as exc:
            pub.status = "failed"
            pub.error_message = f"Unexpected publication failure: {str(exc)}"

        return self.publication_repo.update(pub)

    def schedule_post(
        self,
        user_id: int,
        post_id: int,
        linkedin_account_id: int,
        scheduled_at: datetime
    ) -> Publication:
        # Verify ownership of post
        post = self.post_repo.get_by_id(post_id, user_id)
        if not post:
            raise ValueError("Draft post not found or not owned by user.")

        # Verify ownership of account
        account = self.account_repo.get_by_id(linkedin_account_id, user_id)
        if not account:
            raise ValueError("LinkedIn destination account not found or not owned by user.")

        # Validate future scheduled time
        now = datetime.now(timezone.utc)
        # Handle naive datetime by assuming UTC if no tzinfo
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

        if scheduled_at <= now:
            raise ValueError("Scheduled time must be in the future.")

        pub = Publication(
            user_id=user_id,
            post_id=post.id,
            linkedin_account_id=account.id,
            status="scheduled",
            scheduled_at=scheduled_at
        )
        post.status = "scheduled"
        self.post_repo.update(post)
        return self.publication_repo.create(pub)

    def get_user_publications(self, user_id: int) -> list[Publication]:
        return self.publication_repo.get_all(user_id)

    def get_publication(self, user_id: int, publication_id: int) -> Publication | None:
        return self.publication_repo.get_by_id(publication_id, user_id)

    def process_due_publications(self, now: datetime | None = None) -> list[Publication]:
        """Claims and executes due scheduled publications atomically."""
        if now is None:
            now = datetime.now(timezone.utc)

        due_items = self.publication_repo.get_due_publications(now)
        results = []

        for pub in due_items:
            # Atomic state transition from scheduled -> processing
            pub.status = "processing"
            pub.attempt_count += 1
            self.publication_repo.update(pub)

            # Retrieve account and post
            account = self.account_repo.get_by_id(pub.linkedin_account_id, pub.user_id)
            post = self.post_repo.get_by_id(pub.post_id, pub.user_id)

            if not account or not post:
                pub.status = "failed"
                pub.error_message = "Linked post or LinkedIn account missing."
                self.publication_repo.update(pub)
                results.append(pub)
                continue

            access_token = decrypt_token(account.encrypted_access_token)
            if not access_token:
                pub.status = "failed"
                pub.error_message = "Access token decryption failed."
                self.publication_repo.update(pub)
                results.append(pub)
                continue

            try:
                media_urn = self._resolve_media_urn(post, access_token, account.linkedin_member_urn)
                if media_urn:
                    res = self.linkedin_client.create_post(
                        access_token=access_token,
                        author_urn=account.linkedin_member_urn,
                        commentary=post.content,
                        media_urn=media_urn
                    )
                else:
                    res = self.linkedin_client.create_text_post(
                        access_token=access_token,
                        author_urn=account.linkedin_member_urn,
                        commentary=post.content
                    )
                pub.status = "published"
                pub.linkedin_post_urn = res.get("urn") or res.get("id")
                pub.published_at = datetime.now(timezone.utc)
                pub.error_message = None

                post.status = "published"
                self.post_repo.update(post)
            except Exception as exc:
                pub.status = "failed"
                pub.error_message = f"Execution error: {str(exc)}"

            self.publication_repo.update(pub)
            results.append(pub)

        return results
