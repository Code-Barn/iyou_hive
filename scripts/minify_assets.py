#!/usr/bin/env python3

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

"""
Script to minify CSS and JavaScript files.

This script:
1. Minifies CSS files by removing comments, whitespace, and newlines
2. Minifies JavaScript files similarly
3. Creates .min versions of the original files
4. For production, copy minified files to minified versions
"""

import re
import os
import sys
from pathlib import Path


def minify_css(content):
    """
    Minify CSS content.
    
    Removes:
    - Comments
    - Whitespace
    - Newlines where possible
    - Multiple spaces
    """
    # Remove all comments (both /* */ and //)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    
    # Remove whitespace around {, }, :, ,, ;
    content = re.sub(r'\s*{\s*', '{', content)
    content = re.sub(r'\s*}\s*', '}', content)
    content = re.sub(r'\s*;\s*', ';', content)
    content = re.sub(r'\s*:\s*', ':', content)
    content = re.sub(r'\s*,\s*', ',', content)
    
    # Remove leading/trailing whitespace from lines
    lines = content.split('\n')
    minified = []
    for line in lines:
        line = line.strip()
        if line:
            minified.append(line)
    
    content = '\n'.join(minified)
    
    # Remove last semicolon before closing brace
    content = re.sub(r';}', '}', content)
    
    return content


def minify_js(content):
    """
    Minify JavaScript content.
    
    Removes:
    - Single-line comments
    - Multi-line comments
    - Whitespace where safe
    - Newlines where safe
    """
    # Remove single-line comments (// ...)
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    
    # Remove multi-line comments (/* ... */)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Remove whitespace around operators, brackets, etc.
    content = re.sub(r'\s*([{};,:=+\-*%&|^<>!?])\s*', r'\1', content)
    
    # Remove extra whitespace
    content = re.sub(r'\s+', ' ', content)
    
    # Remove whitespace at start/end of lines
    lines = content.split('\n')
    minified = []
    for line in lines:
        line = line.strip()
        if line:
            minified.append(line)
    
    content = '\n'.join(minified)
    
    # Remove space before/after certain characters
    content = re.sub(r'\s*([,;:.])\s*', r'\1 ', content)
    content = re.sub(r'\s+([{}();])\s*', r'\1', content)
    
    return content


def minify_file(input_path, output_path, minifier):
    """
    Minify a file and save to output.
    
    Args:
        input_path: Path to input file
        output_path: Path to save minified file
        minifier: minify_css or minify_js function
    """
    print(f"Minifying {input_path}...")
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        minified = minifier(content)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(minified)
        
        print(f"  → Saved to {output_path}")
        print(f"  Original: {len(content):,} bytes")
        print(f"  Minified: {len(minified):,} bytes")
        print(f"  Reduction: {((1 - len(minified)/len(content)) * 100):.1f}%")
        
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    """Main function to minify all assets."""
    print("=" * 60)
    print("Hiver Asset Minifier")
    print("=" * 60)
    print()
    
    base_dir = Path(__file__).parent.parent
    static_dir = base_dir / 'static'
    
    # CSS files to minify
    css_files = [
        (static_dir / 'css' / 'style.css', static_dir / 'css' / 'style.min.css'),
    ]
    
    # JS files to minify
    js_files = [
        (static_dir / 'js' / 'theme.js', static_dir / 'js' / 'theme.min.js'),
    ]
    
    # Minify CSS
    print("\n-- CSS Files --")
    for input_path, output_path in css_files:
        if input_path.exists():
            minify_file(input_path, output_path, minify_css)
        else:
            print(f"  ✗ File not found: {input_path}")
    
    # Minify JS
    print("\n-- JavaScript Files --")
    for input_path, output_path in js_files:
        if input_path.exists():
            minify_file(input_path, output_path, minify_js)
        else:
            print(f"  ✗ File not found: {input_path}")
    
    print("\n" + "=" * 60)
    print("Minification complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
