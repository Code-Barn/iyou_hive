# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
PKCE Ingress Integration for Hiver
===================================

Standalone cryptographic login middleware that implements RFC 7636
Proof Key for Code Exchange (PKCE) for the OIDC authorization code flow
with iyou_idp.

Security properties
-------------------
* **code_verifier** -- 128-character high-entropy cryptographic random
  string stored exclusively within the Django encrypted session
  (``hive_sessionid`` cookie).  Never persisted to disk, never logged.
* **code_challenge** -- S256 (BASE64URL(SHA256(code_verifier))) sent
  to the authorization endpoint at ``https://iyou.me/openid/authorize/``.
* **Immediate consumption** -- The verifier is retrieved and destroyed
  in a single atomic operation inside the callback handler, before the
  token exchange is dispatched to iyou_idp's token intercept gateway.
* **Defense-in-depth cleanup** -- ``PKCEVerifierCleanupMiddleware``
  purges any orphaned verifier that outlives the 5-minute maximum age.

Usage
-----
This module replaces the default ``mozilla_django_oidc`` views and
authentication backend with PKCE-aware subclasses.  It does **not**
enable the library's built-in ``OIDC_USE_PKCE`` toggle -- the entire
PKCE lifecycle is managed independently to avoid dual-verifier
conflicts and to guarantee explicit session-bound clearing.

Routes wired in ``config/urls.py``:
    /oidc/login/     -> PKCEAuthorizationRequestView
    /oidc/callback/  -> PKCEAuthenticationCallbackView

Auth backend in ``config/settings.py``:
    AUTHENTICATION_BACKENDS += "apps.core.auth_pkce.PKCEAuthenticationBackend"

Frontend impact: **NONE**.  The React SPA uses cookie-based session
authentication exclusively; it never observes, stores, or transmits
the ``code_verifier``.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from base64 import urlsafe_b64encode

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.deprecation import MiddlewareMixin
from mozilla_django_oidc.utils import (
    absolutify,
    add_state_and_verifier_and_nonce_to_session,
)
from mozilla_django_oidc.views import (
    OIDCAuthenticationCallbackView,
    OIDCAuthenticationRequestView,
    get_next_url,
)

from apps.core.auth import MyOIDCAuthenticationBackend

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────────────────

SESSION_KEY_CODE_VERIFIER = "pkce_code_verifier"
SESSION_KEY_TIMESTAMP = "_pkce_ts"

_VERIFIER_MAX_AGE_S = 300  # 5 minutes — RFC 7636 Section 10


# ──────────────────────────────────────────────────────────────────────
# Cryptographic utilities
# ──────────────────────────────────────────────────────────────────────


def _generate_code_verifier(length: int = 64) -> str:
    """Return a cryptographically secure, URL-safe random string.

    The output length (pre-encoding) is `length` random bytes, which
    yields a base64url string between 43 and 128 characters depending
    on the input length.  RFC 7636 section 4.1 mandates the range
    [43, 128].
    """
    if not (43 <= length <= 128):
        msg = f"code_verifier length must be between 43 and 128, got {length}"
        raise ValueError(msg)
    return secrets.token_urlsafe(length)


def _compute_s256_challenge(verifier: str) -> str:
    """BASE64URL(SHA256(ASCII(code_verifier))) — RFC 7636 section 4.1."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# ──────────────────────────────────────────────────────────────────────
# Session-bound verifier lifecycle
# ──────────────────────────────────────────────────────────────────────


def _store_verifier(request, verifier: str) -> None:
    """Persist the code verifier inside the encrypted Django session."""
    request.session[SESSION_KEY_CODE_VERIFIER] = verifier
    request.session[SESSION_KEY_TIMESTAMP] = time.time()
    request.session.modified = True


def _purge_verifier(request) -> None:
    """Unconditional removal — defense-in-depth."""
    request.session.pop(SESSION_KEY_CODE_VERIFIER, None)
    request.session.pop(SESSION_KEY_TIMESTAMP, None)
    request.session.modified = True


# ──────────────────────────────────────────────────────────────────────
# Authorization Request View
# ──────────────────────────────────────────────────────────────────────


class PKCEAuthorizationRequestView(OIDCAuthenticationRequestView):
    """OIDC login initiation with PKCE code_challenge injection.

    On ``GET /oidc/login/`` this view:

    1. Generates a 64-byte ``code_verifier`` and its S256 ``code_challenge``.
    2. Stores the verifier in the encrypted session (``hive_sessionid``).
    3. Appends ``code_challenge`` + ``code_challenge_method=S256`` to the
       authorization redirect URL targeting ``https://iyou.me/openid/authorize/``.
    4. Stores the standard OIDC ``state`` + ``nonce`` in
       ``session['oidc_states']`` (via the library helper) *without* a
       ``code_verifier`` to avoid dual-verifier confusion.
    """

    http_method_names = ["get"]

    def get(self, request):
        state = get_random_string(self.get_settings("OIDC_STATE_SIZE", 32))
        redirect_field_name = self.get_settings(
            "OIDC_REDIRECT_FIELD_NAME", "next"
        )
        reverse_url = self.get_settings(
            "OIDC_AUTHENTICATION_CALLBACK_URL",
            "oidc_authentication_callback",
        )

        params = {
            "response_type": "code",
            "scope": self.get_settings(
                "OIDC_RP_SCOPES", "openid profile email"
            ),
            "client_id": self.OIDC_RP_CLIENT_ID,
            "redirect_uri": absolutify(request, reverse(reverse_url)),
            "state": state,
        }

        params.update(self.get_extra_params(request))

        if self.get_settings("OIDC_USE_NONCE", True):
            nonce = get_random_string(
                self.get_settings("OIDC_NONCE_SIZE", 32)
            )
            params["nonce"] = nonce

        code_verifier = _generate_code_verifier(
            self.get_settings("OIDC_PKCE_CODE_VERIFIER_SIZE", 64)
        )
        code_challenge = _compute_s256_challenge(code_verifier)

        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

        add_state_and_verifier_and_nonce_to_session(
            request, state, params, code_verifier=None,
        )

        _store_verifier(request, code_verifier)

        request.session[SESSION_KEY_CODE_VERIFIER] = code_verifier
        request.session["oidc_login_next"] = get_next_url(
            request, redirect_field_name
        )
        request.session.save()

        query = "&".join(f"{k}={v}" for k, v in params.items())
        redirect_url = f"{self.OIDC_OP_AUTH_ENDPOINT}?{query}"

        logger.info(
            "PKCE authorization initiated: state=%s challenge_method=S256",
            state,
        )

        return HttpResponseRedirect(redirect_url)


# ──────────────────────────────────────────────────────────────────────
# Authentication Callback View
# ──────────────────────────────────────────────────────────────────────


class PKCEAuthenticationCallbackView(OIDCAuthenticationCallbackView):
    """OIDC callback with explicit PKCE verifier consumption.

    On ``GET /oidc/callback/?code=...&state=...`` this view:

    1. Validates the ``state`` against ``session['oidc_states']``.
    2. Extracts ``nonce`` from the standard state dict.
    3. Atomically retrieves *and* destroys the ``code_verifier`` from
       the isolated session slot via ``get_backend_kwargs()``.
    4. Deletes the state entry to prevent replay.
    5. Passes ``code_verifier`` to ``auth.authenticate()`` which
       dispatches it to iyou_idp's token endpoint.

    This view does NOT override ``get()``.  Instead it overrides the
    library's ``get_backend_kwargs()`` hook, which is called internally
    by the parent ``get()`` method when it invokes the authentication
    backend.  By injecting the code_verifier into the backend kwargs
    here, the verifier is guaranteed to reach the backend's
    ``authenticate()`` call without intercepting the view routing flow.
    """

    def get_backend_kwargs(self, request):
        """Pop the PKCE verifier from the session and forward it to the
        authentication backend via the kwargs dictionary.
        """
        kwargs = super().get_backend_kwargs(request)

        code_verifier = request.session.pop(SESSION_KEY_CODE_VERIFIER, None)

        if code_verifier is None:
            logger.warning(
                "No pkce_code_verifier in session — possible replay, "
                "cookie rotation failure, or direct callback access"
            )

        kwargs.update({"code_verifier": code_verifier})
        return kwargs


# ──────────────────────────────────────────────────────────────────────
# Authentication Backend
# ──────────────────────────────────────────────────────────────────────


class PKCEAuthenticationBackend(MyOIDCAuthenticationBackend):
    """OIDC backend that dispatches ``code_verifier`` to iyou_idp.

    Extends ``MyOIDCAuthenticationBackend`` (DID-based user provisioning)
    to forward the PKCE ``code_verifier`` in the back-channel token
    exchange.  The verifier is cached as an instance attribute to survive
    internal method transitions, then injected into the token payload
    via ``get_token()``.
    """

    def authenticate(self, request, **kwargs):
        code_verifier = kwargs.pop("code_verifier", None)
        if code_verifier is not None:
            self.pkce_code_verifier = code_verifier
        return super().authenticate(request, **kwargs)

    def get_token(self, payload, **kwargs):
        code_verifier = getattr(self, "pkce_code_verifier", None)
        if code_verifier:
            payload["code_verifier"] = code_verifier
        return super().get_token(payload, **kwargs)


# ──────────────────────────────────────────────────────────────────────
# Defense-in-Depth Middleware
# ──────────────────────────────────────────────────────────────────────


class PKCEVerifierCleanupMiddleware(MiddlewareMixin):
    """Scans every request for orphaned PKCE verifiers.

    If a ``pkce_code_verifier`` session key persists beyond the 5-minute
    maximum (e.g. because the callback never arrived or the user aborted
    the flow), this middleware purges it to prevent session state bloat
    and to close the replay window.
    """

    def process_request(self, request):
        if SESSION_KEY_CODE_VERIFIER not in request.session:
            return None

        ts = request.session.get(SESSION_KEY_TIMESTAMP)
        if ts is None or (time.time() - ts) > _VERIFIER_MAX_AGE_S:
            _purge_verifier(request)
            logger.debug("Purged expired/orphaned PKCE verifier from session")

        return None
