from django.conf import settings
import json
import os

class AIService:
    """
    AI-powered services for timeline event classification.
    """
    
    @classmethod
    def classify_party(cls, event_text: str, section_header: str = None) -> str:
        """
        Classify the source party based on event text.
        
        Uses smart keyword matching (fallback if AI not available).
        
        Args:
            event_text: Combined event title and notes
            section_header: Optional section header for context
            
        Returns:
            str: 'CLIENT', 'OPPOSING', or 'NEUTRAL'
        """
        text = event_text.lower()
        section = (section_header or '').lower()
        
        # Smart keyword detection (fallback logic)
        has_david = 'david' in text
        has_pauletta = 'pauletta' in text or 'pauletta' in text
        
        # Determine party based on text
        if has_pauletta and not has_david:
            return 'OPPOSING'  # Pauletta mentioned without David -> Opposing
        elif has_david and not has_pauletta:
            return 'CLIENT'     # David mentioned without Pauletta -> Client
        elif has_david and has_pauletta:
            # Both mentioned - use section context
            if section:
                if 'pauletta' in section:
                    return 'OPPOSING'
                elif 'david' in section:
                    return 'CLIENT'
            return 'NEUTRAL'  # Both mentioned, no clear context
        else:
            # No clear keywords - try AI classification if available
            return cls._ai_classify_party(event_text)
    
    @classmethod
    def _ai_classify_party(cls, event_text: str) -> str:
        """
        Use AI service to classify party if available.
        Falls back to NEUTRAL if AI not configured.
        """
        try:
            # Try to use Mistral AI if configured
            api_key = getattr(settings, 'MISTRAL_API_KEY', None)
            
            if not api_key:
                return 'NEUTRAL'  # No AI configured
            
            # Simple heuristic as fallback (replace with actual AI call)
            # In production, this would call the Mistral API
            neutral_keywords = [
                'birth', 'born', 'graduated', 'married', 'died',
                'purchased', 'sold', 'moved', 'retired',
                'child', 'baby', 'son', 'daughter'
            ]
            
            text_lower = event_text.lower()
            for keyword in neutral_keywords:
                if keyword in text_lower:
                    return 'NEUTRAL'
            
            return 'NEUTRAL'  # Default to neutral if unclear
            
        except Exception as e:
            print(f"AI classification error: {e}")
            return 'NEUTRAL'
