#!/usr/bin/env python3
"""
Script to update existing post pages with:
1. Fix link titles to use actual page <title> tags instead of URL-derived text
2. Update taxonomy tag links
3. Do NOT regenerate content - only fix links and taxonomy

Usage: python3 update_post_page.py [filename or pattern]
Examples:
  python3 update_post_page.py  # Process all posts
  python3 update_post_page.py 2025-12-15-supply-chain-update.md  # Process specific file
"""

import re
import sys
import json
import time
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup


def load_tags_from_config():
    """Load tags from taxonomy_config.json"""
    config_path = Path(__file__).parent / 'taxonomy_config.json'
    if not config_path.exists():
        # Fallback to default tags if config doesn't exist
        return ['bottlenecks', 'distribution', 'electronics', 'industrial',
                'intelligence', 'manufacturing', 'material-cost', 'preparedness',
                'threat-assessment']

    with open(config_path, 'r') as f:
        config = json.load(f)

    # Get tags where hyperlink is enabled
    tags = [
        tag for tag, data in config.get('tags', {}).items()
        if not tag.startswith('_') and isinstance(data, dict) and data.get('hyperlink', True)
    ]
    return sorted(tags)


TAGS = load_tags_from_config()


def get_page_title(url):
    """Fetch the actual page title from the <title> tag"""
    try:
        # Add a small delay to be respectful to servers
        time.sleep(0.5)

        # Use browser-like headers
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
            title = re.sub(r'\s*[\|\-]\s*(Reuters|Bloomberg|WSJ|Supply Chain Dive|Logistics Manager|Tom\'?s Hardware|Torque News|Automotive News|Manufacturing Dive|Boise State University|CNBC|SCMP).*$', '', title, flags=re.IGNORECASE)
            # Remove extra whitespace
            title = ' '.join(title.split())
            return title[:200]  # Limit length

        # Fallback: generate title from URL
        return generate_title_from_url(url)

    except requests.exceptions.HTTPError as e:
        print(f"  Warning: HTTP error for {url}: {e.response.status_code}")
        return None  # Return None to keep existing title
    except Exception as e:
        print(f"  Warning: Could not fetch title for {url}: {type(e).__name__}")
        return None  # Return None to keep existing title


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


def looks_like_url_derived_title(title, url):
    """Check if a link title looks like it was derived from the URL instead of the page title"""
    # Signs of URL-derived title:
    # 1. Contains date patterns like "2025 11 24" (spaces between date parts)
    # 2. Title is very similar to URL slug (when dashes are replaced with spaces)
    # 3. Contains numbers without proper formatting
    # 4. All title case with odd capitalization

    # Extract URL slug
    parsed = urlparse(url)
    slug = parsed.path.strip('/').split('/')[-1]
    slug = re.sub(r'\.(html?|php)$', '', slug)

    # Remove common prefixes/suffixes
    slug_words = slug.replace('-', ' ').lower()
    title_words = title.lower()

    # Check for date pattern with spaces (e.g., "2025 11 24")
    if re.search(r'\d{4}\s+\d{1,2}\s+\d{1,2}', title):
        return True

    # Check if title is very similar to slug (70% similarity)
    slug_set = set(slug_words.split())
    title_set = set(title_words.split())
    if slug_set and title_set:
        overlap = len(slug_set & title_set) / len(slug_set)
        if overlap > 0.7:
            return True

    return False


def fix_link_titles(content):
    """Fix existing link titles to use actual page titles instead of URL-derived text"""
    # Pattern to find <a href="URL">TITLE</a>
    link_pattern = r'<a\s+href="(https?://[^"]+)">([^<]+)</a>'

    links_to_fix = []
    for match in re.finditer(link_pattern, content):
        url = match.group(1)
        current_title = match.group(2)

        # Skip internal links (supplychaindaily.news)
        if 'supplychaindaily.news' in url:
            continue

        # Skip if title looks good (doesn't look URL-derived)
        if not looks_like_url_derived_title(current_title, url):
            continue

        links_to_fix.append((match.start(), match.end(), url, current_title))

    if not links_to_fix:
        return content

    print(f"  Found {len(links_to_fix)} links with URL-derived titles to fix")

    # Process in reverse order to maintain positions
    for start, end, url, old_title in reversed(links_to_fix):
        print(f"  Fixing: {old_title[:50]}...")
        new_title = get_page_title(url)

        if new_title and new_title != old_title:
            new_link = f'<a href="{url}">{new_title}</a>'
            content = content[:start] + new_link + content[end:]
            print(f"    → {new_title[:50]}...")
        else:
            print(f"    → Kept existing (could not fetch)")

    return content


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


def update_post_file(filepath):
    """Update a single post file with fixed links and updated taxonomy"""
    print(f"Processing {filepath.name}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        full_content = f.read()

    # Split frontmatter and content
    parts = full_content.split('<content>')
    if len(parts) != 2:
        print(f"  Skipping - no <content> tag found")
        return False

    frontmatter = parts[0]
    content_parts = parts[1].split('</content>')
    if len(content_parts) != 2:
        print(f"  Skipping - no </content> tag found")
        return False

    content = content_parts[0]
    trailing = content_parts[1]

    # Track if changes were made
    original_content = content

    # Fix link titles first (most important)
    content = fix_link_titles(content)

    # Then update taxonomy tag links
    content = add_tag_links(content)

    # Check if any changes were made
    if content == original_content:
        print(f"  No changes needed")
        return False

    # Reassemble file
    updated = frontmatter + '<content>' + content + '</content>' + trailing

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(updated)

    print(f"  ✓ Updated {filepath.name}")
    return True


def main():
    """Main function to process post files"""
    script_dir = Path(__file__).parent
    content_dir = script_dir / 'content' / 'post'

    if not content_dir.exists():
        print(f"Error: {content_dir} not found")
        return 1

    # Determine which files to process
    if len(sys.argv) > 1:
        # Process specific file or pattern
        pattern = sys.argv[1]
        if pattern.endswith('.md'):
            # Specific file
            markdown_files = [content_dir / pattern]
            if not markdown_files[0].exists():
                print(f"Error: File not found: {markdown_files[0]}")
                return 1
        else:
            # Pattern
            markdown_files = sorted(content_dir.glob(f'{pattern}*.md'))
    else:
        # Process all markdown files
        markdown_files = sorted(content_dir.glob('*.md'))

    print(f"Found {len(markdown_files)} markdown files to process\n")

    updated_count = 0
    for filepath in markdown_files:
        try:
            if update_post_file(filepath):
                updated_count += 1
        except Exception as e:
            print(f"  ✗ Error processing {filepath.name}: {e}")

    print(f"\n✓ Processing complete! Updated {updated_count} files.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
