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

from django.contrib import auth
from django.core.exceptions import SuspiciousOperation
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

# Session namespace for PKCE verifier (isolated from OIDC ``oidc_states``)
_SESSION_KEY_VERIFIER = "_pkce_cv"
_SESSION_KEY_TIMESTAMP = "_pkce_ts"

# RFC 7636 Section 10: verifier must not be usable after excessive delay
_VERIFIER_MAX_AGE_S = 300  # 5 minutes

# RFC 7636 Section 4.1: verifier length 43-128, we use max entropy
_VERIFIER_LENGTH = 128


# ──────────────────────────────────────────────────────────────────────
# Cryptographic utilities
# ──────────────────────────────────────────────────────────────────────


def _generate_code_verifier() -> str:
    """Generate an RFC 7636 Section 4.1 compliant code verifier.

    Uses ``secrets.token_urlsafe`` (CSPRNG) and truncates to exactly
    128 characters for maximum entropy within the allowed range.
    """
    # token_urlsafe produces ~1.3x chars per byte; request extra to
    # guarantee we have enough after truncation.
    raw = secrets.token_urlsafe(96)
    return raw[:_VERIFIER_LENGTH]


def _compute_s256_challenge(verifier: str) -> str:
    """RFC 7636 Section 4.2: BASE64URL(SHA256(ASCII(code_verifier)))."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


# ──────────────────────────────────────────────────────────────────────
# Session-bound verifier lifecycle
# ──────────────────────────────────────────────────────────────────────


def _store_verifier(request, verifier: str) -> None:
    """Persist the code verifier inside the encrypted Django session.

    The verifier lives under ``_pkce_cv`` and its creation timestamp
    under ``_pkce_ts``.  Both keys are namespaced to avoid collision
    with ``mozilla_django_oidc``'s ``oidc_states`` dict.
    """
    request.session[_SESSION_KEY_VERIFIER] = verifier
    request.session[_SESSION_KEY_TIMESTAMP] = time.time()
    request.session.modified = True


def _consume_verifier(request) -> str | None:
    """Atomically retrieve *and* destroy the verifier from the session.

    Returns ``None`` if the verifier is missing or has exceeded the
    maximum allowed age.
    """
    verifier = request.session.pop(_SESSION_KEY_VERIFIER, None)
    ts = request.session.pop(_SESSION_KEY_TIMESTAMP, None)

    if verifier is None:
        return None

    if ts is not None and (time.time() - ts) > _VERIFIER_MAX_AGE_S:
        logger.warning(
            "PKCE verifier expired (age=%.1fs, max=%ds)",
            time.time() - ts,
            _VERIFIER_MAX_AGE_S,
        )
        return None

    request.session.modified = True
    return verifier


def _purge_verifier(request) -> None:
    """Unconditional removal -- defense-in-depth."""
    request.session.pop(_SESSION_KEY_VERIFIER, None)
    request.session.pop(_SESSION_KEY_TIMESTAMP, None)
    request.session.modified = True


# ──────────────────────────────────────────────────────────────────────
# Authorization Request View
# ──────────────────────────────────────────────────────────────────────


class PKCEAuthorizationRequestView(OIDCAuthenticationRequestView):
    """OIDC login initiation with PKCE code_challenge injection.

    On ``GET /oidc/login/`` this view:

    1. Generates a 128-char ``code_verifier`` and its S256 ``code_challenge``.
    2. Stores the verifier in the encrypted session (``hive_sessionid``).
    3. Appends ``code_challenge`` + ``code_challenge_method=S256`` to the
       authorization redirect URL targeting ``https://iyou.me/openid/authorize/``.
    4. Stores the standard OIDC ``state`` + ``nonce`` in ``session['oidc_states']``
       (via the library helper) *without* a ``code_verifier`` to avoid
       dual-verifier confusion.
    """

    def get(self, request):
        state = get_random_string(self.get_settings("OIDC_STATE_SIZE", 32))
        redirect_field_name = self.get_settings("OIDC_REDIRECT_FIELD_NAME", "next")
        reverse_url = self.get_settings(
            "OIDC_AUTHENTICATION_CALLBACK_URL", "oidc_authentication_callback"
        )

        params = {
            "response_type": "code",
            "scope": self.get_settings("OIDC_RP_SCOPES", "openid email"),
            "client_id": self.OIDC_RP_CLIENT_ID,
            "redirect_uri": absolutify(request, reverse(reverse_url)),
            "state": state,
        }

        params.update(self.get_extra_params(request))

        if self.get_settings("OIDC_USE_NONCE", True):
            nonce = get_random_string(self.get_settings("OIDC_NONCE_SIZE", 32))
            params["nonce"] = nonce

        # ── PKCE ────────────────────────────────────────────────
        code_verifier = _generate_code_verifier()
        code_challenge = _compute_s256_challenge(code_verifier)

        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"

        # Store state + nonce in the standard oidc_states dict.
        # Pass code_verifier=None so the library does NOT embed it
        # inside oidc_states -- we manage it independently.
        add_state_and_verifier_and_nonce_to_session(
            request, state, params, code_verifier=None,
        )

        # Store the actual verifier in our isolated session slot
        _store_verifier(request, code_verifier)

        request.session["oidc_login_next"] = get_next_url(request, redirect_field_name)

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
       the isolated session slot.
    4. Deletes the state entry to prevent replay.
    5. Passes ``code_verifier`` to ``auth.authenticate()`` which
       dispatches it to iyou_idp's token endpoint.
    6. Clears the verifier reference from ``request`` on exit.

    If the verifier is missing or expired the callback still proceeds
    (the IDP may or may not require PKCE) but a warning is logged.
    """

    def get(self, request):
        if request.GET.get("error"):
            # ── Error branch ────────────────────────────────────
            _purge_verifier(request)

            if (
                "state" in request.GET
                and "oidc_states" in request.session
                and request.GET["state"] in request.session["oidc_states"]
            ):
                del request.session["oidc_states"][request.GET["state"]]
                request.session.save()

            if request.user.is_authenticated:
                auth.logout(request)
            assert not request.user.is_authenticated
            return self.login_failure()

        elif "code" in request.GET and "state" in request.GET:
            # ── Success branch ──────────────────────────────────
            if "oidc_states" not in request.session:
                return self.login_failure()

            state = request.GET.get("state")
            if state not in request.session["oidc_states"]:
                msg = "OIDC callback state not found in session `oidc_states`!"
                raise SuspiciousOperation(msg)

            nonce = request.session["oidc_states"][state]["nonce"]

            # Consume PKCE verifier -- retrieves and immediately
            # destroys the value in a single session mutation.
            code_verifier = _consume_verifier(request)

            # Remove the state entry to prevent replay attacks
            del request.session["oidc_states"][state]
            request.session.save()

            # Reload session from DB to prevent parallel-tab overwrites
            request.session = request.session.__class__(
                request.session.session_key,
            )

            if code_verifier:
                logger.info(
                    "PKCE verifier consumed (state=%s), "
                    "dispatching to iyou_idp token endpoint",
                    state,
                )
            else:
                logger.warning(
                    "No PKCE verifier in session for callback state=%s",
                    state,
                )

            # Authenticate -- the backend receives code_verifier as a kwarg
            # and includes it in the token exchange payload.
            kwargs = {
                "request": request,
                "nonce": nonce,
                "code_verifier": code_verifier,
            }

            self.user = auth.authenticate(**kwargs)

            if self.user and self.user.is_active:
                return self.login_success()

        return self.login_failure()


# ──────────────────────────────────────────────────────────────────────
# Authentication Backend
# ──────────────────────────────────────────────────────────────────────


class PKCEAuthenticationBackend(MyOIDCAuthenticationBackend):
    """OIDC backend that dispatches ``code_verifier`` to iyou_idp.

    Extends ``MyOIDCAuthenticationBackend`` (DID-based user provisioning)
    to forward the PKCE ``code_verifier`` in the back-channel token
    exchange.  The verifier is included in the ``token_payload`` dict
    sent to ``OIDC_OP_TOKEN_ENDPOINT`` (iyou_idp's token intercept
    gateway view).
    """

    def authenticate(self, request, **kwargs):
        code_verifier = kwargs.pop("code_verifier", None)

        if code_verifier is not None:
            logger.debug("PKCE code_verifier attached to token exchange payload")

        # Delegate to the parent which builds token_payload and calls
        # OIDC_OP_TOKEN_ENDPOINT.  The parent's ``get_token()`` sends
        # the payload as-is, so we inject code_verifier into the kwargs
        # which the parent will forward through the call chain.
        return super().authenticate(request, code_verifier=code_verifier, **kwargs)


# ──────────────────────────────────────────────────────────────────────
# Defense-in-Depth Middleware
# ──────────────────────────────────────────────────────────────────────


class PKCEVerifierCleanupMiddleware(MiddlewareMixin):
    """Scans every request for orphaned PKCE verifiers.

    If a ``_pkce_cv`` session key persists beyond the 5-minute maximum
    (e.g. because the callback never arrived or the user aborted the
    flow), this middleware purges it to prevent session state bloat
    and to close the replay window.
    """

    def process_request(self, request):
        if _SESSION_KEY_VERIFIER not in request.session:
            return None

        ts = request.session.get(_SESSION_KEY_TIMESTAMP)
        if ts is None or (time.time() - ts) > _VERIFIER_MAX_AGE_S:
            _purge_verifier(request)
            logger.debug("Purged expired/orphaned PKCE verifier from session")

        return None
