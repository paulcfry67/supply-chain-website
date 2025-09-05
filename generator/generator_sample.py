#!/usr/bin/env python3
"""
Daily Prepper Précis Generator
Generates daily threat intelligence briefings using Grok API
For prepperprecis.com
"""

import os
import sys
import json
import logging
import smtplib
import requests
import argparse
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration settings"""
    grok_api_key: str
    grok_base_url: str = "https://api.x.ai/v1"
    output_dir: str = "/tmp/daily-precis"
    max_retries: int = 3
    timeout: int = 60
    alert_email: str = "will.appleton@protonmail.com"
    smtp_server: str = "smtp.gmail.com"  # Configure as needed
    smtp_port: int = 587
    smtp_username: str = ""  # Set via environment
    smtp_password: str = ""  # Set via environment
    log_level: str = "INFO"
    max_chars: int = 3000
    min_chars: int = 1500


class PrepperPrecisGenerator:
    """Main class for generating daily prepper précis"""
    
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
        logging.basicConfig(
            level=getattr(logging, self.config.log_level.upper()),
            format=log_format,
            handlers=[
                logging.FileHandler(f"/var/log/prepper-precis-{datetime.now().strftime('%Y-%m')}.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def get_precis_prompt(self) -> str:
        """Get the full prompt for generating the prepper's précis"""
        return """DAILY PREPPER'S OUTLOOK PROMPT

Mission Statement
Generate a comprehensive daily Open Source Intelligence (OSINT) Prepper's Outlook summarizing current and emerging threats and disruptions relevant to individuals in the United States preparing for self-reliance and survival. Provide actionable, practical guidance in a structured, professional format suitable for preppers, homesteaders, and survivalists to enhance preparedness and resilience.

Output Structure
Executive Summary
• Threat Level Assessment: Overall preparedness threat level (Low/Moderate/Elevated/High/Severe) based on disruptions to safety, resources, and self-sufficiency.
• Key Developments: 2-3 critical developments in the past 24 hours affecting preparedness.
• Priority Actions: Immediate steps preppers should take within 24-72 hours to mitigate risks.

Preparedness Categories
1. Physical Security and Safety
• Personal Safety Threats: Risks from terrorism, civil unrest, or violent crime affecting personal or homestead security.
• Community Stability: Local or regional unrest, protests, or law enforcement issues impacting safety.
• Criminal Threats: Trends in looting, burglary, or trafficking affecting prepper communities.
• Infrastructure Risks: Vulnerabilities to power, water, or transportation systems critical to survival.

2. Cyber and Technology Threats
• Personal Cybersecurity: Phishing, malware, or identity theft risks to prepper communications and finances.
• Critical Systems Disruptions: Cyberattacks on utilities, supply chains, or emergency services.
• Technology Dependence Risks: Failures or vulnerabilities in tech-reliant survival tools (e.g., solar systems, comms).
• Data Privacy Threats: Surveillance or data breaches compromising off-grid lifestyles.

3. Natural and Environmental Hazards
• Severe Weather: Storms, floods, or extreme weather impacting shelter, food, or water supplies.
• Geological Events: Earthquakes, landslides, or volcanic risks to homestead stability.
• Public Health: Disease outbreaks or environmental contamination affecting survival.
• Climate-Related: Wildfires, droughts, or floods disrupting food production or access.

4. Economic and Supply Chain Resilience
• Supply Chain Disruptions: Shortages of critical supplies (food, fuel, medical, ammo).
• Financial Preparedness: Economic instability, inflation, or banking disruptions affecting resources.
• Energy Availability: Fuel or power shortages impacting off-grid systems.
• Food and Water Security: Threats to agricultural production, water access, or food storage.

5. Information and Situational Awareness
• Disinformation Risks: Misinformation campaigns affecting prepper decision-making.
• Social Media Manipulation: False narratives impacting community cohesion or resource planning.
• Propaganda Threats: External influences undermining self-reliance or morale.
• Communication Reliability: Risks to radio, internet, or other comms critical for preppers.

Near-Term Preparedness Priorities (24-72 Hours)
For each identified near-term threat, provide:
• Threat Description: Detailed explanation of the disruption or threat.
• Geographic Impact: Affected regions, states, or local areas.
• Population at Risk: Prepper demographics or communities most vulnerable (e.g., rural, urban, off-grid).
• Likelihood Assessment: Probability of threat materialization (Very Low/Low/Medium/High/Very High).
• Potential Impact: Consequences for survival, resources, or security if threat materializes.
• Recommended Actions: Specific preparedness measures (e.g., stockpile food, secure water, fortify defenses).
• Monitoring Indicators: Signals of escalation or de-escalation (e.g., weather updates, unrest reports).

Source Assessment
• Source Reliability: Evaluation of sources (A-F scale, A being most reliable).
• Information Confidence: Confidence level in intelligence (High/Medium/Low).
• Collection Gaps: Areas needing further information for prepper planning.

Requirements
Content Specifications
• Timeframe: Focus on threats and disruptions within 24-72 hours, with context for longer-term preparedness trends.
• Geographic Scope: United States and territories, with relevant global events impacting local resilience.
• Source Types: Open source materials only (news, government advisories, social media, survivalist forums, public databases).
• Length: Keep under 3000 characters but aim for 1500-2000 characters minimum for comprehensive coverage.
• Update Frequency: Daily, with clear date/time stamps.

Analytical Standards
• Objectivity: Present facts without political bias or sensationalism.
• Accuracy: Cross-reference multiple credible sources for reliability.
• Clarity: Use clear, practical language for preppers of varying expertise.
• Actionability: Provide specific, survival-oriented recommendations.
• Timeliness: Emphasize immediate and emerging threats relevant to preparedness.

Formatting Requirements
• Use markdown formatting with consistent section headers.
• Include plain text URLs labeled as "Sources" at the end of each section.
• Timestamp reports with current date and time.
• Include disclaimer about open source limitations.

Quality Control
• Cross-reference sources for significant claims.
• Distinguish confirmed facts from unverified reports.
• Assess source credibility and potential bias.
• Highlight uncertainties or conflicting information.

Generate today's Daily Prepper's Outlook following this exact structure and format. Focus on current threats and actionable intelligence for the preparedness community."""

    def generate_content(self) -> Optional[str]:
        """Generate the daily précis using Grok API"""
        prompt = self.get_precis_prompt()
        
        for attempt in range(1, self.config.max_retries + 1):
            try:
                self.logger.info(f"Attempt {attempt}/{self.config.max_retries}: Generating content via Grok API")
                
                payload = {
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a professional intelligence analyst specializing in OSINT threat assessment for the preparedness community. Generate precise, actionable daily intelligence briefings in markdown format."
                        },
                        {
                            "role": "user", 
                            "content": prompt
                        }
                    ],
                    "model": "grok-beta",  # Adjust model name as needed
                    "temperature": 0.3,
                    "max_tokens": 2000,
                    "stream": False
                }
                
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
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request failed (attempt {attempt}): {str(e)}")
            except KeyError as e:
                self.logger.error(f"Unexpected response format (attempt {attempt}): {str(e)}")
            except Exception as e:
                self.logger.error(f"Unexpected error (attempt {attempt}): {str(e)}")
        
        return None

    def save_content(self, content: str) -> Optional[str]:
        """Save content to markdown file with proper naming"""
        try:
            # Ensure output directory exists
            Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            today = datetime.now().strftime("%Y-%m-%d")
            filename = f"{today}-daily-prepper-precis.md"
            filepath = Path(self.config.output_dir) / filename
            
            # Add frontmatter and format content
            formatted_content = self.format_markdown(content)
            
            # Write file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            
            self.logger.info(f"Content saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to save content: {str(e)}")
            return None

    def format_markdown(self, content: str) -> str:
        """Format content with proper markdown structure and frontmatter"""
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%Y-%m-%d %H:%M UTC")
        
        frontmatter = f"""---
title: "Daily Prepper's Précis - {today}"
date: {now.isoformat()}
draft: false
categories: ["Daily Précis", "Threat Intelligence", "OSINT"]
tags: ["preparedness", "threat-assessment", "intelligence"]
author: "OSINT Analysis Team"
---

# DAILY PREPPER'S OUTLOOK
**Date:** {today}  
**Classification:** UNCLASSIFIED//FOR PUBLIC USE  
**Timestamp:** {timestamp}  
**Distribution:** Public

**Disclaimer:** This report relies on open source information and may be incomplete or unverified. It is not a substitute for official emergency advisories or professional survival training.

---

"""
        return frontmatter + content

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

    def run(self) -> int:
        """Main execution method"""
        self.logger.info("Starting Daily Prepper Précis generation")
        
        try:
            # Generate content
            content = self.generate_content()
            if not content:
                error_msg = "Failed to generate content after all retry attempts"
                self.logger.error(error_msg)
                self.send_alert_email(
                    "Prepper Précis Generation Failed",
                    f"Error: {error_msg}\nTime: {datetime.now()}\nCheck logs for details."
                )
                return 1
            
            # Save content
            filepath = self.save_content(content)
            if not filepath:
                error_msg = "Failed to save generated content"
                self.logger.error(error_msg)
                self.send_alert_email(
                    "Prepper Précis Save Failed", 
                    f"Error: {error_msg}\nTime: {datetime.now()}\nContent was generated but could not be saved."
                )
                return 1
            
            self.logger.info(f"Daily Précis generation completed successfully")
            self.logger.info(f"File ready for ingest: {filepath}")
            
            return 0
            
        except Exception as e:
            error_msg = f"Unexpected error in main execution: {str(e)}"
            self.logger.error(error_msg)
            self.send_alert_email(
                "Prepper Précis Critical Error",
                f"Error: {error_msg}\nTime: {datetime.now()}\nCheck logs immediately."
            )
            return 1


def load_config() -> Config:
    """Load configuration from environment variables and defaults"""
    return Config(
        grok_api_key=os.environ.get("GROK_API_KEY", ""),
        grok_base_url=os.environ.get("GROK_BASE_URL", "https://api.x.ai/v1"),
        output_dir=os.environ.get("PRECIS_OUTPUT_DIR", "/tmp/daily-precis"),
        max_retries=int(os.environ.get("PRECIS_MAX_RETRIES", "3")),
        timeout=int(os.environ.get("PRECIS_TIMEOUT", "60")),
        alert_email=os.environ.get("ALERT_EMAIL", "will.appleton@protonmail.com"),
        smtp_server=os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        smtp_port=int(os.environ.get("SMTP_PORT", "587")),
        smtp_username=os.environ.get("SMTP_USERNAME", ""),
        smtp_password=os.environ.get("SMTP_PASSWORD", ""),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        max_chars=int(os.environ.get("MAX_CHARS", "3000")),
        min_chars=int(os.environ.get("MIN_CHARS", "1500"))
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Generate Daily Prepper Précis")
    parser.add_argument("--config-check", action="store_true", help="Check configuration and exit")
    parser.add_argument("--dry-run", action="store_true", help="Generate content but don't save")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config()
    
    if args.config_check:
        print("Configuration Check:")
        print(f"  Grok API Key: {'✓ Set' if config.grok_api_key else '✗ Missing'}")
        print(f"  Output Directory: {config.output_dir}")
        print(f"  Alert Email: {config.alert_email}")
        print(f"  SMTP Configured: {'✓ Yes' if config.smtp_username else '✗ No'}")
        return 0
    
    if not config.grok_api_key:
        print("ERROR: GROK_API_KEY environment variable is required")
        return 1
    
    # Run generator
    generator = PrepperPrecisGenerator(config)
    
    if args.dry_run:
        content = generator.generate_content()
        if content:
            print("\n" + "="*50)
            print("GENERATED CONTENT (DRY RUN):")
            print("="*50)
            print(generator.format_markdown(content))
            print("="*50)
            return 0
        else:
            print("Failed to generate content")
            return 1
    
    return generator.run()


if __name__ == "__main__":
    sys.exit(main())

