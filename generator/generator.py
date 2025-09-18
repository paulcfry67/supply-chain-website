#!/usr/bin/env python3
"""
Supply Chain Daily Content Generator
Generates daily supply chain intelligence briefings using Grok API
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
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


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
    
    # Live Search settings
    search_mode: str = "auto"  # "auto", "on", "off"
    search_sources: List[str] = field(default_factory=lambda: ["web", "news", "x"])
    max_search_results: int = 20
    return_citations: bool = True
    search_from_date: str = ""  # ISO8601 format: YYYY-MM-DD
    search_to_date: str = ""    # ISO8601 format: YYYY-MM-DD
    excluded_x_handles: List[str] = field(default_factory=list)
    post_favorite_count: int = 0    # Min favorites for X posts
    post_view_count: int = 0        # Min views for X posts
    rss_links: List[str] = field(default_factory=list)
    
    # Processing settings
    max_retries: int = 3
    timeout: int = 180  # 3 minutes for API responses
    min_chars: int = 6000   # Minimum ~1000 words for comprehensive content
    max_chars: int = 15000  # Maximum ~1500 words as per prompts
    
    # Output settings
    output_dir: str = "../content/posts"
    log_level: str = "INFO"
    
    # Email settings
    alert_email: str = ""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    
    # Prompt file paths
    site_prompt_file: str = "site_prompt.txt"
    system_prompt_file: str = "system_prompt.txt"
    
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
        
        # Create logs directory in parent directory 
        log_dir = Path("../logs")
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
    
    def build_search_parameters(self) -> Dict[str, Any]:
        """Build search parameters for live search functionality"""
        search_params = {
            "mode": self.config.search_mode
        }
        
        if self.config.search_mode != "off":
            # Note: Not including sources parameter to use defaults (web, news, x)
            # The API has specific object structure requirements for sources
            
            if self.config.max_search_results != 20:  # Only set if different from default
                search_params["max_search_results"] = self.config.max_search_results
            
            if not self.config.return_citations:  # Only set if different from default
                search_params["return_citations"] = self.config.return_citations
            
            # Date range filtering
            if self.config.search_from_date:
                search_params["from_date"] = self.config.search_from_date
            if self.config.search_to_date:
                search_params["to_date"] = self.config.search_to_date
            
            # X-specific filtering
            if self.config.excluded_x_handles:
                search_params["excluded_x_handles"] = self.config.excluded_x_handles
            if self.config.post_favorite_count > 0:
                search_params["post_favorite_count"] = self.config.post_favorite_count
            if self.config.post_view_count > 0:
                search_params["post_view_count"] = self.config.post_view_count
            
            # RSS links
            if self.config.rss_links:
                search_params["links"] = self.config.rss_links
        
        return search_params

    def get_current_supply_chain_data(self) -> str:
        """Get current supply chain data - now enhanced with live search context"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        # With live search enabled, this data will be supplemented by real-time information
        base_context = f"""Current supply chain analysis context for {today}:

FOCUS AREAS FOR LIVE SEARCH:
- Latest supply chain disruptions and news affecting manufacturing
- Semiconductor availability and automotive production updates
- Port congestion, shipping costs, and logistics developments
- Raw material price changes (steel, aluminum, rare earth elements)
- Trade policy changes and regulatory updates affecting supply chains
- Economic indicators: inflation, interest rates, commodity prices
- Weather events and geopolitical tensions affecting supply routes
- Labor strikes or shortages in key manufacturing sectors
- Technology disruptions (AI, automation) in supply chain management
- Sustainability initiatives and ESG requirements in supply chains

SEARCH KEYWORDS TO PRIORITIZE:
- "supply chain disruption"
- "automotive semiconductor shortage"
- "port congestion"
- "shipping costs"
- "manufacturing production"
- "raw material prices"
- "logistics bottlenecks"
- "trade policy supply chain"

With live search enabled, the AI will automatically fetch and incorporate the most recent data on these topics."""
        
        return base_context
    
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
                
                # Add search parameters for live search functionality
                search_params = self.build_search_parameters()
                if search_params["mode"] != "off":
                    payload["search_parameters"] = search_params
                    self.logger.info(f"Live search enabled with mode: {search_params['mode']}, sources: default (web, news, x)")
                
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
                    
                    # Log usage information including search sources if available
                    usage_info = data.get("usage", {})
                    if "num_sources_used" in usage_info:
                        sources_used = usage_info["num_sources_used"]
                        self.logger.info(f"Live search used {sources_used} sources")
                        
                        # Log cost information (Live Search is $25 per 1,000 sources)
                        if sources_used > 0:
                            estimated_cost = sources_used * 0.025
                            self.logger.info(f"Estimated live search cost: ${estimated_cost:.3f}")
                    
                    # Log citations if available
                    if hasattr(data.get("choices", [{}])[0].get("message", {}), "citations"):
                        citations = data["choices"][0]["message"].get("citations", [])
                        if citations:
                            self.logger.info(f"Content includes {len(citations)} citations from live search")
                            for i, citation in enumerate(citations[:5], 1):  # Log first 5 citations
                                self.logger.debug(f"Citation {i}: {citation}")
                    
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
        
        # First, extract and remove the main H1 title (since Hugo will display it from frontmatter)
        h1_pattern = r'<h1[^>]*>(.*?)</h1>'
        h1_match = re.search(h1_pattern, content, flags=re.DOTALL)
        if h1_match:
            # Remove the first H1 - Hugo theme will handle the title display
            content = re.sub(h1_pattern, '', content, count=1, flags=re.DOTALL)
        
        # Convert remaining headers (starting from H2)
        content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1', content, flags=re.DOTALL)
        content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1', content, flags=re.DOTALL)
        content = re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1', content, flags=re.DOTALL)
        content = re.sub(r'<h5[^>]*>(.*?)</h5>', r'##### \1', content, flags=re.DOTALL)
        content = re.sub(r'<h6[^>]*>(.*?)</h6>', r'###### \1', content, flags=re.DOTALL)
        
        # Convert paragraphs
        content = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n', content, flags=re.DOTALL)
        
        # Convert lists
        content = re.sub(r'<ul[^>]*>', '', content)
        content = re.sub(r'</ul>', '\n', content)
        content = re.sub(r'<ol[^>]*>', '', content)
        content = re.sub(r'</ol>', '\n', content)
        content = re.sub(r'<li[^>]*>(.*?)</li>', r'- \1', content, flags=re.DOTALL)
        
        # Convert bold and italic
        content = re.sub(r'<strong[^>]*>(.*?)</strong>', r'**\1**', content, flags=re.DOTALL)
        content = re.sub(r'<em[^>]*>(.*?)</em>', r'*\1*', content, flags=re.DOTALL)
        
        # Clean up extra whitespace and empty lines at the start
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        content = content.strip()
        
        return content

    def build_hugo_site(self) -> bool:
        """Build the Hugo site after content generation"""
        if not self.config.hugo_build:
            return True
            
        try:
            import subprocess
            result = subprocess.run(['hugo'], cwd='..', capture_output=True, text=True, timeout=60)
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
        # Live Search settings
        'search_mode': 'auto',
        'search_sources': ["web", "news", "x"],
        'max_search_results': 20,
        'return_citations': True,
        'search_from_date': '',
        'search_to_date': '',
        'excluded_x_handles': [],
        'post_favorite_count': 0,
        'post_view_count': 0,
        'rss_links': [],
        # Processing settings
        'max_retries': 3,
        'timeout': 180,
        'min_chars': 6000,
        'max_chars': 15000,
        'output_dir': '../content/posts',
        'log_level': 'INFO',
        'alert_email': '',
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'smtp_username': '',
        'smtp_password': '',
        'site_prompt_file': 'site_prompt.txt',
        'system_prompt_file': 'system_prompt.txt',
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
                if config_key in ['max_retries', 'timeout', 'min_chars', 'max_chars', 'smtp_port', 'max_tokens', 'max_search_results', 'post_favorite_count', 'post_view_count']:
                    config_values[config_key] = int(value)
                elif config_key in ['temperature', 'presence_penalty', 'frequency_penalty']:
                    config_values[config_key] = float(value)
                elif config_key in ['hugo_build', 'return_citations']:
                    config_values[config_key] = value.lower() in ['true', '1', 'yes']
                elif config_key in ['search_sources', 'excluded_x_handles', 'rss_links']:
                    # Handle comma-separated list values
                    if value.strip():
                        config_values[config_key] = [item.strip() for item in value.split(',')]
                    else:
                        config_values[config_key] = []
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
        'HUGO_BUILD': ('hugo_build', lambda x: x.lower() in ['true', '1', 'yes']),
        # Live Search environment variables
        'SEARCH_MODE': 'search_mode',
        'SEARCH_SOURCES': ('search_sources', lambda x: [item.strip() for item in x.split(',') if item.strip()]),
        'MAX_SEARCH_RESULTS': ('max_search_results', int),
        'RETURN_CITATIONS': ('return_citations', lambda x: x.lower() in ['true', '1', 'yes']),
        'SEARCH_FROM_DATE': 'search_from_date',
        'SEARCH_TO_DATE': 'search_to_date',
        'EXCLUDED_X_HANDLES': ('excluded_x_handles', lambda x: [item.strip() for item in x.split(',') if item.strip()]),
        'POST_FAVORITE_COUNT': ('post_favorite_count', int),
        'POST_VIEW_COUNT': ('post_view_count', int),
        'RSS_LINKS': ('rss_links', lambda x: [item.strip() for item in x.split(',') if item.strip()])
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
        print(f"  Live Search:")
        print(f"    - Mode: {config.search_mode}")
        print(f"    - Sources: {', '.join(config.search_sources) if config.search_sources else 'default'}")
        print(f"    - Max Results: {config.max_search_results}")
        print(f"    - Citations: {'✓ Enabled' if config.return_citations else '✗ Disabled'}")
        if config.search_from_date or config.search_to_date:
            print(f"    - Date Range: {config.search_from_date or 'any'} to {config.search_to_date or 'any'}")
        if config.excluded_x_handles:
            print(f"    - Excluded X Handles: {', '.join(config.excluded_x_handles)}")
        if config.rss_links:
            print(f"    - RSS Links: {len(config.rss_links)} configured")
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