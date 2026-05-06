"""
AI API client for Hiver supporting Mistral and Gemini.
"""

import json
import requests
from django.conf import settings
from apps.ai_assistant.models import UserSettings


def get_user_settings(user=None):
    if not user:
        return None
    try:
        return UserSettings.objects.get(user=user)
    except UserSettings.DoesNotExist:
        return None


def call_ai_api(prompt, user=None, model="mistral-tiny", temperature=0.7, max_tokens=2000):
    """
    Call the AI API to get a response.

    Uses the preferred API provider when configured.
    """
    user_settings = get_user_settings(user)

    provider = 'mistral'
    if user_settings:
        provider = user_settings.preferred_ai_provider

    if provider == 'gemini':
        api_key = (user_settings.gemini_api_key if user_settings and user_settings.gemini_api_key
                   else getattr(settings, 'GEMINI_API_KEY', None))

        if not api_key:
            return (
                "Error: Gemini API key not configured.\n\n"
                "Please configure your Google Gemini API key in settings."
            )

        return _call_gemini_api(prompt, api_key, temperature, max_tokens)
    else:
        api_key = (user_settings.mistral_api_key if user_settings and user_settings.mistral_api_key
                   else getattr(settings, 'MISTRAL_API_KEY', None))

        if not api_key:
            return (
                "Error: Mistral API key not configured.\n\n"
                "Please configure your Mistral API key in settings."
            )

        return _call_mistral_api(prompt, api_key, model, temperature, max_tokens)


def _call_gemini_api(prompt, api_key, temperature=0.7, max_tokens=2000):
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-pro:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']

    except requests.exceptions.Timeout:
        return "API Request Timeout: The request to Gemini API timed out.\n\nPlease try again later."
    except requests.exceptions.RequestException as e:
        return f"API Request Failed: {str(e)}\n\nPlease check your network connection and API key."
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        return f"API Response Error: {str(e)}\n\nThe Gemini API may have changed or returned an unexpected format."
    except Exception as e:
        return f"Error processing AI request: {str(e)}\n\nPlease check your Gemini API configuration."


def _call_mistral_api(prompt, api_key, model="mistral-tiny", temperature=0.7, max_tokens=2000):
    try:
        # Make actual API call to Mistral using requests
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        return data['choices'][0]['message']['content']

    except requests.exceptions.Timeout:
        # Handle timeout errors
        return f"API Request Timeout: The request to Mistral API timed out.\n\nPlease try again later."
    except requests.exceptions.RequestException as e:
        # Network or API error
        return f"API Request Failed: {str(e)}\n\nPlease check your network connection and API key."
    except (KeyError, json.JSONDecodeError) as e:
        # API response format error
        return f"API Response Error: {str(e)}\n\nThe Mistral API may have changed or returned an unexpected format."
    except Exception as e:
        # Other errors
        return f"Error processing AI request: {str(e)}\n\nPlease check your Mistral API configuration."
