from django import template
from django.conf import settings
import json
import os

register = template.Library()

@register.simple_tag
def get_vite_assets():
    """
    Read the Vite manifest.json and return JS/CSS paths.
    Returns dict with 'js' and 'css' keys.
    
    Note: The manifest.json paths ALREADY include 'assets/' prefix.
    Do NOT add it again.
    """
    # Check both possible manifest locations
    manifest_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'frontend', '.vite', 'manifest.json'),
        os.path.join(settings.BASE_DIR, 'static', 'frontend', 'assets', 'manifest.json')
    ]
    
    default_assets = {
        'js': '/static/frontend/assets/index.js',
        'css': '/static/frontend/assets/index.css'
    }
    
    manifest_path = None
    for path in manifest_paths:
        if os.path.exists(path):
            manifest_path = path
            break
    
    if not manifest_path:
        print("WARNING: No manifest.json found, using defaults")
        return default_assets
        
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Look for the main entry point
        entry = manifest.get('index.html', {})
        if not entry:
            # Try to find any entry point with 'isEntry': True
            for key, value in manifest.items():
                if value.get('isEntry'):
                    entry = value
                    break
        
        # Get the file path (already includes 'assets/' prefix from manifest)
        js_file = entry.get('file', '')
        
        # Get CSS files (already include 'assets/' prefix)
        css_files = entry.get('css', [])
        
        # Construct final URLs - manifest already has 'assets/' prefix
        # So we only need to add /static/frontend/ prefix
        js_url = f'/static/frontend/{js_file}' if js_file else default_assets['js']
        css_url = f'/static/frontend/{css_files[0]}' if css_files else default_assets['css']
        
        # Debug output
        print(f"DEBUG: Manifest path: {manifest_path}")
        print(f"DEBUG: JS file from manifest: {js_file}")
        print(f"DEBUG: Final JS URL: {js_url}")
        print(f"DEBUG: CSS file from manifest: {css_files[0] if css_files else 'None'}")
        print(f"DEBUG: Final CSS URL: {css_url}")
        
        result = {
            'js': js_url,
            'css': css_url
        }
        
        return result
        
    except Exception as e:
        print(f"ERROR reading manifest: {e}")
        return default_assets
