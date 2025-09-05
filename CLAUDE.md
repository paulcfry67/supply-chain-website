# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is "supchain" - a supply chain content generation system. The project focuses on generating daily website content about supply chain issues in manufacturing and distribution, with emphasis on USA automotive manufacturing.

## Architecture

The project has a minimal structure with a `generator/` directory containing prompt templates for AI content generation:

- `generator/system_prompt.txt` - Defines the AI assistant role for supply chain economics and logistics
- `generator/site_prompt.txt` - Contains detailed instructions for generating daily website content, including structure, SEO requirements, and content guidelines

## Content Generation System

The system uses a template-based approach with two input variables:
- `CURRENT_SUPPLY_CHAIN_DATA` - Latest supply chain information 
- `PREVIOUS_SITE_CONTENT` - Previous day's content for continuity

Content structure follows a specific HTML format:
1. Daily Supply Chain Update heading
2. Top Supply Chain News
3. Industry-Specific Updates (Automotive, Electronics, Industrial Equipment)
4. Impact Analysis
5. Recommendations
6. Conclusion

Target content length: 1000-1500 words with SEO optimization.

## Development Notes

- No package.json, build system, or traditional development commands present
- This appears to be a prompt engineering project rather than a traditional codebase
- Focus is on content generation templates and prompts for supply chain analysis