#!/usr/bin/env python3
"""
Fix date mismatches between post filenames and titles.

Example issue:
- Filename: 2025-12-26-supply-chain-update.md
- Title: "Daily Supply Chain News - 2025-12-27"
Should be: "Daily Supply Chain News - 2025-12-26"
"""

import re
import sys
from pathlib import Path


def fix_post_date(filepath):
    """Fix date mismatch in a single post file"""
    filename = filepath.name

    # Extract date from filename (YYYY-MM-DD format)
    match = re.match(r'(\d{4}-\d{2}-\d{2})-supply-chain-update\.md', filename)
    if not match:
        return False

    filename_date = match.group(1)

    # Read file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract title from frontmatter
    title_match = re.search(r'^title:\s*"Daily Supply Chain News - (\d{4}-\d{2}-\d{2})"', content, re.MULTILINE)
    if not title_match:
        print(f"  Skipping {filename} - no matching title format found")
        return False

    title_date = title_match.group(1)

    # Check if dates match
    if filename_date == title_date:
        print(f"  ✓ {filename} - dates match ({filename_date})")
        return False

    # Dates don't match - fix it
    print(f"  ✗ {filename} - MISMATCH:")
    print(f"      Filename date: {filename_date}")
    print(f"      Title date:    {title_date}")

    # Replace title date with filename date
    old_title = f'title: "Daily Supply Chain News - {title_date}"'
    new_title = f'title: "Daily Supply Chain News - {filename_date}"'

    updated_content = content.replace(old_title, new_title)

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(updated_content)

    print(f"      → Fixed to: {filename_date}")
    return True


def main():
    """Main function to process all post files"""
    script_dir = Path(__file__).parent
    content_dir = script_dir / 'content' / 'post'

    if not content_dir.exists():
        print(f"Error: {content_dir} not found")
        return 1

    # Find all supply-chain-update posts
    markdown_files = sorted(content_dir.glob('*-supply-chain-update.md'))

    print(f"Checking {len(markdown_files)} posts for date mismatches...\n")

    fixed_count = 0
    for filepath in markdown_files:
        try:
            if fix_post_date(filepath):
                fixed_count += 1
        except Exception as e:
            print(f"  ✗ Error processing {filepath.name}: {e}")

    print(f"\n{'='*60}")
    print(f"Summary: Fixed {fixed_count} file(s)")
    print(f"{'='*60}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
