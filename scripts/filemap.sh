#!/bin/bash

MAP_NAME="FILEMAP.md"

{
    echo "# Case File Inventory"
    echo "## Case Reference: 25FA152"
    echo "Generated on: $(date)"
    echo ""
    echo "## Full Directory Structure"
    echo "\`\`\`"
    # Scans everything from where you run it
    tree -F --dirsfirst
    echo "\`\`\`"
    echo ""
    echo "## Recursive Document Index (Chapters)"
    echo ""

    # Recursively find all PDFs starting from the current directory (.)
    find . -type f -name "*.pdf" | sort | while read -r f; do
        # Ignore the result file if it's a PDF
        if [[ "$(basename "$f")" == "filemap.pdf" ]]; then continue; fi
        
        echo "### $f"
        
        # Extract bookmarks from deep subfolders
        CHAPTERS=$(pdftk "$f" dump_data_utf8 2>/dev/null | grep "BookmarkTitle:" | sed 's/BookmarkTitle: //')

        if [[ -n "$CHAPTERS" ]]; then
            echo "Contains internal chapters:"
            while read -r title; do
                echo "* $title"
            done <<< "$CHAPTERS"
        else
            echo "* (Single Document - No internal chapters found)"
        fi
        echo ""
    done
} > "$MAP_NAME"

echo "---------------------------------------"
echo "Success! Deep Filemap created: $MAP_NAME"
