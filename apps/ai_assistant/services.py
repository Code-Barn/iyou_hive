"""
AI services for photo-timeline matching and analysis.
"""

from django.utils import timezone
from datetime import timedelta
from apps.archive.models import Photo
from apps.timeline.models import TimelineEvent, PhotoEventLink
from apps.ai_assistant.api_client import call_ai_api


def match_photos_to_events(case, user):
    """
    Match photos to timeline events based on timestamp and GPS proximity.
    
    Args:
        case: Case object
        user: User object
        
    Returns:
        list: Created PhotoEventLink objects
    """
    # Get all photos for this case
    photos = Photo.objects.filter(case=case, uploader=user)
    
    # Get all timeline events for this case
    events = TimelineEvent.objects.filter(case=case, created_by=user)
    
    created_links = []
    
    for photo in photos:
        if not photo.timestamp:
            continue
        
        # Find events within ±1 hour of the photo timestamp
        time_range_start = photo.timestamp - timedelta(hours=1)
        time_range_end = photo.timestamp + timedelta(hours=1)
        
        candidate_events = events.filter(
            date__gte=time_range_start.date(),
            date__lte=time_range_end.date()
        )
        
        for event in candidate_events:
            # Calculate confidence based on time proximity
            time_diff = abs((photo.timestamp - timezone.make_aware(
                timezone.datetime.combine(event.date, timezone.datetime.min.time()))).total_seconds())
            time_confidence = max(0, 1 - (time_diff / 3600))  # 0-1 based on 1 hour window
            
            # GPS proximity (if available)
            gps_confidence = 0
            if photo.gps_latitude and photo.gps_longitude:
                # Placeholder: In a real implementation, this would compare with event GPS
                # For now, assume some GPS confidence if photo has GPS data
                gps_confidence = 0.3
            
            # Combined confidence
            confidence = min(1.0, time_confidence + gps_confidence)
            
            if confidence > 0.5:  # Only create links with reasonable confidence
                # Generate AI explanation
                prompt = f"""
Explain why this photo might be related to this timeline event:

Photo:
- Timestamp: {photo.timestamp}
- Device: {photo.device}
- GPS: {photo.gps_latitude}, {photo.gps_longitude}

Event:
- Date: {event.date}
- Event: {event.event}
- Category: {event.category}
- Notes: {event.notes}

Confidence: {confidence:.2f}

Provide a brief explanation (1-2 sentences) for why these might be related.
"""
                ai_notes = call_ai_api(prompt, user=user)
                
                # Create the link
                link = PhotoEventLink.objects.create(
                    photo=photo,
                    event=event,
                    confidence=confidence,
                    notes=ai_notes if ai_notes else f"Matched based on timestamp proximity ({time_confidence:.2f}) and GPS ({gps_confidence:.2f})"
                )
                created_links.append(link)
    
    return created_links


def analyze_photo(photo_id, user=None):
    """
    Analyze a single photo using AI.
    
    Args:
        photo_id: ID of the Photo object
        user: Optional user object for API settings
        
    Returns:
        dict: Analysis results
    """
    try:
        photo = Photo.objects.get(id=photo_id)
        
        prompt = f"""
Analyze this photo for forensic timeline purposes:

Photo Details:
- Timestamp: {photo.timestamp}
- Device: {photo.device}
- GPS: {photo.gps_latitude}, {photo.gps_longitude}
- File: {photo.file.name}

Provide:
1. A brief description of what might be in the photo
2. Any notable features or anomalies
3. Suggestions for related timeline events
4. Potential issues or inconsistencies

Format as markdown with clear sections.
"""
        analysis = call_ai_api(prompt, user=user)
        
        return {
            'success': True,
            'analysis': analysis,
            'photo_id': photo_id
        }
    
    except Photo.DoesNotExist:
        return {'success': False, 'error': 'Photo not found'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
