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
