import logging

import requests
from django.contrib.auth.backends import BaseBackend
from django.urls import reverse
from mozilla_django_oidc.utils import absolutify

logger = logging.getLogger(__name__)


class MyOIDCAuthenticationBackend(BaseBackend):
    """Base OIDC authentication backend with DID-based user provisioning.

    Inherits from ``django.contrib.auth.backends.BaseBackend`` (NOT
    ``OIDCAuthenticationBackend``) to avoid ``OIDC_RP_CLIENT_SECRET``
    enforcement at ``__init__`` time (Rule 2).

    User lookup filters strictly on ``username=sub`` (the root DID
    string), completely bypassing email fields to prevent unique
    constraint violations (Rule 4).

    Sovereign Admin Posture Hook (AUTH_FLOW_SPECIFICATION.md §6.2):
    elevate if ``settings.ADMIN_DID`` matches ``sub``, always call
    ``set_unusable_password()`` on admin, elevation only.
    """

    def authenticate(self, request, **kwargs):
        if not request:
            return None

        code = request.GET.get("code")
        state = request.GET.get("state")
        if not (code and state):
            return None

        token_payload = {
            "client_id": self._get_setting("OIDC_RP_CLIENT_ID"),
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": absolutify(
                request,
                reverse(
                    self._get_setting(
                        "OIDC_AUTHENTICATION_CALLBACK_URL",
                        "oidc_authentication_callback",
                    )
                ),
            ),
        }

        client_secret = self._get_setting("OIDC_RP_CLIENT_SECRET", "")
        if client_secret:
            token_payload["client_secret"] = client_secret

        try:
            token_info = self.get_token(token_payload)
        except requests.ConnectionError:
            logger.error("Connection refused by token endpoint")
            return None
        except requests.Timeout:
            logger.error("Token endpoint timed out")
            return None
        except requests.RequestException as exc:
            logger.error("Token exchange failed: %s", exc)
            return None

        if "error" in token_info:
            logger.warning(
                "Token error [%s]: %s",
                token_info.get("error"),
                token_info.get("error_description", "(no description)"),
            )
            return None

        try:
            user_info = self._do_userinfo_request(token_info)
        except requests.ConnectionError:
            logger.error("Connection refused by userinfo endpoint")
            return None
        except requests.Timeout:
            logger.error("UserInfo endpoint timed out")
            return None
        except requests.RequestException as exc:
            logger.error("UserInfo request failed: %s", exc)
            return None

        return self._get_or_create_user(user_info)

    def get_token(self, payload, **kwargs):
        """Execute the token exchange. Override point for PKCE injection."""
        auth_header = None
        if self._get_setting("OIDC_TOKEN_USE_BASIC_AUTH", False):
            auth_header = requests.auth.HTTPBasicAuth(
                payload.pop("client_id", ""),
                payload.pop("client_secret", ""),
            )

        response = requests.post(
            self._get_setting("OIDC_OP_TOKEN_ENDPOINT"),
            data=payload,
            auth=auth_header,
            verify=self._get_setting("OIDC_VERIFY_SSL", True),
            timeout=self._get_setting("OIDC_TIMEOUT", 10),
        )
        response.raise_for_status()
        return response.json()

    def get_user(self, user_id):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

    def get_username(self, claims):
        return claims.get("sub")

    def _do_userinfo_request(self, token_info):
        access_token = token_info.get("access_token")
        if not access_token:
            raise ValueError("Token response missing access_token")

        response = requests.get(
            self._get_setting("OIDC_OP_USER_ENDPOINT"),
            headers={"Authorization": f"Bearer {access_token}"},
            verify=self._get_setting("OIDC_VERIFY_SSL", True),
            timeout=self._get_setting("OIDC_TIMEOUT", 10),
        )
        response.raise_for_status()
        return response.json()

    def _get_or_create_user(self, user_info):
        from django.contrib.auth import get_user_model

        User = get_user_model()

        sub = user_info.get("sub")
        if not sub:
            logger.warning("OIDC userinfo missing 'sub' claim")
            return None

        user, created = User.objects.get_or_create(
            username=sub,
            defaults={
                "email": user_info.get("email", ""),
                "first_name": user_info.get("given_name", ""),
                "last_name": user_info.get("family_name", ""),
            },
        )

        from django.conf import settings as _settings

        target_admin_did = getattr(_settings, "ADMIN_DID", None)
        is_admin = bool(target_admin_did) and sub == target_admin_did

        dirty = False
        if is_admin:
            if not user.is_staff:
                user.is_staff = True
                dirty = True
            if not user.is_superuser:
                user.is_superuser = True
                dirty = True
            if user.has_usable_password():
                user.set_unusable_password()
                dirty = True

        if dirty:
            user.save(update_fields=["is_staff", "is_superuser", "password"])

        return user

    @staticmethod
    def _get_setting(key, default=None):
        from django.conf import settings as _s

        return getattr(_s, key, default)
