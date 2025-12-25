#!/usr/bin/env python3
"""
Add Construction and Chemicals categories to posts that have those sections
"""

import re
from pathlib import Path

def update_post_categories(post_file):
    """Add Construction/Chemicals categories if sections exist"""
    with open(post_file, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Check for sections
    has_construction = bool(re.search(r'###?\s+Construction', content, re.IGNORECASE))
    has_chemicals = bool(re.search(r'###?\s+Chemicals?', content, re.IGNORECASE))

    if not (has_construction or has_chemicals):
        return False

    # Extract current categories
    cat_match = re.search(r'^categories:\s*\[(.*?)\]', content, re.MULTILINE)
    if not cat_match:
        return False

    cats_str = cat_match.group(1)
    categories = [c.strip().strip('"').strip("'") for c in cats_str.split(',')]

    changes = []

    # Add Construction if needed
    if has_construction and 'Construction' not in categories:
        categories.append('Construction')
        changes.append('Added Construction')

    # Add Chemicals if needed
    if has_chemicals and 'Chemicals' not in categories:
        categories.append('Chemicals')
        changes.append('Added Chemicals')

    if not changes:
        return False

    # Update categories in content
    new_cats_str = ', '.join([f'"{c}"' for c in categories])
    content = re.sub(
        r'^categories:\s*\[.*?\]',
        f'categories: [{new_cats_str}]',
        content,
        count=1,
        flags=re.MULTILINE
    )

    # Write back
    with open(post_file, 'w', encoding='utf-8') as f:
        f.write(content)

    return True, changes

def main():
    posts_dir = Path('content/post')
    updated_count = 0

    print("Updating posts with new categories...\n")

    for post_file in sorted(posts_dir.glob('*.md')):
        result = update_post_categories(post_file)
        if result:
            updated, changes = result if isinstance(result, tuple) else (result, [])
            if updated:
                updated_count += 1
                print(f"✓ {post_file.name}: {', '.join(changes)}")

    print(f"\nUpdated {updated_count} posts")

if __name__ == '__main__':
    main()
