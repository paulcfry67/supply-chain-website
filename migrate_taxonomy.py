#!/usr/bin/env python3
"""
Taxonomy Migration Script
Migrates tags and categories based on taxonomy_config.json
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def load_config():
    """Load taxonomy configuration"""
    with open('taxonomy_config.json', 'r') as f:
        return json.load(f)

def validate_config(config):
    """Validate configuration file"""
    errors = []

    # Check required sections
    if 'tags' not in config:
        errors.append("Missing 'tags' section")
    if 'categories' not in config:
        errors.append("Missing 'categories' section")

    # Validate tag mappings
    if 'mappings' in config['tags']:
        for old_tag, new_tag in config['tags']['mappings'].items():
            if old_tag.startswith('_'):  # Skip metadata fields
                continue
            if new_tag and new_tag not in config['tags']['new']:
                errors.append(f"Tag mapping '{old_tag}' -> '{new_tag}' but '{new_tag}' not in new tags")

    # Validate category mappings
    if 'mappings' in config['categories']:
        for old_cat, new_cat in config['categories']['mappings'].items():
            if old_cat.startswith('_'):  # Skip metadata fields
                continue
            if new_cat and new_cat not in config['categories']['new']:
                errors.append(f"Category mapping '{old_cat}' -> '{new_cat}' but '{new_cat}' not in new categories")

    return errors

def preview_changes(config):
    """Preview what will change"""
    print("=" * 70)
    print("MIGRATION PREVIEW")
    print("=" * 70)

    # Tag changes
    print("\n📌 TAG CHANGES:")
    print("-" * 70)

    tag_changes = []
    for old_tag, new_tag in config['tags']['mappings'].items():
        if old_tag.startswith('_'):  # Skip metadata
            continue
        if old_tag != new_tag:
            tag_changes.append(f"  • '{old_tag}' → '{new_tag}'")

    if tag_changes:
        for change in tag_changes:
            print(change)
    else:
        print("  No tag renames")

    # Check for removed tags
    current_tags = set(k for k in config['tags']['current'].keys() if not k.startswith('_'))
    new_tags = set(k for k in config['tags']['new'].keys() if not k.startswith('_'))
    # Filter out metadata keys from mappings
    mapped_tags = set(v for k, v in config['tags']['mappings'].items()
                      if not k.startswith('_') and v)

    removed_tags = current_tags - mapped_tags
    added_tags = new_tags - current_tags

    if removed_tags:
        print(f"\n  ⚠️  REMOVED TAGS ({len(removed_tags)}):")
        for tag in sorted(removed_tags):
            tag_data = config['tags']['current'].get(tag, {})
            count = tag_data.get('count', 0) if isinstance(tag_data, dict) else 0
            print(f"     - {tag} ({count} posts)")

    if added_tags:
        print(f"\n  ✨ NEW TAGS ({len(added_tags)}):")
        for tag in sorted(added_tags):
            print(f"     + {tag}")

    # Category changes
    print("\n\n📂 CATEGORY CHANGES:")
    print("-" * 70)

    cat_changes = []
    for old_cat, new_cat in config['categories']['mappings'].items():
        if old_cat.startswith('_'):  # Skip metadata
            continue
        if old_cat != new_cat:
            cat_changes.append(f"  • '{old_cat}' → '{new_cat}'")

    if cat_changes:
        for change in cat_changes:
            print(change)
    else:
        print("  No category renames")

    # Check for removed categories
    current_cats = set(k for k in config['categories']['current'].keys() if not k.startswith('_'))
    new_cats = set(k for k in config['categories']['new'].keys() if not k.startswith('_'))
    # Filter out metadata keys from mappings
    mapped_cats = set(v for k, v in config['categories']['mappings'].items()
                      if not k.startswith('_') and v)

    removed_cats = current_cats - mapped_cats
    added_cats = new_cats - current_cats

    if removed_cats:
        print(f"\n  ⚠️  REMOVED CATEGORIES ({len(removed_cats)}):")
        for cat in sorted(removed_cats):
            cat_data = config['categories']['current'].get(cat, {})
            count = cat_data.get('count', 0) if isinstance(cat_data, dict) else 0
            print(f"     - {cat} ({count} posts)")

    if added_cats:
        print(f"\n  ✨ NEW CATEGORIES ({len(added_cats)}):")
        for cat in sorted(added_cats):
            print(f"     + {cat}")

    # Summary
    print("\n\n📊 IMPACT SUMMARY:")
    print("-" * 70)
    posts_dir = Path('content/post')
    post_count = len(list(posts_dir.glob('*.md')))
    print(f"  Total posts to update: {post_count}")
    print(f"  Tags in new taxonomy: {len(new_tags)}")
    print(f"  Categories in new taxonomy: {len(new_cats)}")

    # Hyperlinking changes
    hyperlink_tags = [tag for tag, data in config['tags']['new'].items()
                      if not tag.startswith('_') and isinstance(data, dict) and data.get('hyperlink', True)]
    print(f"  Tags with auto-hyperlinking: {len(hyperlink_tags)}")

    print("\n" + "=" * 70)

def migrate_post_frontmatter(post_file, tag_mappings, cat_mappings):
    """Migrate tags and categories in a post's frontmatter"""
    with open(post_file, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content
    changes_made = []

    # Migrate tags
    tags_match = re.search(r'^tags:\s*\[(.*?)\]', content, re.MULTILINE)
    if tags_match:
        tags_str = tags_match.group(1)
        old_tags = [t.strip().strip('"').strip("'") for t in tags_str.split(',')]
        new_tags = []

        for tag in old_tags:
            if tag in tag_mappings:
                mapped = tag_mappings[tag]
                if mapped:  # Not null
                    if isinstance(mapped, list):
                        new_tags.extend(mapped)
                    else:
                        new_tags.append(mapped)
                    if tag != mapped:
                        changes_made.append(f"tag: {tag} → {mapped}")
            else:
                new_tags.append(tag)

        # Remove duplicates while preserving order
        seen = set()
        new_tags = [t for t in new_tags if not (t in seen or seen.add(t))]

        # Replace in content
        new_tags_str = ', '.join([f'"{t}"' for t in new_tags])
        content = re.sub(
            r'^tags:\s*\[.*?\]',
            f'tags: [{new_tags_str}]',
            content,
            count=1,
            flags=re.MULTILINE
        )

    # Migrate categories
    cat_match = re.search(r'^categories:\s*\[(.*?)\]', content, re.MULTILINE)
    if cat_match:
        cats_str = cat_match.group(1)
        old_cats = [c.strip().strip('"').strip("'") for c in cats_str.split(',')]
        new_cats = []

        for cat in old_cats:
            if cat in cat_mappings:
                mapped = cat_mappings[cat]
                if mapped:  # Not null
                    if isinstance(mapped, list):
                        new_cats.extend(mapped)
                    else:
                        new_cats.append(mapped)
                    if cat != mapped:
                        changes_made.append(f"category: {cat} → {mapped}")
            else:
                new_cats.append(cat)

        # Remove duplicates while preserving order
        seen = set()
        new_cats = [c for c in new_cats if not (c in seen or seen.add(c))]

        # Replace in content
        new_cats_str = ', '.join([f'"{c}"' for c in new_cats])
        content = re.sub(
            r'^categories:\s*\[.*?\]',
            f'categories: [{new_cats_str}]',
            content,
            count=1,
            flags=re.MULTILINE
        )

    # Write back if changed
    if content != original_content:
        with open(post_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, changes_made

    return False, []

def update_update_content_script(config):
    """Update the TAGS list in update_content.py"""
    script_path = Path('update_content.py')

    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Get new tags that should be hyperlinked (skip metadata keys)
    hyperlink_tags = sorted([
        tag for tag, data in config['tags']['new'].items()
        if not tag.startswith('_') and isinstance(data, dict) and data.get('hyperlink', True)
    ])

    # Create new TAGS list
    tags_list = ', '.join([f"'{tag}'" for tag in hyperlink_tags])
    new_tags_section = f"TAGS = [\n    {tags_list}\n]"

    # Replace TAGS section
    content = re.sub(
        r'TAGS = \[.*?\]',
        new_tags_section,
        content,
        flags=re.DOTALL
    )

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✓ Updated update_content.py with {len(hyperlink_tags)} tags")

def main():
    """Main migration function"""
    print("\n🚀 Taxonomy Migration Script\n")

    # Load configuration
    print("Loading taxonomy_config.json...")
    config = load_config()

    # Validate
    print("Validating configuration...")
    errors = validate_config(config)
    if errors:
        print("\n❌ VALIDATION ERRORS:")
        for error in errors:
            print(f"   - {error}")
        return 1
    print("  ✓ Configuration valid")

    # Preview changes
    preview_changes(config)

    # Confirm before proceeding
    dry_run = config.get('migration', {}).get('dry_run', True)
    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made")
        print("Set 'migration.dry_run': false in taxonomy_config.json to execute")
        return 0

    # Execute migration
    print("\n\n🔄 EXECUTING MIGRATION...")
    print("=" * 70)

    # Get mappings
    tag_mappings = config['tags']['mappings']
    cat_mappings = config['categories']['mappings']

    # Update posts
    print("\n1. Updating post frontmatter...")
    posts_dir = Path('content/post')
    updated_count = 0

    for post_file in sorted(posts_dir.glob('*.md')):
        updated, changes = migrate_post_frontmatter(post_file, tag_mappings, cat_mappings)
        if updated:
            updated_count += 1
            if changes:
                print(f"  ✓ {post_file.name}: {', '.join(changes[:2])}")

    print(f"\n  Updated {updated_count} posts")

    # Update update_content.py
    print("\n2. Updating update_content.py...")
    update_update_content_script(config)

    print("\n" + "=" * 70)
    print("✅ MIGRATION COMPLETE!")
    print("\nNext steps:")
    print("  1. Review changes with: git diff")
    print("  2. Rebuild site with: hugo")
    print("  3. Commit and push changes")

    return 0

if __name__ == '__main__':
    exit(main())
