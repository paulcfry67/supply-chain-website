# Taxonomy Configuration Guide

This guide explains how to edit `taxonomy_config.json` to update your site's tags and categories.

## Overview

The `taxonomy_config.json` file has three main sections for both tags and categories:
- **current**: Auto-generated snapshot of existing taxonomy (read-only)
- **new**: Your desired taxonomy structure (EDIT THIS)
- **mappings**: How to migrate from old to new (EDIT THIS)

## How to Make Changes

### 1. Adding a New Tag or Category

In the `new` section, add a new entry:

```json
"new-tag-name": {
  "slug": "new-tag-name",           // URL-friendly version (lowercase, hyphens)
  "display_name": "New Tag Name",    // How it appears on the site
  "hyperlink": true,                 // (tags only) Auto-link in content?
  "description": "What this tag means"
}
```

### 2. Renaming a Tag or Category

1. Update the entry in the `new` section with the new name
2. Add a mapping in the `mappings` section:

```json
"mappings": {
  "old-name": "new-name"
}
```

### 3. Removing a Tag or Category

1. Delete the entry from the `new` section
2. In `mappings`, either:
   - Map it to another tag: `"old-tag": "replacement-tag"`
   - Map it to null to remove: `"old-tag": null`

### 4. Splitting One Tag into Multiple

In the `mappings` section, use an array:

```json
"mappings": {
  "broad-topic": ["specific-topic-1", "specific-topic-2"]
}
```

### 5. Merging Multiple Tags into One

In the `mappings` section:

```json
"mappings": {
  "old-tag-1": "consolidated-tag",
  "old-tag-2": "consolidated-tag",
  "old-tag-3": "consolidated-tag"
}
```

## Current State Summary

### Tags (12 total)
**Heavily used (72 posts each):**
- bottlenecks
- distribution
- manufacturing
- material cost (note: displays as "material-cost" in URLs)

**Lightly used (1 post each):**
- automotive, daily-update, electronics, industrial, intelligence, preparedness, supply-chain, threat-assessment

### Categories (7 total)
**Heavily used:**
- Aerospace (73 posts)
- Automotive (73 posts)
- Electronics (73 posts)
- Transportation (72 posts)

**Lightly used (1 post each):**
- Logistics, Manufacturing, Supply Chain

## Tag Hyperlinking

Tags with `"hyperlink": true` will be automatically linked in content. For example, if you have a tag "automotive", the word "automotive" in your content will become a link to the automotive tag page.

**Best practices:**
- Set `hyperlink: true` for topic/industry tags
- Set `hyperlink: false` for meta tags like "daily-update"
- Don't hyperlink category names as tags (causes confusion)

## Example Editing Session

Let's say you want to:
1. Add a new "tariffs" tag
2. Rename "material cost" to "costs"
3. Remove "daily-update" tag
4. Merge "Aerospace" and "Transportation" categories into "Transportation & Aerospace"

### Step 1: Edit `tags.new`

```json
"costs": {
  "slug": "costs",
  "display_name": "Costs",
  "hyperlink": true,
  "description": "Cost-related supply chain issues"
},
"tariffs": {
  "slug": "tariffs",
  "display_name": "Tariffs",
  "hyperlink": true,
  "description": "Trade tariffs and their impact"
}
```

Remove the "daily-update" entry entirely.

### Step 2: Edit `tags.mappings`

```json
"mappings": {
  "material cost": "costs",
  "daily-update": null,
  // ... keep other mappings unchanged
}
```

### Step 3: Edit `categories.new`

```json
"Transportation & Aerospace": {
  "slug": "transportation-aerospace",
  "display_name": "Transportation & Aerospace",
  "description": "Transportation, logistics, and aerospace industries"
}
```

Remove the individual "Aerospace" and "Transportation" entries.

### Step 4: Edit `categories.mappings`

```json
"mappings": {
  "Aerospace": "Transportation & Aerospace",
  "Transportation": "Transportation & Aerospace",
  // ... keep other mappings unchanged
}
```

## After Editing

Once you're done editing `taxonomy_config.json`, let me know and I'll:

1. **Validate** your changes (check for errors)
2. **Preview** what will change (show you a diff)
3. **Execute** the migration:
   - Update all post frontmatter
   - Update `update_content.py` tag list
   - Update content hyperlinks
   - Rebuild Hugo site
4. **Commit and deploy** the changes

## Tips

- **Start small**: Make a few changes, test, then make more
- **Check usage counts**: High-count items need careful consideration
- **Keep categories focused**: 5-10 categories is ideal
- **Make tags specific**: More granular than categories
- **Use consistent naming**: Choose either "Supply Chain" or "supply-chain" style and stick with it

## Questions?

Just ask! I'm here to help you refine your taxonomy structure.
