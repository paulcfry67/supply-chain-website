#!/usr/bin/env python3
"""
Supply Chain Daily Content Generator
Generates daily supply chain intelligence briefings using Grok API
For supplychaindaily.com
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
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration settings"""
    # API settings
    grok_api_key: str
    grok_base_url: str = "https://api.x.ai/v1"
    model: str = "grok-2-1212"
    temperature: float = 0.3
    max_tokens: int = 10000
    presence_penalty: float = 0.1
    frequency_penalty: float = 0.1
    
    # Processing settings
    max_retries: int = 3
    timeout: int = 180  # 3 minutes for API responses
    min_chars: int = 6000   # Minimum ~1000 words for comprehensive content
    max_chars: int = 15000  # Maximum ~1500 words as per prompts
    
    # Output settings
    output_dir: str = "./content/posts"
    log_level: str = "INFO"
    
    # Email settings
    alert_email: str = ""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    
    # Prompt file paths
    site_prompt_file: str = "generator/site_prompt.txt"
    system_prompt_file: str = "generator/system_prompt.txt"
    
    # Hugo settings
    hugo_build: bool = True
    content_section: str = "posts"


class SupplyChainGenerator:
    """Main class for generating daily supply chain content"""
    
    def __init__(self, config: Config):
        self.config = config
        self.setup_logging()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.grok_api_key}",
            "Content-Type": "application/json"
        })
    
    def setup_logging(self):
        """Configure logging"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Create logs directory in project root
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"supply-chain-generator-{datetime.now().strftime('%Y-%m')}.log"
        
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_site_prompt(self) -> str:
        """Get the full prompt for generating supply chain content"""
        try:
            prompt_file = Path(self.config.site_prompt_file)
            if prompt_file.exists():
                self.logger.debug(f"Loading site prompt from file: {prompt_file}")
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.logger.warning(f"Site prompt file not found: {prompt_file}, using default")
                return self._get_default_site_prompt()
        except Exception as e:
            self.logger.error(f"Error reading site prompt file: {str(e)}, using default")
            return self._get_default_site_prompt()
    
    def _get_default_site_prompt(self) -> str:
        """Default prompt if file not found"""
        return """Generate comprehensive daily supply chain content following this structure:

<content>
<h1>Daily Supply Chain Update: [Current Date]</h1>

<h2>Top Supply Chain News</h2>
[News summary content]

<h2>Industry-Specific Updates</h2>
<h3>Automotive Sector</h3>
[Automotive industry update]

<h3>Electronics Sector</h3>
[Electronics industry update]

<h3>Industrial Equipment Sector</h3>
[Industrial equipment industry update]

<h2>Impact Analysis</h2>
[Impact analysis content]

<h2>Recommendations</h2>
[Recommendations content]

<h2>Conclusion</h2>
[Brief conclusion and outlook]
</content>

Target 1000-1500 words with SEO optimization for supply chain keywords."""
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the AI model"""
        try:
            system_file = Path(self.config.system_prompt_file)
            if system_file.exists():
                self.logger.debug(f"Loading system prompt from file: {system_file}")
                with open(system_file, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.logger.warning(f"System prompt file not found: {system_file}, using default")
        except Exception as e:
            self.logger.error(f"Error reading system prompt file: {str(e)}, using default")
        
        # Default system prompt
        return """You are an AI assistant fully versed in supply chain economics and practical logistics of supply chain for industry. You are tasked with generating content for a daily-updated website focused on supply chain issues in the manufacturing and distribution business sectors, with an emphasis on USA automotive manufacturing. Your goal is to create informative, engaging, and SEO-friendly content based on the latest supply chain data and previous site content."""
    
    def get_previous_content(self) -> str:
        """Get previous day's content for continuity"""
        try:
            # Look for the most recent post in the content directory
            content_dir = Path(self.config.output_dir)
            if not content_dir.exists():
                return "No previous content available."
            
            # Find the most recent markdown file
            markdown_files = list(content_dir.glob("*.md"))
            if not markdown_files:
                return "No previous content available."
            
            # Sort by modification time and get the most recent
            latest_file = max(markdown_files, key=lambda p: p.stat().st_mtime)
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Remove frontmatter for cleaner previous content
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        return parts[2].strip()
                return content.strip()
                
        except Exception as e:
            self.logger.warning(f"Could not read previous content: {str(e)}")
            return "No previous content available."
    
    def get_current_supply_chain_data(self) -> str:
        """Get current supply chain data - placeholder for future data integration"""
        # This would be enhanced to pull from actual data sources
        today = datetime.now().strftime("%Y-%m-%d")
        return f"""Current supply chain data for {today}:
- Latest industry reports and news
- Manufacturing capacity utilization
- Material availability status
- Transportation and logistics updates
- Economic indicators affecting supply chains
- Regulatory changes and policy updates

[Note: This is a placeholder - in production this would pull from actual data feeds, APIs, and industry sources]"""
    
    def generate_content(self) -> Optional[str]:
        """Generate the daily supply chain content using Grok API"""
        today = datetime.now()
        date_str = today.strftime("%Y-%m-%d")
        day_name = today.strftime("%A")
        
        # Get template data
        site_prompt = self.get_site_prompt()
        current_data = self.get_current_supply_chain_data()
        previous_content = self.get_previous_content()
        
        # Replace template variables
        prompt = site_prompt.replace("{{CURRENT_SUPPLY_CHAIN_DATA}}", current_data)
        prompt = prompt.replace("{{PREVIOUS_SITE_CONTENT}}", previous_content)
        
        # Add current date instruction
        final_prompt = f"""CRITICAL: Today's date is {date_str} ({day_name}).

You MUST generate content for TODAY'S DATE: {date_str}
All dates in your response should reflect this current date.
Do NOT use placeholder dates.

{prompt}"""
        
        for attempt in range(1, self.config.max_retries + 1):
            try:
                self.logger.info(f"Attempt {attempt}/{self.config.max_retries}: Generating content via Grok API")
                
                payload = {
                    "messages": [
                        {
                            "role": "system",
                            "content": self.get_system_prompt()
                        },
                        {
                            "role": "user", 
                            "content": final_prompt
                        }
                    ],
                    "model": self.config.model,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens,
                    "stream": False
                }
                
                # Add penalty parameters only for models that support them
                if not self.config.model.startswith("grok-4"):
                    payload["presence_penalty"] = self.config.presence_penalty
                    payload["frequency_penalty"] = self.config.frequency_penalty
                
                response = self.session.post(
                    f"{self.config.grok_base_url}/chat/completions",
                    json=payload,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
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
            except Exception as e:
                self.logger.error(f"Unexpected error (attempt {attempt}): {str(e)}")
        
        return None

    def save_content(self, content: str) -> Optional[str]:
        """Save content to Hugo markdown file"""
        try:
            # Ensure output directory exists
            Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            today = datetime.now().strftime("%Y-%m-%d")
            filename = f"{today}-supply-chain-update.md"
            filepath = Path(self.config.output_dir) / filename
            
            if filepath.exists():
                self.logger.info(f"Overwriting existing file: {filepath}")
            
            # Format content for Hugo
            formatted_content = self.format_hugo_markdown(content)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            
            self.logger.info(f"Content saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to save content: {str(e)}")
            return None

    def format_hugo_markdown(self, content: str) -> str:
        """Format content with proper Hugo frontmatter and markdown"""
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        
        # Extract title from content if possible
        title = f"Daily Supply Chain Update - {today}"
        if "<h1>" in content:
            import re
            title_match = re.search(r'<h1[^>]*>(.*?)</h1>', content)
            if title_match:
                title = title_match.group(1).strip()
                # Remove HTML tags
                title = re.sub(r'<[^>]+>', '', title)
        
        # Convert HTML to markdown-friendly format
        processed_content = self.html_to_markdown(content)
        
        frontmatter = f"""---
title: "{title}"
date: {now.isoformat()}
draft: false
categories: ["Supply Chain", "Manufacturing", "Logistics"]
tags: ["supply-chain", "automotive", "electronics", "industrial", "daily-update"]
author: "Supply Chain Analysis Team"
description: "Daily intelligence briefing on supply chain issues affecting manufacturing and distribution"
---

"""
        return frontmatter + processed_content

    def html_to_markdown(self, html_content: str) -> str:
        """Convert HTML content to markdown format"""
        import re
        
        # Remove <content> tags if present
        content = re.sub(r'</?content[^>]*>', '', html_content)
        
        # Convert headers
        content = re.sub(r'<h1[^>]*>(.*?)</h1>', r'# \1', content, flags=re.DOTALL)
        content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', content, flags=re.DOTALL)
        content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', content, flags=re.DOTALL)
        content = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1', content, flags=re.DOTALL)
        
        # Convert paragraphs
        content = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', content, flags=re.DOTALL)
        
        # Convert lists
        content = re.sub(r'<ul[^>]*>', '', content)
        content = re.sub(r'</ul>', '\n', content)
        content = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', content, flags=re.DOTALL)
        
        # Convert bold and italic
        content = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', content, flags=re.DOTALL)
        content = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', content, flags=re.DOTALL)
        
        # Clean up extra whitespace
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = content.strip()
        
        return content

    def build_hugo_site(self) -> bool:
        """Build the Hugo site after content generation"""
        if not self.config.hugo_build:
            return True
            
        try:
            import subprocess
            result = subprocess.run(['hugo'], capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                self.logger.info("Hugo site built successfully")
                return True
            else:
                self.logger.error(f"Hugo build failed: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to build Hugo site: {str(e)}")
            return False

    def send_alert_email(self, subject: str, message: str):
        """Send alert email on failure"""
        try:
            if not self.config.smtp_username or not self.config.smtp_password or not self.config.alert_email:
                self.logger.warning("Email settings not configured, skipping alert")
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

    def run(self) -> int:
        """Main execution method"""
        self.logger.info("Starting Supply Chain Daily content generation")
        
        try:
            # Generate content
            content = self.generate_content()
            if not content:
                error_msg = "Failed to generate content after all retry attempts"
                self.logger.error(error_msg)
                self.send_alert_email(
                    "Supply Chain Content Generation Failed",
                    f"Error: {error_msg}\nTime: {datetime.now()}\nCheck logs for details."
                )
                return 1
            
            # Save content
            filepath = self.save_content(content)
            if not filepath:
                error_msg = "Failed to save generated content"
                self.logger.error(error_msg)
                self.send_alert_email(
                    "Supply Chain Content Save Failed", 
                    f"Error: {error_msg}\nTime: {datetime.now()}\nContent was generated but could not be saved."
                )
                return 1
            
            # Build Hugo site
            if not self.build_hugo_site():
                self.logger.warning("Hugo build failed, but content was saved successfully")
            
            self.logger.info(f"Supply Chain Daily content generation completed successfully")
            self.logger.info(f"File ready: {filepath}")
            
            return 0
            
        except Exception as e:
            error_msg = f"Unexpected error in main execution: {str(e)}"
            self.logger.error(error_msg)
            self.send_alert_email(
                "Supply Chain Generator Critical Error",
                f"Error: {error_msg}\nTime: {datetime.now()}\nCheck logs immediately."
            )
            return 1


def load_config(config_file: Optional[str] = None) -> Config:
    """Load configuration from config file and environment variables"""
    config_values = {
        'grok_api_key': '',
        'grok_base_url': 'https://api.x.ai/v1',
        'model': 'grok-2-1212',
        'temperature': 0.3,
        'max_tokens': 10000,
        'presence_penalty': 0.1,
        'frequency_penalty': 0.1,
        'max_retries': 3,
        'timeout': 180,
        'min_chars': 6000,
        'max_chars': 15000,
        'output_dir': './content/posts',
        'log_level': 'INFO',
        'alert_email': '',
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_username': '',
        'smtp_password': '',
        'site_prompt_file': 'generator/site_prompt.txt',
        'system_prompt_file': 'generator/system_prompt.txt',
        'hugo_build': True,
        'content_section': 'posts'
    }
    
    # Try to load from config file
    if config_file is None:
        config_file = Path("generator.config")
    else:
        config_file = Path(config_file)
    
    if config_file.exists():
        parser = configparser.ConfigParser()
        parser.read(config_file)
        
        for section in parser.sections():
            for key, value in parser.items(section):
                config_key = key.lower()
                
                # Type conversion
                if config_key in ['max_retries', 'timeout', 'min_chars', 'max_chars', 'smtp_port', 'max_tokens']:
                    config_values[config_key] = int(value)
                elif config_key in ['temperature', 'presence_penalty', 'frequency_penalty']:
                    config_values[config_key] = float(value)
                elif config_key in ['hugo_build']:
                    config_values[config_key] = value.lower() in ['true', '1', 'yes']
                else:
                    config_values[config_key] = value
    
    # Environment variable overrides
    env_mappings = {
        'GROK_API_KEY': 'grok_api_key',
        'GROK_BASE_URL': 'grok_base_url',
        'OUTPUT_DIR': 'output_dir',
        'MAX_RETRIES': ('max_retries', int),
        'TIMEOUT': ('timeout', int),
        'ALERT_EMAIL': 'alert_email',
        'SMTP_USERNAME': 'smtp_username',
        'SMTP_PASSWORD': 'smtp_password',
        'LOG_LEVEL': 'log_level',
        'HUGO_BUILD': ('hugo_build', lambda x: x.lower() in ['true', '1', 'yes'])
    }
    
    for env_key, mapping in env_mappings.items():
        if env_key in os.environ:
            if isinstance(mapping, tuple):
                config_key, converter = mapping
                config_values[config_key] = converter(os.environ[env_key])
            else:
                config_values[mapping] = os.environ[env_key]
    
    return Config(**config_values)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Generate Supply Chain Daily Content")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--config-check", action="store_true", help="Check configuration and exit")
    parser.add_argument("--dry-run", action="store_true", help="Generate content but don't save")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    
    if args.config_check:
        print("Configuration Check:")
        print(f"  Config File: {args.config or 'generator.config (default)'}")
        print(f"  Grok API Key: {'✓ Set' if config.grok_api_key else '✗ Missing'}")
        print(f"  Model: {config.model}")
        print(f"  Temperature: {config.temperature}")
        print(f"  Max Tokens: {config.max_tokens}")
        print(f"  Output Directory: {config.output_dir}")
        print(f"  Hugo Build: {'✓ Enabled' if config.hugo_build else '✗ Disabled'}")
        print(f"  Prompt Files:")
        print(f"    - Site: {config.site_prompt_file}")
        print(f"    - System: {config.system_prompt_file}")
        return 0
    
    if not config.grok_api_key:
        print("ERROR: GROK_API_KEY environment variable is required")
        return 1
    
    generator = SupplyChainGenerator(config)
    
    if args.dry_run:
        content = generator.generate_content()
        if content:
            print("\n" + "="*50)
            print("GENERATED CONTENT (DRY RUN):")
            print("="*50)
            print(generator.format_hugo_markdown(content))
            print("="*50)
            return 0
        else:
            print("Failed to generate content")
            return 1
    
    return generator.run()


if __name__ == "__main__":
    sys.exit(main())