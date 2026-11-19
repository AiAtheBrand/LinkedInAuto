import os
import urllib.parse
from typing import Any

import httpx

LINKEDIN_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
LINKEDIN_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
LINKEDIN_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
LINKEDIN_POSTS_URL = "https://api.linkedin.com/rest/posts"
LINKEDIN_IMAGES_URL = "https://api.linkedin.com/rest/images?action=initializeUpload"
# Use the env var if set; fall back to a known-active version.
# LinkedIn REST API versions use YYYYMM format; versions < ~202501 are sunset.
LINKEDIN_API_VERSION = os.getenv("LINKEDIN_API_VERSION", "202604")


class LinkedInAPIError(Exception):
    def __init__(self, message: str, status_code: int | None = None, response_body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class LinkedInClient:

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None
    ):
        self.client_id = client_id or os.getenv("LINKEDIN_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("LINKEDIN_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri or os.getenv("LINKEDIN_REDIRECT_URI", "http://127.0.0.1:8000/linkedin/oauth/callback")

    def build_authorization_url(self, state: str, scopes: list[str] | None = None) -> str:
        if scopes is None:
            scopes = ["openid", "profile", "email", "w_member_social"]
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
            "scope": " ".join(scopes),
        }
        return f"{LINKEDIN_AUTH_URL}?{urllib.parse.urlencode(params)}"

    def exchange_code_for_token(self, code: str) -> dict:
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(LINKEDIN_TOKEN_URL, data=data, headers=headers)
                if response.status_code != 200:
                    raise LinkedInAPIError(
                        f"LinkedIn token exchange failed: {response.text}",
                        status_code=response.status_code,
                        response_body=response.text
                    )
                return response.json()
        except httpx.RequestError as exc:
            raise LinkedInAPIError(f"Network error during LinkedIn token exchange: {str(exc)}")

    def get_user_profile(self, access_token: str) -> dict:
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(LINKEDIN_USERINFO_URL, headers=headers)
                if response.status_code != 200:
                    raise LinkedInAPIError(
                        f"LinkedIn profile fetch failed: {response.text}",
                        status_code=response.status_code,
                        response_body=response.text
                    )
                return response.json()
        except httpx.RequestError as exc:
            raise LinkedInAPIError(f"Network error fetching LinkedIn profile: {str(exc)}")

    def upload_image(self, access_token: str, author_urn: str, file_bytes: bytes) -> str:
        """Initializes image upload with LinkedIn REST API, uploads bytes, and returns remote image URN."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": LINKEDIN_API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json"
        }
        init_body = {
            "initializeUploadRequest": {
                "owner": author_urn
            }
        }
        try:
            with httpx.Client(timeout=30.0) as client:
                init_res = client.post(LINKEDIN_IMAGES_URL, json=init_body, headers=headers)
                if init_res.status_code not in (200, 201):
                    raise LinkedInAPIError(
                        f"Failed to initialize image upload: {init_res.text}",
                        status_code=init_res.status_code,
                        response_body=init_res.text
                    )
                init_data = init_res.json().get("value", {})
                upload_url = init_data.get("uploadUrl")
                image_urn = init_data.get("image")

                if not upload_url or not image_urn:
                    raise LinkedInAPIError("LinkedIn did not return uploadUrl or image URN.")

                # Upload binary bytes
                put_headers = {"Authorization": f"Bearer {access_token}"}
                put_res = client.put(upload_url, content=file_bytes, headers=put_headers)
                if put_res.status_code not in (200, 201):
                    raise LinkedInAPIError(
                        f"Failed to upload image binary: {put_res.text}",
                        status_code=put_res.status_code,
                        response_body=put_res.text
                    )
                return image_urn
        except httpx.RequestError as exc:
            raise LinkedInAPIError(f"Network error uploading image to LinkedIn: {str(exc)}")

    def create_post(
        self,
        access_token: str,
        author_urn: str,
        commentary: str,
        media_urn: str | None = None
    ) -> dict:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": LINKEDIN_API_VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "author": author_urn,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }

        if media_urn:
            payload["content"] = {
                "media": {
                    "id": media_urn,
                    "title": "Attached Image"
                }
            }

        try:
            with httpx.Client(timeout=20.0) as client:
                response = client.post(LINKEDIN_POSTS_URL, json=payload, headers=headers)
                if response.status_code not in (200, 201):
                    raise LinkedInAPIError(
                        f"LinkedIn post publishing failed: {response.text}",
                        status_code=response.status_code,
                        response_body=response.text
                    )
                post_urn = response.headers.get("x-restli-id") or response.headers.get("x-linkedin-id")
                result = response.json() if response.text else {}
                if post_urn:
                    result["urn"] = post_urn
                return result
        except httpx.RequestError as exc:
            raise LinkedInAPIError(f"Network error publishing LinkedIn post: {str(exc)}")

    def create_text_post(self, access_token: str, author_urn: str, commentary: str) -> dict:
        """Alias for create_post for text-only posts."""
        return self.create_post(access_token=access_token, author_urn=author_urn, commentary=commentary)
