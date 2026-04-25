#!/usr/bin/env python3
"""
Filemapper Script

Generates a hierarchical map of files in a directory as a Markdown document.
This is useful for visualizing the archive structure in Hiver.

Usage:
    python scripts/filemapper.py <directory_path> [output_file] [max_depth]

Arguments:
    directory_path   Path to the directory to map
    output_file     Optional output file path (default: archive_map.md)
    max_depth       Maximum depth to map (default: 6)

Example:
    python scripts/filemapper.py user_archive/ user_archive/archive_map.md 6
"""

import os
import sys
from pathlib import Path


def generate_file_map(directory, max_depth=6, prefix="", level=0):
    """
    Recursively generate a file tree map.
    
    Args:
        directory: Path to the directory being mapped
        max_depth: Maximum depth to traverse
        prefix: Current indentation string
        level: Current depth level
        
    Returns:
        list: Lines of the file tree
    """
    lines = []
    
    # Stop if we've reached max depth
    if level > max_depth:
        return lines
    
    try:
        items = sorted(os.listdir(directory), key=lambda x: (not os.path.isdir(os.path.join(directory, x)), x.lower()))
    except (OSError, PermissionError) as e:
        lines.append(f"{prefix}🔒 __Access Denied__ ({e})")
        return lines
    
    for i, item in enumerate(items):
        item_path = os.path.join(directory, item)
        is_last = i == len(items) - 1
        
        if os.path.isdir(item_path):
            # Directory
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}📁 {item}/")
            
            # Recurse into directory
            new_prefix = prefix + ("    " if is_last else "│   ")
            lines.extend(generate_file_map(item_path, max_depth, new_prefix, level + 1))
        else:
            # File
            connector = "└── " if is_last else "├── "
            
            # Get file extension and icon
            ext = os.path.splitext(item)[1].lower() if '.' in item else ''
            icon = get_file_icon(ext)
            
            # Get file info
            size = os.path.getsize(item_path)
            size_str = format_size(size)
            
            lines.append(f"{prefix}{connector}{icon} {item} ({size_str})")
    
    return lines


def get_file_icon(extension):
    """
    Get an emoji icon for a file based on its extension.
    
    Args:
        extension: File extension (e.g., '.pdf', '.md')
        
    Returns:
        str: Emoji icon
    """
    icons = {
        '.pdf': '📕',
        '.md': '📄',
        '.txt': '📝',
        '.doc': '📑',
        '.docx': '📑',
        '.xls': '📊',
        '.xlsx': '📊',
        '.ppt': '📑',
        '.pptx': '📑',
        '.jpg': '🖼️',
        '.jpeg': '🖼️',
        '.png': '🖼️',
        '.gif': '🖼️',
        '.svg': '🖼️',
        '.eml': '✉️',
        '.json': '📋',
        '.xml': '📋',
        '.csv': '📊',
        '.zip': '🗄️',
        '.tar': '🗄️',
        '.gz': '🗄️',
    }
    
    return icons.get(extension, '📎')


def format_size(size_bytes):
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Human-readable size (e.g., "1.5 KB", "2.3 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def generate_markdown_map(directory, max_depth=6):
    """
    Generate a complete Markdown file tree map.
    
    Args:
        directory: Path to the directory to map
        max_depth: Maximum depth to traverse
        
    Returns:
        str: Complete markdown document
    """
    lines = []
    
    # Header
    dir_name = os.path.basename(os.path.abspath(directory))
    lines.append(f"# {dir_name} Archive Map")
    lines.append("")
    lines.append(f"Generated: {os.path.abspath(directory)}")
    lines.append(f"Total Size: {format_size(get_directory_size(directory))}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Date range (if dates can be extracted from filenames)
    dates = extract_dates_from_filenames(directory)
    if dates:
        lines.append(f"**Date Range:** {min(dates)} to {max(dates)}")
        lines.append("")
    
    # File tree
    lines.append("## File Structure")
    lines.append("")
    lines.append("```")
    
    # Add the tree
    tree_lines = generate_file_map(directory, max_depth)
    for line in tree_lines:
        lines.append(line)
    
    lines.append("```")
    lines.append("")
    
    # Statistics
    file_count, dir_count = count_files_and_dirs(directory)
    lines.append("## Statistics")
    lines.append("")
    lines.append(f"- **Total Files:** {file_count}")
    lines.append(f"- **Total Directories:** {dir_count}")
    lines.append(f"- **Max Depth:** {get_max_depth(directory)}")
    lines.append("")
    
    # File type breakdown
    file_types = get_file_type_breakdown(directory)
    if file_types:
        lines.append("## File Type Breakdown")
        lines.append("")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            icon = get_file_icon(ext if ext else '')
            lines.append(f"- {icon} `{ext or 'no extension'}`: {count} files")
        lines.append("")
    
    return "\n".join(lines)


def get_directory_size(directory):
    """Calculate total size of all files in directory."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            try:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
            except (OSError, PermissionError):
                pass
    return total_size


def extract_dates_from_filenames(directory):
    """Extract dates from filenames in the directory."""
    import re
    dates = []
    date_pattern = re.compile(r'(\d{4}[-\.]\d{2}[-\.]\d{2}|\d{2}[-\.]\d{2}[-\.]\d{4})')
    
    for dirpath, dirnames, filenames in os.walk(directory):
        for item in dirnames + filenames:
            match = date_pattern.search(item)
            if match:
                dates.append(match.group(1))
    
    return dates


def count_files_and_dirs(directory):
    """Count files and directories in a directory tree."""
    file_count = 0
    dir_count = 0
    
    for dirpath, dirnames, filenames in os.walk(directory):
        file_count += len(filenames)
        dir_count += len(dirnames)
    
    return file_count, dir_count


def get_max_depth(directory):
    """Get the maximum depth of the directory tree."""
    max_depth = 0
    
    for dirpath, dirnames, filenames in os.walk(directory):
        # Count the depth
        depth = dirpath[len(directory):].count(os.sep)
        max_depth = max(max_depth, depth)
    
    return max_depth


def get_file_type_breakdown(directory):
    """Get a breakdown of file types in the directory."""
    file_types = {}
    
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            file_types[ext] = file_types.get(ext, 0) + 1
    
    return file_types


def main():
    """Main entry point for command-line usage."""
    if len(sys.argv) < 2:
        print("Usage: python filemapper.py <directory> [output_file] [max_depth]")
        print("\nGenerates a Markdown file tree map of the specified directory.")
        print("\nArguments:")
        print("  <directory>    Path to the directory to map")
        print("  [output_file]  Output file path (default: archive_map.md in directory)")
        print("  [max_depth]    Maximum depth to map (default: 6)")
        sys.exit(1)
    
    directory = sys.argv[1]
    
    # Validate directory
    if not os.path.isdir(directory):
        print(f"Error: Directory not found: {directory}", file=sys.stderr)
        sys.exit(1)
    
    # Get max depth
    max_depth = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    
    # Generate the map
    markdown = generate_markdown_map(directory, max_depth)
    
    # Determine output path
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    else:
        output_path = os.path.join(directory, "archive_map.md")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    # Save the map
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f"Successfully generated file map: {output_path}")
    print(f"Mapped {count_files_and_dirs(directory)[0]} files and {count_files_and_dirs(directory)[1]} directories")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
