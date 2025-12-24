#!/usr/bin/env python3
"""
Simplified script to update content posts to match site_prompt.txt requirements.
"""

import re
from pathlib import Path

DISCLAIMER = """<div style="text-align: center; margin-top: 20px;">
AIs can make mistakes. Check important info.
</div>"""

def add_disclaimer_if_missing(content):
    """Add disclaimer at the bottom if not present"""
    if "AIs can make mistakes" not in content:
        content = content.rstrip() + '\n\n' + DISCLAIMER + '\n'
    return content

def convert_raw_urls_to_links(content):
    """Convert raw URLs (not in <a> tags) to proper links"""
    # Find URLs that are on their own line starting with - or *
    # Pattern: - https://example.com or * https://example.com
    lines = content.split('\n')
    updated_lines = []

    for line in lines:
        # Check if line is a list item with a raw URL
        match = re.match(r'^(\s*[-*]\s+)(https?://[^\s<]+)$', line)
        if match:
            indent = match.group(1)
            url = match.group(2)

            # Generate a simple title from URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            path = parsed.path.strip('/').split('/')[-1]

            if path and len(path) > 3:
                title = path.replace('-', ' ').replace('_', ' ').title()[:80]
            else:
                title = domain

            # Create the link
            link = f'{indent}<a href="{url}">{title}</a>'
            updated_lines.append(link)
        else:
            updated_lines.append(line)

    return '\n'.join(updated_lines)

def remove_old_sections(content):
    """Remove outdated section headers"""
    # Remove standalone title at start
    content = re.sub(r'^#\s+[^\n]+\n+', '', content)

    # Remove "News Summary" section header (but keep content)
    content = re.sub(r'##?\s+News Summary[:\s][^\n]*\n+', '', content)

    # Remove "Industry-Specific Updates" header
    content = re.sub(r'##?\s+Industry-Specific Updates\s*\n+', '', content)

    # Remove "Impact Analysis" section header
    content = re.sub(r'##?\s+Impact Analysis[:\s][^\n]*\n+', '', content)

    # Remove "Recommendations" section header
    content = re.sub(r'##?\s+Recommendations[^\n]*\n+', '', content)

    return content

def update_file(filepath):
    """Update a single content file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        full_content = f.read()

    # Split frontmatter and content
    parts = full_content.split('<content>')
    if len(parts) != 2:
        return False, "No <content> tag"

    frontmatter = parts[0]
    content_parts = parts[1].split('</content>')
    if len(content_parts) != 2:
        return False, "No </content> tag"

    content = content_parts[0]
    trailing = content_parts[1]

    # Apply updates
    original_content = content
    content = remove_old_sections(content)
    content = convert_raw_urls_to_links(content)
    content = add_disclaimer_if_missing(content)

    # Check if anything changed
    if content == original_content:
        return False, "No changes needed"

    # Reassemble and write
    updated = frontmatter + '<content>' + content + '</content>' + trailing

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(updated)

    return True, "Updated"

def main():
    import sys

    if len(sys.argv) > 1:
        # Process single file
        filepath = Path(sys.argv[1])
        if not filepath.exists():
            print(f"Error: {filepath} not found")
            return

        success, msg = update_file(filepath)
        print(f"{filepath.name}: {msg}")
    else:
        # Process all files
        content_dir = Path('content/post')
        markdown_files = sorted(content_dir.glob('*.md'))

        print(f"Processing {len(markdown_files)} files...\n")

        updated_count = 0
        for filepath in markdown_files:
            try:
                success, msg = update_file(filepath)
                if success:
                    print(f"✓ {filepath.name}")
                    updated_count += 1
                else:
                    print(f"  {filepath.name}: {msg}")
            except Exception as e:
                print(f"✗ {filepath.name}: {e}")

        print(f"\nUpdated {updated_count} files")

if __name__ == '__main__':
    main()
