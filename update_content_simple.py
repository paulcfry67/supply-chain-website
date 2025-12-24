#!/usr/bin/env python3
"""
Simplified script to update content posts to match site_prompt.txt requirements.
"""

import re
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

DISCLAIMER = """<div style="text-align: center; margin-top: 20px;">
AIs can make mistakes. Check important info.
</div>"""

def add_disclaimer_if_missing(content):
    """Add disclaimer at the bottom if not present"""
    if "AIs can make mistakes" not in content:
        content = content.rstrip() + '\n\n' + DISCLAIMER + '\n'
    return content

def add_tag_hyperlinking(content):
    """Add hyperlinks for tag words in the body text"""
    tags = [
        'automotive', 'bottlenecks', 'daily-update', 'distribution',
        'electronics', 'industrial', 'intelligence', 'manufacturing',
        'material-cost', 'preparedness', 'supply-chain', 'threat-assessment'
    ]

    # Sort by length (longest first) to avoid partial matches
    tags_sorted = sorted(tags, key=len, reverse=True)

    for tag in tags_sorted:
        # Create case-insensitive pattern for the tag word
        # Only match whole words, not already in links
        tag_lower = tag.replace('-', ' ')  # "material-cost" -> "material cost"
        tag_pattern = r'\b' + re.escape(tag_lower) + r'\b'

        # Find all occurrences (case-insensitive)
        def replace_tag(match):
            matched_text = match.group(0)
            # Don't replace if already inside a link
            return f'<a href="https://supplychaindaily.news/tags/{tag}/">{matched_text}</a>'

        # Split content by both HTML <a> tags and markdown links to avoid replacing inside them
        parts = re.split(r'(<a\s[^>]*>.*?</a>|\[(?:[^\]]+)\]\([^\)]+\))', content, flags=re.DOTALL)

        for i in range(len(parts)):
            # Only process parts that are not links (even indices)
            if i % 2 == 0:
                # Replace first 3 occurrences in this part
                count = 0
                def limited_replace(match):
                    nonlocal count
                    if count < 3:
                        count += 1
                        return replace_tag(match)
                    return match.group(0)

                parts[i] = re.sub(tag_pattern, limited_replace, parts[i], flags=re.IGNORECASE)

        content = ''.join(parts)

    return content

def get_page_title(url):
    """Fetch the actual title from a webpage"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        title_tag = soup.find('title')

        if title_tag and title_tag.string:
            # Clean up the title
            title = title_tag.string.strip()
            # Remove common site name suffixes
            for separator in [' | ', ' - ', ' – ', ' — ']:
                if separator in title:
                    parts = title.split(separator)
                    # Usually the first part is the article title
                    title = parts[0].strip()
                    break
            return title[:150]  # Limit length
    except Exception as e:
        print(f"    Warning: Could not fetch title for {url}: {e}")

    # Fallback: generate from URL
    parsed = urlparse(url)
    path = parsed.path.strip('/').split('/')[-1]
    if path and len(path) > 3:
        title = path.replace('-', ' ').replace('_', ' ').title()[:80]
        return title
    return parsed.netloc.replace('www.', '')

def fix_existing_link_titles(content):
    """Fix link titles that are just numbers or URL fragments"""
    # Pattern to find <a> tags with poor titles (numbers, fragments, etc.)
    pattern = r'<a href="([^"]+)">([^<]+)</a>'

    def should_fix_title(title, url):
        """Determine if a link title needs fixing"""
        # Fix if title is just numbers
        if title.strip().isdigit():
            return True
        # Fix if title ends with .html or .htm
        if title.strip().lower().endswith(('.html', '.htm')):
            return True
        # Fix if title is very short (less than 10 chars) and URL is long
        if len(title.strip()) < 10 and len(url) > 50:
            return True
        return False

    def replace_link(match):
        url = match.group(1)
        current_title = match.group(2)

        if should_fix_title(current_title, url):
            print(f"    Fetching title for: {url[:60]}...")
            new_title = get_page_title(url)
            return f'<a href="{url}">{new_title}</a>'

        return match.group(0)

    return re.sub(pattern, replace_link, content)

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

            # Fetch the actual page title
            title = get_page_title(url)

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
    content = fix_existing_link_titles(content)
    content = add_tag_hyperlinking(content)
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
