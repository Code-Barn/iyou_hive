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

import logging

from django.contrib.auth import get_user_model
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)
User = get_user_model()


class MyOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    def authenticate(self, request, **kwargs):
        try:
            return super().authenticate(request, **kwargs)
        except Exception as e:
            logger.error(f"OIDC authenticate error: {e}", exc_info=True)
            raise

    def create_user(self, claims):
        user = User.objects.create_user(username=claims.get("sub"))
        user.is_active = True
        user.set_unusable_password()
        user.save()
        logger.info(f"Created sovereign user: {user.username}")
        return user

    def filter_users_by_claims(self, claims):
        did = claims.get("sub")
        if not did:
            logger.error("No 'sub' claim found in OIDC token")
            return User.objects.none()
        user, created = User.objects.get_or_create(username=did)
        if created:
            user.set_unusable_password()
            user.is_active = True
            user.save()
            logger.info(f"Auto-created sovereign user via OIDC: {user.username}")
        else:
            logger.info(f"Mapped to existing user: {user.username}")
        return User.objects.filter(id=user.id)

    def verify_claims(self, claims):
        return "sub" in claims

    def get_username(self, claims):
        return claims.get("sub")
