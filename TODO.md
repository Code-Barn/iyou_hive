# TODO — iyou_hive (Legal Vault)

**Orchestrated from:** `omni_social` (central hub)
**Last synced:** 2026-07-14

---

## Layer 0 — Ecosystem Standardization

> Templates generated via `omni_social/generate_templates.py`. Do not edit
> `_ecosystem_bar.html` or `_standard_header.html` manually — changes will be
> overwritten on next regeneration. Edit the canonical source in omni_social instead.

- [x] Templates regenerated — **Done 2026-07-13**

## Layer 1 — PKCE / Auth — Public PKCE Alignment

> Canonical spec: `omni_social/docs/OMNI_SOCIAL_AUTH_STANDARDIZATION.md`
> Reference module: `omni_social/templates/utils/auth_pkce.py`

Current state: `PKCEVerifierCleanupMiddleware` with dual session keys (`_pkce_cv`/`_pkce_ts`), 128-char verifier, 300s TTL. Session container override was removed (fix for cross-thread state loss). Needs alignment to canonical pattern.

- [ ] **Scope alignment:** Verify `OIDC_RP_SCOPES = "openid profile email"` in settings.py. Not `"openid"` alone — matches IDP default scope set.
- [ ] **Rule 1 — Proxy Header:** Add `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")` to `settings.py`
- [ ] **Rule 2 — Public Client:** Verify backend inherits `auth.Backend`, not `OIDCAuthenticationBackend`. Remove any `OIDC_RP_CLIENT_SECRET` references.
- [ ] **Rule 3 — Instance State Relay:** Verify callback view overrides `get_backend_kwargs()`, not `get()`. Verifier must flow through kwargs to backend.
- [ ] **Rule 4 — Sovereign Profile Anchoring:** Verify `get_username()` pinned to `sub` claim. No email-based lookup fallback.
- [ ] **Privilege evaluation:** Verify `settings.ADMIN_DID` (not `os.environ.get`). Uses `save(update_fields=[...])`.
- [ ] **Dirty-flag pattern:** Verify `user.save()` only executes when staff/superuser state actually changes.
- [ ] **Exception guard:** Verify `try/except requests.RequestException` on all back-channel HTTP calls.
- [ ] **Secret stripping:** Remove `OIDC_RP_CLIENT_SECRET` from container manifests (Helm values.yaml, Docker Compose .env).
- [ ] **Rule 5 — Logout View:** Add `path("oidc/logout/", OIDCLogoutView.as_view(), name="oidc_logout")` to config/urls.py. Set `LOGOUT_REDIRECT_URL = "/"` in settings.

## Layer 2 — App-Specific

- [ ] **Ecosystem Doc Organization:** Standardize repo layout to match iyou_wun precedent — root: `AGENT.md`, `README.md`; `docs/`: `DEVELOPER_GUIDE.md`, `DESIGN_DOC.md`, `TODO.md`, `ecosystem_shared/`, `archive/`.

---
