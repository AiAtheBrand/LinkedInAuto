import os
from datetime import datetime, timezone

from app.core.security import decrypt_token
from app.models.publication import Publication
from app.repositories.linkedin_account import LinkedInAccountRepository
from app.repositories.post import PostRepository
from app.repositories.publication import PublicationRepository
from app.repositories.social_account import SocialAccountRepository
from app.schemas.social import PlatformDestination
from app.services.linkedin_client import LinkedInClient, LinkedInAPIError
from app.services.meta_client import MetaClient, MetaAPIError


class PublicationService:

    def __init__(
        self,
        publication_repo: PublicationRepository,
        post_repo: PostRepository,
        account_repo: LinkedInAccountRepository,
        linkedin_client: LinkedInClient | None = None,
        social_account_repo: SocialAccountRepository | None = None,
        meta_client: MetaClient | None = None
    ):
        self.publication_repo = publication_repo
        self.post_repo = post_repo
        self.account_repo = account_repo
        self.linkedin_client = linkedin_client or LinkedInClient()
        self.social_account_repo = social_account_repo
        self.meta_client = meta_client or MetaClient()

    def _resolve_media_bytes(self, post) -> bytes | None:
        """Reads local post image file bytes if image_url is present."""
        if not post.image_url:
            return None

        clean_path = post.image_url.lstrip("/")
        proj_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        disk_path = os.path.join(proj_root, clean_path)

        if not os.path.exists(disk_path):
            return None

        with open(disk_path, "rb") as f:
            return f.read()

    def _resolve_media_urn(self, post, access_token: str, author_urn: str) -> str | None:
        """Reads local post image file and uploads to LinkedIn if image_url is present."""
        file_bytes = self._resolve_media_bytes(post)
        if not file_bytes:
            return None

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
            platform="linkedin",
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
            pub.remote_post_id = pub.linkedin_post_urn
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

    def publish_multi_destinations(
        self,
        user_id: int,
        post_id: int,
        destinations: list[PlatformDestination]
    ) -> list[Publication]:
        """
        Publishes a single post to multiple chosen platforms (LinkedIn, Facebook, Instagram)
        with destination-specific validation and isolated publication tracking.
        """
        if not destinations:
            raise ValueError("Please select at least one destination platform to publish to.")

        post = self.post_repo.get_by_id(post_id, user_id)
        if not post:
            raise ValueError("Draft post not found or not owned by user.")

        clean_content = post.content.strip() if post.content else ""
        if not clean_content:
            raise ValueError("Cannot publish an empty post.")

        # Pre-validate platform constraints across all selected destinations
        for dest in destinations:
            if dest.platform == "instagram":
                if not post.image_url:
                    raise ValueError(
                        "Instagram requires an image attachment to publish. "
                        "Please attach an image to your post first, or uncheck Instagram."
                    )
                if len(clean_content) > 2200:
                    raise ValueError(
                        f"Post length ({len(clean_content)} chars) exceeds Instagram's limit of 2,200 characters."
                    )
            elif dest.platform == "linkedin":
                if len(clean_content) > 3000:
                    raise ValueError(
                        f"Post length ({len(clean_content)} chars) exceeds LinkedIn's limit of 3,000 characters."
                    )

        results: list[Publication] = []
        any_success = False

        for dest in destinations:
            if dest.platform == "linkedin":
                account = self.account_repo.get_by_id(dest.account_id, user_id)
                if not account:
                    raise ValueError(f"LinkedIn account (ID {dest.account_id}) not found or not owned by user.")

                pub = Publication(
                    user_id=user_id,
                    post_id=post.id,
                    platform="linkedin",
                    linkedin_account_id=account.id,
                    status="processing",
                    attempt_count=1
                )
                pub = self.publication_repo.create(pub)

                access_token = decrypt_token(account.encrypted_access_token)
                if not access_token:
                    pub.status = "failed"
                    pub.error_message = "Failed to decrypt LinkedIn access token; reauthorization required."
                    results.append(self.publication_repo.update(pub))
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
                    pub.remote_post_id = pub.linkedin_post_urn
                    pub.published_at = datetime.now(timezone.utc)
                    pub.error_message = None
                    any_success = True
                except Exception as exc:
                    pub.status = "failed"
                    pub.error_message = f"LinkedIn publish failed: {str(exc)}"

                results.append(self.publication_repo.update(pub))

            elif dest.platform == "facebook":
                if not self.social_account_repo:
                    raise ValueError("Social account repository is required for Facebook publication.")

                account = self.social_account_repo.get_by_id(dest.account_id, user_id)
                if not account or account.platform != "facebook":
                    raise ValueError(f"Facebook account (ID {dest.account_id}) not found or not owned by user.")

                pub = Publication(
                    user_id=user_id,
                    post_id=post.id,
                    platform="facebook",
                    social_account_id=account.id,
                    status="processing",
                    attempt_count=1
                )
                pub = self.publication_repo.create(pub)

                access_token = decrypt_token(account.encrypted_access_token)
                if not access_token:
                    pub.status = "failed"
                    pub.error_message = "Failed to decrypt Facebook access token."
                    results.append(self.publication_repo.update(pub))
                    continue

                image_bytes = self._resolve_media_bytes(post)
                try:
                    res = self.meta_client.publish_facebook(
                        access_token=access_token,
                        page_id=account.account_identifier,
                        message=post.content,
                        image_bytes=image_bytes
                    )
                    pub.status = "published"
                    pub.remote_post_id = res.get("id") or res.get("post_id")
                    pub.published_at = datetime.now(timezone.utc)
                    pub.error_message = None
                    any_success = True
                except Exception as exc:
                    pub.status = "failed"
                    pub.error_message = f"Facebook publish failed: {str(exc)}"

                results.append(self.publication_repo.update(pub))

            elif dest.platform == "instagram":
                if not self.social_account_repo:
                    raise ValueError("Social account repository is required for Instagram publication.")

                account = self.social_account_repo.get_by_id(dest.account_id, user_id)
                if not account or account.platform != "instagram":
                    raise ValueError(f"Instagram account (ID {dest.account_id}) not found or not owned by user.")

                pub = Publication(
                    user_id=user_id,
                    post_id=post.id,
                    platform="instagram",
                    social_account_id=account.id,
                    status="processing",
                    attempt_count=1
                )
                pub = self.publication_repo.create(pub)

                access_token = decrypt_token(account.encrypted_access_token)
                if not access_token:
                    pub.status = "failed"
                    pub.error_message = "Failed to decrypt Instagram access token."
                    results.append(self.publication_repo.update(pub))
                    continue

                image_bytes = self._resolve_media_bytes(post)
                try:
                    res = self.meta_client.publish_instagram(
                        access_token=access_token,
                        ig_user_id=account.account_identifier,
                        caption=post.content,
                        image_bytes=image_bytes,
                        image_url=post.image_url
                    )
                    pub.status = "published"
                    pub.remote_post_id = res.get("id")
                    pub.published_at = datetime.now(timezone.utc)
                    pub.error_message = None
                    any_success = True
                except Exception as exc:
                    pub.status = "failed"
                    pub.error_message = f"Instagram publish failed: {str(exc)}"

                results.append(self.publication_repo.update(pub))

        if any_success:
            post.status = "published"
            self.post_repo.update(post)

        return results

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
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

        if scheduled_at <= now:
            raise ValueError("Scheduled time must be in the future.")

        pub = Publication(
            user_id=user_id,
            post_id=post.id,
            platform="linkedin",
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
            pub.status = "processing"
            pub.attempt_count += 1
            self.publication_repo.update(pub)

            account = self.account_repo.get_by_id(pub.linkedin_account_id, pub.user_id) if pub.linkedin_account_id else None
            post = self.post_repo.get_by_id(pub.post_id, pub.user_id)

            if not account or not post:
                pub.status = "failed"
                pub.error_message = "Linked post or account missing."
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
                pub.remote_post_id = pub.linkedin_post_urn
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
