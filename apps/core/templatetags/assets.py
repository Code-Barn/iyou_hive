import os
import json

from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def render_vite_assets():
    """
    Parse the Vite 5 manifest and return compiled script/link markup.

    Checks both standard manifest locations before falling back to
    raw asset paths.  Returns a safe HTML string for direct injection
    into the template <head>.
    """
    manifest_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'frontend', '.vite', 'manifest.json'),
        os.path.join(settings.BASE_DIR, 'static', 'frontend', 'assets', 'manifest.json'),
    ]

    js_file = 'frontend/assets/index.js'
    css_file = 'frontend/assets/index.css'

    manifest_path = None
    for p in manifest_paths:
        if os.path.exists(p):
            manifest_path = p
            break

    if manifest_path:
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)

            entry = (
                manifest.get('index.html')
                or manifest.get('src/main.tsx')
                or list(manifest.values())[0]
            )

            if isinstance(entry, dict):
                if entry.get('file'):
                    js_file = f"frontend/{entry['file']}"
                css_list = entry.get('css', [])
                if css_list:
                    css_file = f"frontend/{css_list[0]}"
        except Exception:
            pass

    js_url = f"{settings.STATIC_URL}{js_file}"
    css_url = f"{settings.STATIC_URL}{css_file}"

    return mark_safe(
        f'  <link rel="stylesheet" href="{css_url}">\n'
        f'  <script type="module" src="{js_url}"></script>'
    )
