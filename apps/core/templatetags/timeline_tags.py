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

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def timeline_class(source_party):
    """
    Returns the CSS class for timeline events based on source_party.
    
    Args:
        source_party: The source party value (CLIENT, OPPOSING, NEUTRAL)
    
    Returns:
        str: CSS class name (client, opposing, neutral)
    """
    mapping = {
        'CLIENT': 'client',
        'OPPOSING': 'opposing',
        'NEUTRAL': 'neutral',
    }
    return mapping.get(source_party, 'neutral')


@register.filter
def category_badge_class(category):
    """
    Returns the CSS class for category badges.
    
    Args:
        category: The category value (VERIFIED, CONTESTED)
    
    Returns:
        str: CSS class name (verified, contested)
    """
    mapping = {
        'VERIFIED': 'verified',
        'CONTESTED': 'contested',
    }
    return mapping.get(category, 'contested')


@register.filter
def source_party_label(source_party):
    """
    Returns a human-readable label for source_party.
    Only returns label for CLIENT or OPPOSING (not NEUTRAL).
    
    Args:
        source_party: The source party value
        
    Returns:
        str: Human-readable label, or empty string if NEUTRAL/unknown
    """
    mapping = {
        'CLIENT': 'Client',
        'OPPOSING': 'Opposing Party',
    }
    return mapping.get(source_party, '')
