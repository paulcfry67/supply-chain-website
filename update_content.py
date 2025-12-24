#!/usr/bin/env python3
"""
Script to update all content posts to match current site_prompt.txt requirements.
Updates:
1. Add disclaimer at bottom if missing
2. Add tag hyperlinking throughout content
3. Convert raw URLs to proper <a> tags with titles
4. Remove outdated sections
5. Clean up content structure
"""

import re
import os
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import time

# Available tags from the site
TAGS = [
    'bottlenecks', 'distribution', 'electronics', 'industrial', 'intelligence', 'manufacturing', 'material-cost', 'preparedness', 'threat-assessment'
]

DISCLAIMER = """<div style="text-align: center; margin-top: 20px;">
AIs can make mistakes. Check important info.
</div>"""

def get_page_title(url):
    """Fetch the actual page title from the <title> tag"""
    try:
        # Add a small delay to be respectful to servers
        time.sleep(0.5)

        # Use more complete browser-like headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()

        # Parse HTML and extract title
        soup = BeautifulSoup(response.content, 'html.parser')
        title_tag = soup.find('title')

        if title_tag and title_tag.string:
            title = title_tag.string.strip()
            # Clean up common title suffixes and separators
            title = re.sub(r'\s*[\|\-]\s*(Reuters|Bloomberg|WSJ|Supply Chain Dive|Logistics Manager|Tom\'?s Hardware|Torque News|Automotive News|Manufacturing Dive|Boise State University).*$', '', title, flags=re.IGNORECASE)
            # Remove extra whitespace
            title = ' '.join(title.split())
            return title[:200]  # Limit length

        # Fallback: generate title from URL
        return generate_title_from_url(url)

    except requests.exceptions.HTTPError as e:
        print(f"  Warning: HTTP error for {url}: {e.response.status_code}")
        return generate_title_from_url(url)
    except Exception as e:
        print(f"  Warning: Could not fetch title for {url}: {type(e).__name__}")
        return generate_title_from_url(url)

def generate_title_from_url(url):
    """Generate a readable title from URL when page cannot be fetched"""
    parsed = urlparse(url)
    domain = parsed.netloc.replace('www.', '').split('.')[0].title()

    # Try to extract meaningful info from path
    path = parsed.path.strip('/').split('/')[-1]
    if path and not path.endswith(('.html', '.htm', '.php')):
        # Clean up slug
        words = path.replace('-', ' ').replace('_', ' ')
        # Remove date patterns
        words = re.sub(r'\d{4}-\d{2}-\d{2}', '', words)
        words = re.sub(r'\d{8}', '', words)
        words = ' '.join(words.split()).title()
        if len(words) > 10:  # If meaningful text exists
            return words[:100]

    return f"{domain} Article"

def add_tag_links(content):
    """Add hyperlinks for tag words in content"""
    # Sort tags by length (longest first) to avoid partial matches
    sorted_tags = sorted(TAGS, key=len, reverse=True)

    for tag in sorted_tags:
        # Skip if tag is already heavily linked
        tag_link = f'tags/{tag}/'
        if content.count(tag_link) >= 3:
            continue

        # Create variations of the tag (capitalized, etc.)
        tag_variations = [tag, tag.capitalize(), tag.title()]

        for tag_var in tag_variations:
            # Simple pattern to match the tag word as a standalone word
            pattern = r'\b(' + re.escape(tag_var) + r')\b'

            # Find all matches
            matches = list(re.finditer(pattern, content))

            # Replace up to 3 instances, carefully checking context
            replacements_made = 0
            offset = 0

            for match in matches:
                if replacements_made >= 3:
                    break

                start = match.start() + offset
                end = match.end() + offset

                # Get context around the match
                context_start = max(0, start - 300)
                context_before = content[context_start:start]
                context_after = content[end:min(len(content), end + 50)]

                # Skip if inside HTML tag or attribute
                # Count open/close brackets
                open_count = context_before.count('<')
                close_count = context_before.count('>')
                if open_count > close_count:
                    continue

                # Skip if inside an href attribute
                last_href = context_before.rfind('href="')
                last_close_quote = context_before.rfind('">')
                if last_href > last_close_quote and last_href >= 0:
                    continue

                # Skip if inside an existing <a> tag
                last_open_a = context_before.rfind('<a ')
                last_close_a = context_before.rfind('</a>')
                if last_open_a > last_close_a and last_open_a >= 0:
                    continue

                # Skip if the closing </a> is very close after
                if '</a>' in context_after[:10]:
                    continue

                # Skip if this is part of a URL or file path
                if '://' in context_before[-10:] or '/' in context_before[-3:]:
                    continue

                # Replace this instance
                matched_text = content[start:end]
                replacement = f'<a href="https://supplychaindaily.news/tags/{tag}/">{matched_text}</a>'

                content = content[:start] + replacement + content[end:]

                # Update offset for subsequent matches
                offset += len(replacement) - (end - start)
                replacements_made += 1

    return content

def convert_raw_urls(content):
    """Convert raw URLs to proper <a> tags with titles"""
    # Pattern to find raw URLs - must not be inside href="" already
    # Also avoid URLs that are already inside <a> tags
    url_pattern = r'(?<!href=")(?<!src=")(https?://[^\s<>"]+)(?!</a>)'

    # Find all URLs first
    urls_found = []
    for match in re.finditer(url_pattern, content):
        url = match.group(0)
        pos = match.start()

        # Check if this URL is inside an <a> tag by looking backward
        before = content[max(0, pos-500):pos]
        # Count opening and closing <a> tags
        open_tags = before.count('<a ')
        close_tags = before.count('</a>')

        # If more opening tags than closing tags, we're inside a link
        if open_tags > close_tags:
            continue

        # Check if URL is already part of href attribute
        if 'href="' in before[-10:]:
            continue

        urls_found.append((url, pos))

    # Process URLs in reverse order to maintain positions
    for url, pos in reversed(urls_found):
        # Clean up URL (remove trailing punctuation)
        clean_url = url.rstrip('.,;:)')

        # Get title
        title = get_page_title(clean_url)

        # Create link tag
        link_tag = f'<a href="{clean_url}">{title}</a>'

        # Replace this specific occurrence
        content = content[:pos] + link_tag + content[pos + len(url):]

    return content

def clean_content_structure(content):
    """Remove outdated sections and clean up structure"""
    # Remove title if it exists at the start of content
    content = re.sub(r'^#\s+[^\n]+\n+', '', content, count=1)

    # Remove "News Summary" section and its content
    content = re.sub(r'##?\s+News Summary[:\s][^\n]*\n+.*?(?=##|\Z)', '', content, flags=re.DOTALL)

    # Remove "Impact Analysis" section
    content = re.sub(r'##?\s+Impact Analysis[:\s][^\n]*\n+.*?(?=##|\Z)', '', content, flags=re.DOTALL)

    # Remove "Recommendations" section
    content = re.sub(r'##?\s+Recommendations[^\n]*\n+.*?(?=##|\Z)', '', content, flags=re.DOTALL)

    # Remove "Industry-Specific Updates" header if it exists
    content = re.sub(r'##?\s+Industry-Specific Updates\s*\n+', '', content)

    return content

def add_disclaimer_if_missing(content):
    """Add disclaimer at the bottom if not present"""
    if "AIs can make mistakes" not in content:
        # Remove trailing whitespace and add disclaimer
        content = content.rstrip() + '\n\n' + DISCLAIMER + '\n'
    return content

def update_content_file(filepath):
    """Update a single content file"""
    print(f"Processing {filepath.name}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        full_content = f.read()

    # Split frontmatter and content
    parts = full_content.split('<content>')
    if len(parts) != 2:
        print(f"  Skipping - no <content> tag found")
        return

    frontmatter = parts[0]
    content_parts = parts[1].split('</content>')
    if len(content_parts) != 2:
        print(f"  Skipping - no </content> tag found")
        return

    content = content_parts[0]
    trailing = content_parts[1]

    # Apply updates
    content = clean_content_structure(content)
    content = convert_raw_urls(content)
    content = add_tag_links(content)
    content = add_disclaimer_if_missing(content)

    # Reassemble file
    updated = frontmatter + '<content>' + content + '</content>' + trailing

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(updated)

    print(f"  ✓ Updated {filepath.name}")

def main():
    """Main function to process all content files"""
    content_dir = Path('content/post')

    if not content_dir.exists():
        print(f"Error: {content_dir} not found")
        return

    markdown_files = sorted(content_dir.glob('*.md'))

    print(f"Found {len(markdown_files)} markdown files to process\n")

    for filepath in markdown_files:
        try:
            update_content_file(filepath)
        except Exception as e:
            print(f"  ✗ Error processing {filepath.name}: {e}")

    print(f"\n✓ Processing complete!")

if __name__ == '__main__':
    main()
