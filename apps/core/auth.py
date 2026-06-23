import logging

import environ
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)
env = environ.Env()


class MyOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    """Canonical OIDC authentication backend with DID-based user provisioning."""

    def authenticate(self, request, **kwargs):
        try:
            return super().authenticate(request, **kwargs)
        except Exception as e:
            logger.error(f"OIDC authenticate error: {e}", exc_info=True)
            return None

    def create_user(self, claims):
        user = super().create_user(claims)
        user.set_unusable_password()
        user.save()
        return self._evaluate_admin_elevation(user)

    def filter_users_by_claims(self, claims):
        did = claims.get("sub")
        if not did:
            logger.error("No 'sub' claim found in OIDC token")
            return self.UserModel.objects.none()
        users = self.UserModel.objects.filter(username=did)
        if not users.exists():
            user = self.UserModel.objects.create_user(username=did)
            user.set_unusable_password()
            user.save()
            logger.info(f"Auto-created sovereign user via OIDC: {user.username}")
            self._evaluate_admin_elevation(user)
            return self.UserModel.objects.filter(username=did)
        for user in users:
            self._evaluate_admin_elevation(user)
        return users

    def verify_claims(self, claims):
        return "sub" in claims

    def get_username(self, claims):
        return claims.get("sub")

    def _evaluate_admin_elevation(self, user):
        if not user or user.is_anonymous:
            return user
        master_admin_did = env.str("ADMIN_DID", default="")
        if master_admin_did and user.username == master_admin_did:
            user.is_staff = True
            user.is_superuser = True
        user.save()
        return user
