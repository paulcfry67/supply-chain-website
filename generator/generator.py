#!/usr/bin/env python3
"""
    generator.py - Python script to generate supply chain daily content

    2025-09-05: Created using Claude code console.
    2025-09-25: First major update
        (adapted from "Daily Prepper Précis Generator" by Will Appleton)
        Modifying with SCDN-specific tags & section headers

    Generates Supply Chain News briefings using Grok API
    For supplychaindaily.news

"""

import os
import sys
import json
import logging
import smtplib
import requests
import argparse
import configparser
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class Config:
    """Configuration settings"""

    # ===== API settings (required first) =====
    grok_api_key: str  # required (no default)

    # Optional defaults
    grok_base_url: str = "https://api.x.ai/v1"
    model: str = "grok-4-0709"
    temperature: float = 0.2  # default is 2, edit to reset to 2
    max_tokens: int = 16000
    presence_penalty: float = 0.1
    frequency_penalty: float = 0.1

    # Live Search parameters (x.ai Live Search guide)
    # Keep simple as Dict[str, Any]; pass {} to accept server defaults.
    search_parameters: Dict[str, Any] = field(default_factory=dict)

    # ===== Processing settings =====
    max_retries: int = 3
    timeout: int = 180  # 3 minutes for API responses
    min_chars: int = 6000   # Minimum ~800 words for comprehensive content
    max_chars: int = 30000  # Increased to allow full comprehensive content without truncation

    # ===== Output settings =====
    output_dir: str = "/tmp/supchain"
    log_level: str = "INFO"

    # ===== Email settings =====
    alert_email: str = "paul.fry@flexresourcing.com"
    smtp_server: str = "smtp.gmail.com"  # Configure as needed
    smtp_port: int = 587
    smtp_username: str = ""  # Set via environment
    smtp_password: str = ""  # Set via environment

    # ===== Prompt file paths =====
    daily_prompt_file: str = "site_prompt.txt"
    system_prompt_file: str = "system_prompt.txt"


class SupplyChainDailyGenerator:
    """Main class for generating daily updates"""

    def __init__(self, config: Config, target_date: Optional[datetime] = None):
        self.config = config
        self.target_date = target_date or datetime.now()
        self.setup_logging()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.grok_api_key}",
            "Content-Type": "application/json"
        })

    def setup_logging(self):
        """Configure logging"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

        # Use output_dir for logs instead of /var/log
        log_dir = Path(self.config.output_dir) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"supply-chain-daily-{datetime.now().strftime('%Y-%m')}.log"

        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file, mode="a"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_daily_prompt(self) -> str:
        """Get the full prompt for generating the supply chain daily news précis"""
        try:
            # Try to read prompt from file first
            prompt_file = Path(__file__).parent / self.config.daily_prompt_file
            if prompt_file.exists():
                self.logger.debug(f"Loading prompt from file: {prompt_file}")
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.logger.warning(f"Prompt file not found: {prompt_file}, using default prompt")
                # Fallback to a minimal default prompt
                return """Generate a comprehensive daily Supply Chain report for the United States.
Include: Executive Summary and Information Operations.
Focus on 24-72 hour news cycle."""
        except Exception as e:
            self.logger.error(f"Error reading prompt file: {str(e)}, using default prompt")
            return """Generate a comprehensive supply chain daily news update for the United States.
Include: Executive Summary and Information Operations.
Focus on 24-72 hour news cycle."""

    def get_system_prompt(self) -> str:
        """Get the system prompt for the AI model"""
        try:
            system_file = Path(__file__).parent / self.config.system_prompt_file
            if system_file.exists():
                self.logger.debug(f"Loading system prompt from file: {system_file}")
                with open(system_file, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.logger.warning(f"System prompt file not found: {system_file}, using default")
        except Exception as e:
            self.logger.error(f"Error reading system prompt file: {str(e)}, using default")

        # Default system prompt
        return """You are an elite OSINT analyst specializing in threat assessment for U.S. national security. Your role is to produce professional, unbiased daily threat intelligence briefings following strict analytical standards.

Key requirements:
- Follow the exact format structure provided in the prompt
- Use current date and real-time threat information
- Maintain objectivity without political bias
- Provide specific, actionable intelligence
- Cross-reference multiple credible sources
- Use professional intelligence community language
- Focus on 24-72 hour threat window
- Include confidence assessments and source reliability ratings"""

    def get_top_story_url(self) -> Optional[str]:
        """Read the top story URL from topstory.txt (last line)"""
        try:
            topstory_file = Path(__file__).parent / "topstory.txt"
            if topstory_file.exists():
                with open(topstory_file, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
                    if lines:
                        url = lines[-1]  # Get last non-empty line
                        if url.startswith('http'):
                            self.logger.info(f"Top story URL from topstory.txt: {url}")
                            return url
            self.logger.warning("No valid top story URL found in topstory.txt")
            return None
        except Exception as e:
            self.logger.error(f"Error reading topstory.txt: {str(e)}")
            return None

    def generate_content(self) -> Optional[str]:
        """Generate the daily précis using Grok API"""
        # Get current date for the prompt
        today = self.target_date
        date_str = today.strftime("%Y-%m-%d")
        day_name = today.strftime("%A")

        # Get top story URL selected by Paul Fry
        top_story_url = self.get_top_story_url()
        top_story_instruction = ""
        if top_story_url:
            top_story_instruction = f"""
IMPORTANT - TOP STORY:
Paul Fry has selected this URL as today's top supply chain story: {top_story_url}
Please analyze this article and incorporate relevant insights from it into your content where appropriate.
The homepage Top Story section will be automatically updated with this URL.
"""

        # Get base prompt and add current date instruction
        base_prompt = self.get_daily_prompt()
        prompt = f"""CRITICAL: Today's date is {date_str} ({day_name}).

You MUST generate content for TODAY'S DATE: {date_str}
All dates in your response should reflect this current date.
Do NOT use placeholder dates like 2023-10-10 or October 10, 2023.

{top_story_instruction}

{base_prompt}"""

        for attempt in range(1, self.config.max_retries + 1):
            try:
                self.logger.info(f"Attempt {attempt}/{self.config.max_retries}: Generating content via Grok API (timeout: {self.config.timeout}s)")

                # Base payload
                payload: Dict[str, Any] = {
                    "messages": [
                        {
                            "role": "system",
                            "content": self.get_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "model": self.config.model,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                    "stream": False
                }

                # Add penalty parameters only for models that support them
                # grok-4 models don't support presence/frequency penalties
                if not self.config.model.startswith("grok-4"):
                    payload["presence_penalty"] = self.config.presence_penalty
                    payload["frequency_penalty"] = self.config.frequency_penalty
                    self.logger.debug(f"Added penalty parameters for model {self.config.model}")
                else:
                    self.logger.debug(f"Skipping penalty parameters for model {self.config.model}")

                # Note: search_parameters removed as live search is deprecated
                # Use Agent Tools API instead if search functionality needed

                response = self.session.post(
                    f"{self.config.grok_base_url}/chat/completions",
                    json=payload,
                    timeout=self.config.timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    # Defensive extraction in case of streaming-like content
                    content = data["choices"][0]["message"]["content"]

                    # Validate content length
                    char_count = len(content)
                    if char_count < self.config.min_chars:
                        self.logger.warning(f"Content too short ({char_count} chars), retrying...")
                        continue
                    elif char_count > self.config.max_chars:
                        self.logger.warning(f"Content too long ({char_count} chars), truncating...")
                        content = content[:self.config.max_chars] + "\n\n*[Content truncated due to length limits]*"

                    self.logger.info(f"Content generated successfully ({len(content)} characters)")
                    return content

                else:
                    self.logger.error(f"API request failed: {response.status_code} - {response.text}")

            except requests.exceptions.Timeout:
                self.logger.error(f"Request timed out (attempt {attempt})")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed (attempt {attempt}): {str(e)}")
            except KeyError as e:
                self.logger.error(f"Unexpected response format (attempt {attempt}): {str(e)}")
            except Exception as e:
                self.logger.error(f"Unexpected error (attempt {attempt}): {str(e)}")

        return None

    def get_page_info_for_top_story(self, url: str) -> dict:
        """Fetch page title, source, and synopsis for top story URL"""
        try:
            import requests
            from bs4 import BeautifulSoup
            from urllib.parse import urlparse

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Get title
            title = "Top Story"
            title_tag = soup.find('title')
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
                # Remove site name suffixes
                for separator in [' | ', ' - ', ' – ', ' — ']:
                    if separator in title:
                        parts = title.split(separator)
                        title = parts[0].strip()
                        break
                title = title[:150]

            # Get source from domain
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            source_name = domain.split('.')[0].title()
            source = f"{source_name} ({domain})"

            # Get synopsis from meta description or first paragraph
            synopsis = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            if meta_desc and meta_desc.get('content'):
                synopsis = meta_desc.get('content').strip()[:300]
            else:
                # Try to get first paragraph
                paragraphs = soup.find_all('p')
                for p in paragraphs[:5]:
                    text = p.get_text().strip()
                    if len(text) > 50:  # Skip short paragraphs
                        synopsis = text[:300]
                        break

            if not synopsis:
                synopsis = "Read the full article for details on this important supply chain development."

            return {
                'title': title,
                'source': source,
                'synopsis': synopsis
            }

        except Exception as e:
            self.logger.warning(f"Could not fetch info for {url}: {e}")

            # Fallback
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            path = parsed.path.strip('/').split('/')[-1]

            title = path.replace('-', ' ').title()[:80] if path else "Top Story"
            source_name = domain.split('.')[0].title()

            return {
                'title': title,
                'source': f"{source_name} ({domain})",
                'synopsis': "Read the full article for details on this important supply chain development."
            }

    def update_homepage_top_story(self, content: str) -> bool:
        """Create Top Story from topstory.txt URL and update homepage"""
        try:
            import re

            # Get the top story URL from topstory.txt
            top_story_url = self.get_top_story_url()
            if not top_story_url:
                self.logger.warning("No top story URL available")
                return False

            # Fetch the page info (title, source, synopsis)
            page_info = self.get_page_info_for_top_story(top_story_url)

            # Create Top Story div with the new format
            top_story_html = f'''<div id="top-story">
<p><strong>Today's Top Story:</strong><br>
{page_info['title']}</p>

<p><em>Source: {page_info['source']}</em></p>

<p>{page_info['synopsis']}</p>

<p style="color: red;"><a href="{top_story_url}" style="color: red;">Read the whole story at {page_info['source'].split('(')[0].strip()}</a></p>
</div>'''

            # Read the homepage file
            homepage_path = Path("../content/_index.md")
            if not homepage_path.exists():
                self.logger.error(f"Homepage file not found: {homepage_path}")
                return False

            with open(homepage_path, 'r', encoding='utf-8') as f:
                homepage_content = f.read()

            # Replace the Top Story section
            updated_homepage = re.sub(
                r'<div id="top-story">.*?</div>',
                top_story_html,
                homepage_content,
                flags=re.DOTALL
            )

            # Write back to homepage
            with open(homepage_path, 'w', encoding='utf-8') as f:
                f.write(updated_homepage)

            self.logger.info(f"Updated homepage Top Story with URL: {top_story_url}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update homepage Top Story: {str(e)}")
            return False

    def save_content(self, content: str) -> Optional[str]:
        """Save content to markdown file with proper naming"""
        try:
            # Update the homepage with Top Story from topstory.txt
            self.update_homepage_top_story(content)

            # Ensure output directory exists
            Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)

            # Generate filename
            today = self.target_date.strftime("%Y-%m-%d")
            filename = f"{today}-supply-chain-update.md"
            filepath = Path(self.config.output_dir) / filename

            # Check if file exists and log overwrite
            if filepath.exists():
                self.logger.info(f"Overwriting existing file: {filepath}")

            # Add frontmatter and format content
            formatted_content = self.format_markdown(content)

            # Write file (will overwrite if exists)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(formatted_content)

            self.logger.info(f"Content saved to: {filepath}")
            return str(filepath)

        except Exception as e:
            self.logger.error(f"Failed to save content: {str(e)}")
            return None

    def format_markdown(self, content: str) -> str:
        """Format content with proper markdown structure and frontmatter"""
        now = self.target_date.replace(tzinfo=timezone.utc)
        today = now.strftime("%Y-%m-%d")

        # Map/normalize sections for Hugo validation
        sections_mapping = {
            "Physical Security Threats": "Physical Security",
            "Cyber Threats": "Cyber Threats",
            "Natural and Environmental Hazards": "Public Health",
            "Economic and Supply Chain Threats": "Economic and Supply Chain",
            "Near-Term Threat Expansions": "Key Indicators"
        }

        processed_content = content
        for old_section, new_section in sections_mapping.items():
            if f"## {old_section}" in processed_content or f"### {old_section}" in processed_content:
                processed_content = processed_content.replace(f"### {old_section}", f"## {new_section}")
                processed_content = processed_content.replace(f"#### {old_section}", f"## {new_section}")
                processed_content = processed_content.replace(f"## {old_section}", f"## {new_section}")
            elif old_section in processed_content and new_section not in processed_content:
                processed_content = processed_content.replace(old_section, f"## {new_section}\n\n{old_section}")

        frontmatter = f"""---
title: "Daily Supply Chain News - {today}"
date: {now.isoformat()}
draft: false
categories: ["Electronics", "Automotive", "Aerospace", "Transportation"]
tags: ["material cost", "bottlenecks", "distribution", "manufacturing"]
author: "Supply Chain Analysis Team"
---

"""
        return frontmatter + processed_content

    def send_alert_email(self, subject: str, message: str):
        """Send alert email on failure"""
        try:
            if not self.config.smtp_username or not self.config.smtp_password:
                self.logger.warning("SMTP credentials not configured, skipping email alert")
                return

            msg = MIMEMultipart()
            msg['From'] = self.config.smtp_username
            msg['To'] = self.config.alert_email
            msg['Subject'] = subject

            msg.attach(MIMEText(message, 'plain'))

            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)

            self.logger.info(f"Alert email sent to {self.config.alert_email}")

        except Exception as e:
            self.logger.error(f"Failed to send alert email: {str(e)}")

    def rebuild_taxonomy(self) -> bool:
        """Rebuild taxonomy-based content using update_content.py"""
        try:
            self.logger.info("Rebuilding taxonomy-based hyperlinks...")

            # Get path to update_content.py (in parent directory)
            script_path = Path(__file__).parent.parent / 'update_content.py'

            if not script_path.exists():
                self.logger.warning(f"update_content.py not found at {script_path}")
                return False

            # Import and run the update script
            import sys
            sys.path.insert(0, str(script_path.parent))

            try:
                import update_content
                # Reload tags in case config changed
                update_content.TAGS = update_content.load_tags_from_config()

                # Run the main update function
                update_content.main()
                self.logger.info("Taxonomy rebuild completed successfully")
                return True

            except Exception as e:
                self.logger.error(f"Error running update_content.py: {e}")
                return False

        except Exception as e:
            self.logger.error(f"Error in rebuild_taxonomy: {e}")
            return False

    def run(self) -> int:
        """Main execution method"""
        self.logger.info("Starting Daily Supply Chain generation")

        try:
            # Generate content
            content = self.generate_content()
            if not content:
                error_msg = "Failed to generate content after all retry attempts"
                self.logger.error(error_msg)
                self.send_alert_email(
                    "Supply Chain Generation Failed",
                    f"Error: {error_msg}\nTime: {datetime.now()}\nCheck logs for details."
                )
                return 1

            # Save content
            filepath = self.save_content(content)
            if not filepath:
                error_msg = "Failed to save generated content"
                self.logger.error(error_msg)
                self.send_alert_email(
                    "Supply Chain Save Failed",
                    f"Error: {error_msg}\nTime: {datetime.now()}\nContent was generated but could not be saved."
                )
                return 1

            # Rebuild taxonomy (hyperlinks based on taxonomy_config.json)
            self.rebuild_taxonomy()

            self.logger.info(f"Daily Précis generation completed successfully")
            self.logger.info(f"File ready for ingest: {filepath}")

            return 0

        except Exception as e:
            error_msg = f"Unexpected error in main execution: {str(e)}"
            self.logger.error(error_msg)
            self.send_alert_email(
                "Supply Chain Critical Error",
                f"Error: {error_msg}\nTime: {datetime.now()}\nCheck logs immediately."
            )
            return 1


def load_config(config_file: Optional[str] = None) -> Config:
    """Load configuration from config file, then environment variables"""
    # Set default values (leave API key blank by default; prefer env/secret)
    config_values: Dict[str, Any] = {
        'search_parameters': {},
        'grok_api_key': os.environ.get('GROK_API_KEY', ''),
        'grok_base_url': 'https://api.x.ai/v1',
        'model': 'grok-4-0709',
        'temperature': 0.2,
        'max_tokens': 16000,
        'presence_penalty': 0.1,
        'frequency_penalty': 0.1,
        'max_retries': 3,
        'timeout': 180,
        'min_chars': 4800,
        'max_chars': 80000,
        'output_dir': '/tmp/supchain',
        'log_level': 'INFO',
        'alert_email': 'paul.fry@flexresourcing.com',
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_username': '',
        'smtp_password': '',
        'daily_prompt_file': 'site_prompt.txt',
        'system_prompt_file': 'system_prompt.txt'
    }

    # Try to load from config file
    if config_file is None:
        config_file = Path(__file__).parent / "generator.config"
    else:
        config_file = Path(config_file)

    if config_file.exists():
        parser = configparser.ConfigParser()
        parser.read(config_file)

        # Update values from config file
        for section in parser.sections():
            for key, value in parser.items(section):
                config_key = key.lower()

                if config_key in ['max_retries', 'timeout', 'min_chars', 'max_chars', 'smtp_port', 'max_tokens']:
                    config_values[config_key] = int(value)
                elif config_key in ['temperature', 'presence_penalty', 'frequency_penalty']:
                    config_values[config_key] = float(value)
                elif config_key == 'search_parameters':
                    # Expect JSON object in config; fall back to {}
                    try:
                        parsed = json.loads(value)
                        if isinstance(parsed, dict):
                            config_values[config_key] = parsed
                    except Exception:
                        pass
                else:
                    config_values[config_key] = value

    # Override with environment variables if they exist
    env_mappings: Dict[str, Any] = {
        'GROK_API_KEY': 'grok_api_key',
        'GROK_BASE_URL': 'grok_base_url',
        'MODEL': 'model',
        'DAILY_OUTPUT_DIR': 'output_dir',
        'DAILY_MAX_RETRIES': ('max_retries', int),
        'DAILY_TIMEOUT': ('timeout', int),
        'SEARCH_PARAMETERS': 'search_parameters',  # JSON string
        'ALERT_EMAIL': 'alert_email',
        'SMTP_SERVER': 'smtp_server',
        'SMTP_PORT': ('smtp_port', int),
        'SMTP_USERNAME': 'smtp_username',
        'SMTP_PASSWORD': 'smtp_password',
        'LOG_LEVEL': 'log_level',
        'MAX_CHARS': ('max_chars', int),
        'MIN_CHARS': ('min_chars', int)
    }

    for env_key, mapping in env_mappings.items():
        if env_key in os.environ:
            if isinstance(mapping, tuple):
                config_key, converter = mapping
                config_values[config_key] = converter(os.environ[env_key])
            else:
                if mapping == 'search_parameters':
                    # Parse JSON from env; ignore if invalid
                    try:
                        parsed = json.loads(os.environ[env_key])
                        if isinstance(parsed, dict):
                            config_values[mapping] = parsed
                        # If not dict, ignore silently
                    except Exception:
                        pass
                else:
                    config_values[mapping] = os.environ[env_key]

    return Config(**config_values)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Generate Daily Supply Chain News")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--config-check", action="store_true", help="Check configuration and exit")
    parser.add_argument("--dry-run", action="store_true", help="Generate content but don't save")
    parser.add_argument("--date", type=str, help="Generate for specific date (YYYY-MM-DD)")

    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    if args.config_check:
        print("Configuration Check:")
        print(f"  Config File: {args.config or 'generator.config (default)'}")
        print(f"  Grok API Key: {'✓ Set' if config.grok_api_key else '✗ Missing'}")
        print(f"  Model: {config.model}")
        print(f"  Temperature: {config.temperature}")
        print(f"  Max Tokens: {config.max_tokens}")
        print(f"  Output Directory: {config.output_dir}")
        print(f"  Alert Email: {config.alert_email}")
        print(f"  Live Search Parameters: {json.dumps(config.search_parameters) if config.search_parameters else '{}'}")
        print(f"  SMTP Configured: {'✓ Yes' if config.smtp_username else '✗ No'}")
        print(f"  Prompt Files:")
        print(f"    - Daily: {config.daily_prompt_file}")
        print(f"    - System: {config.system_prompt_file}")
        return 0

    if not config.grok_api_key:
        print("ERROR: GROK_API_KEY environment variable (or config) is required")
        return 1

    # Parse target date if provided
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
            print(f"Generating content for date: {args.date}")
        except ValueError:
            print(f"ERROR: Invalid date format '{args.date}'. Use YYYY-MM-DD format.")
            return 1

    # Run generator
    generator = SupplyChainDailyGenerator(config, target_date)

    if args.dry_run:
        content = generator.generate_content()
        if content:
            print("\n" + "=" * 50)
            print("GENERATED CONTENT (DRY RUN):")
            print("=" * 50)
            print(generator.format_markdown(content))
            print("=" * 50)
            return 0
        else:
            print("Failed to generate content")
            return 1

    return generator.run()


if __name__ == "__main__":
    sys.exit(main())
