import logging
import httpx

logger = logging.getLogger(__name__)


class MetaAPIError(Exception):
    def __init__(self, message: str, status_code: int = 500, response_data: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data or {}


class MetaClient:
    """Official Meta Graph API client for Facebook and Instagram publishing."""

    GRAPH_API_BASE = "https://graph.facebook.com/v19.0"

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=30.0)

    def publish_facebook(
        self,
        access_token: str,
        page_id: str,
        message: str,
        image_bytes: bytes | None = None
    ) -> dict:
        """
        Publishes a message or photo post to a Facebook Page via Graph API.
        """
        if not message or not message.strip():
            raise ValueError("Facebook post content cannot be blank.")

        # If image is attached, publish to /{page_id}/photos endpoint
        if image_bytes:
            endpoint = f"{self.GRAPH_API_BASE}/{page_id}/photos"
            data = {"caption": message, "access_token": access_token}
            files = {"source": ("post_image.jpg", image_bytes, "image/jpeg")}
            try:
                response = self.client.post(endpoint, data=data, files=files)
            except Exception as e:
                raise MetaAPIError(f"Network error publishing to Facebook: {str(e)}")
        else:
            endpoint = f"{self.GRAPH_API_BASE}/{page_id}/feed"
            json_payload = {
                "message": message,
                "access_token": access_token
            }
            try:
                response = self.client.post(endpoint, data=json_payload)
            except Exception as e:
                raise MetaAPIError(f"Network error publishing to Facebook: {str(e)}")

        if response.status_code not in (200, 201):
            try:
                err_body = response.json()
            except Exception:
                err_body = {"raw": response.text}
            error_msg = err_body.get("error", {}).get("message", response.text)
            raise MetaAPIError(f"Facebook API error ({response.status_code}): {error_msg}", status_code=response.status_code, response_data=err_body)

        return response.json()

    def publish_instagram(
        self,
        access_token: str,
        ig_user_id: str,
        caption: str,
        image_bytes: bytes | None = None,
        image_url: str | None = None
    ) -> dict:
        """
        Publishes an Instagram post via Instagram Graph API Content Publishing.
        Note: Instagram Graph API strictly requires media (image or video) for feed posts.
        """
        if not image_bytes and not image_url:
            raise ValueError("Instagram requires an image attachment to publish. Please attach an image.")

        if len(caption) > 2200:
            raise ValueError(f"Instagram caption exceeds maximum limit of 2,200 characters (length: {len(caption)}).")

        # Step 1: Create IG Container
        container_url = f"{self.GRAPH_API_BASE}/{ig_user_id}/media"
        params = {
            "caption": caption,
            "access_token": access_token
        }
        if image_url:
            params["image_url"] = image_url

        try:
            if image_bytes and not image_url:
                # If uploading direct media file
                files = {"image": ("instagram_media.jpg", image_bytes, "image/jpeg")}
                res_container = self.client.post(container_url, data=params, files=files)
            else:
                res_container = self.client.post(container_url, data=params)
        except Exception as e:
            raise MetaAPIError(f"Network error creating Instagram media container: {str(e)}")

        if res_container.status_code not in (200, 201):
            try:
                err_body = res_container.json()
            except Exception:
                err_body = {"raw": res_container.text}
            error_msg = err_body.get("error", {}).get("message", res_container.text)
            raise MetaAPIError(f"Instagram API container error ({res_container.status_code}): {error_msg}", status_code=res_container.status_code, response_data=err_body)

        container_id = res_container.json().get("id")

        # Step 2: Publish container
        publish_url = f"{self.GRAPH_API_BASE}/{ig_user_id}/media_publish"
        try:
            res_publish = self.client.post(publish_url, data={
                "creation_id": container_id,
                "access_token": access_token
            })
        except Exception as e:
            raise MetaAPIError(f"Network error publishing Instagram container: {str(e)}")

        if res_publish.status_code not in (200, 201):
            try:
                err_body = res_publish.json()
            except Exception:
                err_body = {"raw": res_publish.text}
            error_msg = err_body.get("error", {}).get("message", res_publish.text)
            raise MetaAPIError(f"Instagram publication error ({res_publish.status_code}): {error_msg}", status_code=res_publish.status_code, response_data=err_body)

        return res_publish.json()
