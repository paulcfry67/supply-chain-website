# Supply Chain Daily Website

Hugo-powered supply chain intelligence website with AI-driven content generation using Grok API.

## Quick Start

### 1. Generate Content
```bash
python3 generator.py
```

### 2. Start Development Server
```bash
hugo server --buildDrafts
```
Visit http://localhost:1313

### 3. Build for Production
```bash
hugo --minify
```

## Configuration

Edit `generator.config` to customize:
- Grok API settings
- Content generation parameters
- Output directories
- Email alerts

## Content Generation

The generator uses two prompt files:
- `generator/system_prompt.txt` - AI role definition
- `generator/site_prompt.txt` - Content structure template

Variables replaced during generation:
- `{{CURRENT_SUPPLY_CHAIN_DATA}}` - Latest supply chain data
- `{{PREVIOUS_SITE_CONTENT}}` - Previous day's content

## Daily Automation

Set up cron job for daily content generation:
```bash
# Daily at 6 AM
0 6 * * * cd /path/to/supchain && python3 generator.py
```

## Architecture

- **Hugo Framework**: Static site generator with Hugo News theme
- **Grok API**: AI content generation via X.ai
- **Python Generator**: Automated content creation and formatting
- **Markdown Posts**: Hugo-compatible content with frontmatter

## Commands

- `python3 generator.py --config-check` - Verify configuration
- `python3 generator.py --dry-run` - Test generation without saving
- `hugo server` - Start development server
- `hugo --buildDrafts` - Build including draft content