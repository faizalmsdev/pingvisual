from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import json
import threading
from datetime import datetime
from flask import Flask, render_template, jsonify
import difflib
import re
import requests
import os

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

class AIAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
    def analyze_portfolio_changes(self, change_data):
        """Analyze changes using AI to detect new portfolio companies"""
        try:
            # Prepare context for AI analysis
            context = self._prepare_context(change_data)
            
            if not context:
                return None
                
            prompt = f"""
    You are an expert analyst specializing in investor portfolios and venture capital firms. 
    Analyze the following website changes to determine if any new companies have been added to an investor's portfolio.

    Context: This is from a website monitoring system tracking changes on investor/VC firm websites.

    Changes detected:
    {context}

    Please dont need to show the changes done on the navbar like this contents avoid this contents to show as changes "RA Capital menu Home about us About RA Capital Our Team What We Do Social Responsibility News faq venture Venture AT RA Our Portfolio Venture Testimonials techatlas TechAtlas Overview Work With Us map catalog Planetary join us The Right Job RA Capital RA Ventures Our Portfolio Companies knowledge".
    Dont mark it as text changes when the text contains par alike home about us our team etc.

    Your task is to analyze these changes and determine if any new companies have been added to the portfolio of the investor/VC firm. 
    Please analyze these changes and determine:
    1. Are there any new companies that appear to have been added to a portfolio?
    2. What are the company names (extract from alt text, titles, or content)?
    3. What type of companies are these (sector/industry)?
    4. Is this likely a new portfolio addition or just a website update?

    Also for the removed company if any image url removed or text removed from the website use that and verify if that removed url contains the company name or not if then extract the company name from that.

    IMPORTANT: Respond with ONLY valid JSON, no markdown formatting or code blocks.

    {{
        "new_companies_detected": true/false,
        "companies": [
            {{
                "name": "Company Name",
                "sector": "Industry/Sector",
                "confidence": "high/medium/low",
                "evidence": "What evidence suggests this is a new portfolio company",
                "source": "image/text/link"
            }}
        ],
        "added_company": "Added Company Name if detected or null",
        "removed_company": "Removed Company Name if detected or null",
        "modified_company": "Modified Company Name if detected or null",
        "analysis_summary": "Brief summary of the analysis"
    }}

    Focus only on actual portfolio company additions, not general website updates or news.
    """

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "deepseek/deepseek-r1:free",
                "messages": [
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "temperature": 0.1,  # Lower temperature for more consistent JSON output
                "max_tokens": 1000
            }
            
            response = requests.post(self.base_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result['choices'][0]['message']['content'].strip()
                
                # Extract JSON from markdown code blocks if present
                if ai_response.startswith('```json'):
                    # Find the JSON content between ```json and ```
                    start_marker = '```json'
                    end_marker = '```'
                    start_idx = ai_response.find(start_marker) + len(start_marker)
                    end_idx = ai_response.find(end_marker, start_idx)
                    if end_idx != -1:
                        ai_response = ai_response[start_idx:end_idx].strip()
                elif ai_response.startswith('```'):
                    # Handle generic code blocks
                    lines = ai_response.split('\n')
                    ai_response = '\n'.join(lines[1:-1])  # Remove first and last line
                
                # Try to parse JSON response
                try:
                    parsed_json = json.loads(ai_response)
                    
                    # Ensure all required fields are present with proper null handling
                    required_fields = {
                        "new_companies_detected": False,
                        "companies": [],
                        "added_company": None,
                        "removed_company": None,
                        "modified_company": None,
                        "analysis_summary": "Analysis completed"
                    }
                    
                    for field, default_value in required_fields.items():
                        if field not in parsed_json:
                            parsed_json[field] = default_value
                    
                    return parsed_json
                    
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error: {e}")
                    print(f"Raw AI response: {ai_response}")
                    
                    # Create a fallback structured response
                    return {
                        "new_companies_detected": False,
                        "companies": [],
                        "added_company": None,
                        "removed_company": None,
                        "modified_company": None,
                        "analysis_summary": "AI analysis completed but response format was invalid",
                        "error": f"JSON parsing failed: {str(e)}",
                        "raw_response": ai_response[:500]  # Truncate for logging
                    }
            else:
                print(f"AI API Error: {response.status_code} - {response.text}")
                return {
                    "new_companies_detected": False,
                    "companies": [],
                    "added_company": None,
                    "removed_company": None,
                    "modified_company": None,
                    "analysis_summary": f"API request failed with status {response.status_code}",
                    "error": f"API Error: {response.status_code}"
                }
                
        except Exception as e:
            print(f"Error in AI analysis: {e}")
            return {
                "new_companies_detected": False,
                "companies": [],
                "added_company": None,
                "removed_company": None,
                "modified_company": None,
                "analysis_summary": "Analysis failed due to system error",
                "error": str(e)
            }
    
    def _prepare_context(self, change_data):
        """Prepare context string from change data for AI analysis"""
        context_parts = []
        
        if change_data['type'] == 'new_images' and change_data.get('details'):
            context_parts.append("=== NEW IMAGES DETECTED ===")
            for img in change_data['details']:
                img_context = []
                if img.get('alt'):
                    img_context.append(f"Alt text: {img['alt']}")
                if img.get('title'):
                    img_context.append(f"Title: {img['title']}")
                if img.get('src'):
                    img_context.append(f"Image URL: {img['src']}")
                if img.get('context'):
                    img_context.append(f"Context: {img['context']}")
                
                if img_context:
                    context_parts.append(" | ".join(img_context))
        
        elif change_data['type'] == 'removed_images' and change_data.get('details'):
            context_parts.append("=== REMOVED IMAGES DETECTED ===")
            for img in change_data['details']:
                img_context = []
                if img.get('alt'):
                    img_context.append(f"Alt text: {img['alt']}")
                if img.get('title'):
                    img_context.append(f"Title: {img['title']}")
                if img.get('src'):
                    img_context.append(f"Image URL: {img['src']}")
                if img.get('context'):
                    img_context.append(f"Context: {img['context']}")
                if img.get('potential_company'):
                    img_context.append(f"Potential Company: {img['potential_company']}")
                
                if img_context:
                    context_parts.append(" | ".join(img_context))
        
        elif change_data['type'] == 'text_change' and change_data.get('details'):
            context_parts.append("=== TEXT CHANGES DETECTED ===")
            for detail in change_data['details']:
                if detail['type'] == 'added':
                    context_parts.append(f"New text added: {detail['content']}")
                elif detail['type'] == 'removed':
                    context_parts.append(f"Text removed: {detail['content']}")
                    if detail.get('potential_companies'):
                        context_parts.append(f"Potential companies in removed text: {', '.join(detail['potential_companies'])}")
        
        elif change_data['type'] == 'new_links' and change_data.get('details'):
            context_parts.append("=== NEW LINKS DETECTED ===")
            for link in change_data['details']:
                link_context = []
                if link.get('text'):
                    link_context.append(f"Link text: {link['text']}")
                if link.get('url'):
                    link_context.append(f"URL: {link['url']}")
                if link.get('title'):
                    link_context.append(f"Title: {link['title']}")
                
                if link_context:
                    context_parts.append(" | ".join(link_context))
        
        elif change_data['type'] == 'removed_links' and change_data.get('details'):
            context_parts.append("=== REMOVED LINKS DETECTED ===")
            for link in change_data['details']:
                link_context = []
                if link.get('text'):
                    link_context.append(f"Link text: {link['text']}")
                if link.get('url'):
                    link_context.append(f"URL: {link['url']}")
                if link.get('title'):
                    link_context.append(f"Title: {link['title']}")
                if link.get('potential_company'):
                    link_context.append(f"Potential Company: {link['potential_company']}")
                
                if link_context:
                    context_parts.append(" | ".join(link_context))
        
        elif change_data['type'] == 'removed_portfolio_companies' and change_data.get('details'):
            context_parts.append("=== REMOVED PORTFOLIO COMPANIES DETECTED ===")
            for company in change_data['details']:
                company_context = []
                if company.get('name'):
                    company_context.append(f"Company name: {company['name']}")
                if company.get('context'):
                    company_context.append(f"Context: {company['context']}")
                
                if company_context:
                    context_parts.append(" | ".join(company_context))
        
        return "\n".join(context_parts) if context_parts else None

class WebChangeMonitor:
    def __init__(self, url="http://127.0.0.1:3001/caspianequity.html", api_key=None):
        self.url = url
        self.previous_content = None
        self.current_content = None
        self.changes = []
        self.running = False
        self.driver = None
        
        # Initialize AI analyzer if API key is provided
        self.ai_analyzer = AIAnalyzer(api_key) if api_key else None
        
    def setup_driver(self):
        """Setup Chrome driver with options"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        service = Service()
        self.driver = webdriver.Chrome(service=service, options=options)
    
    def is_navigation_content(self, text):
        """Check if the text content is likely navigation/menu content"""
        if not text:
            return False
            
        text_lower = text.lower()
        
        # Common navigation keywords
        nav_keywords = [
            'menu', 'home', 'about', 'about us', 'our team', 'what we do', 
            'social responsibility', 'news', 'faq', 'venture', 'portfolio',
            'testimonials', 'overview', 'work with us', 'contact', 'login',
            'courses', 'resources', 'archives', 'gateway', 'investor login',
            'innovator resources', 'rapport', 'techatlas', 'planetary'
        ]
        
        # Check if text contains multiple navigation keywords
        keyword_count = sum(1 for keyword in nav_keywords if keyword in text_lower)
        
        # If text is short and contains nav keywords, likely navigation
        if len(text) < 500 and keyword_count >= 3:
            return True
            
        # Check for typical navigation patterns
        nav_patterns = [
            r'\bmenu\b.*\bhome\b.*\babout\b',  # menu home about pattern
            r'\bhome\s*/\s*\w+\s*/\s*\w+',     # breadcrumb pattern like "Home / Venture / Portfolio"
            r'(\w+\s+){5,}.*\b(home|about|contact|login)\b'  # long sequence with nav words
        ]
        
        for pattern in nav_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Check if it's mostly navigation links (high ratio of nav keywords to total words)
        words = text.split()
        if len(words) > 0:
            nav_word_ratio = keyword_count / len(words)
            if nav_word_ratio > 0.3:  # More than 30% navigation keywords
                return True
        
        return False
    
    def filter_navigation_changes(self, text_changes):
        """Filter out navigation-related text changes"""
        filtered_changes = []
        navigation_filtered_count = 0
        
        for change in text_changes:
            content = change.get('content', '')
            
            # Skip if this looks like navigation content
            if self.is_navigation_content(content):
                navigation_filtered_count += 1
                print(f"🔍 Filtered navigation content ({change['type']}): {content[:100]}...")
                continue
            
            # Skip very short changes that are likely navigation
            if len(content.strip()) < 20:
                continue
            
            # Skip if content is mostly navigation keywords
            words = content.lower().split()
            nav_word_count = sum(1 for word in words if word in [
                'menu', 'home', 'about', 'contact', 'login', 'portfolio', 
                'venture', 'team', 'news', 'faq', 'overview'
            ])
            
            if len(words) > 0 and (nav_word_count / len(words)) > 0.4:
                navigation_filtered_count += 1
                print(f"🔍 Filtered high nav-keyword content ({change['type']}): {content[:100]}...")
                continue
            
            filtered_changes.append(change)
        
        if navigation_filtered_count > 0:
            print(f"🔍 Total navigation content filtered: {navigation_filtered_count} items")
        
        return filtered_changes
        
    def extract_image_info(self, img_element):
        """Extract comprehensive image information including attributes"""
        img_info = {
            'src': img_element.get('src', ''),
            'alt': img_element.get('alt', ''),
            'title': img_element.get('title', ''),
            'data-id': img_element.get('data-id', ''),
            'data-src': img_element.get('data-src', ''),
            'data-original': img_element.get('data-original', ''),
            'class': img_element.get('class', ''),
            'id': img_element.get('id', ''),
            'width': img_element.get('width', ''),
            'height': img_element.get('height', ''),
            'loading': img_element.get('loading', ''),
            'data-caption': img_element.get('data-caption', ''),
            'aria-label': img_element.get('aria-label', ''),
            'aria-describedby': img_element.get('aria-describedby', '')
        }
        
        # Create a unique identifier for the image based on multiple attributes
        identifier_parts = []
        if img_info['src']:
            identifier_parts.append(f"src:{img_info['src']}")
        if img_info['data-id']:
            identifier_parts.append(f"data-id:{img_info['data-id']}")
        if img_info['id']:
            identifier_parts.append(f"id:{img_info['id']}")
        if img_info['alt']:
            identifier_parts.append(f"alt:{img_info['alt'][:50]}")
        
        img_info['unique_id'] = " | ".join(identifier_parts) if identifier_parts else img_info['src']
        
        return img_info
    
    def scrape_page(self):
        """Enhanced scrape_page method to better preserve structure and filter navigation"""
        try:
            if not self.driver:
                self.setup_driver()
                
            self.driver.get(self.url)
            time.sleep(5)  # Wait for page to load
            
            html_content = self.driver.page_source
            
            # Parse with BeautifulSoup to extract body content only
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove navigation elements before processing
            nav_selectors = [
                'nav', 'header', '.navbar', '.nav', '.menu', '.navigation',
                '[class*="nav"]', '[class*="menu"]', '[id*="nav"]', '[id*="menu"]'
            ]
            
            for selector in nav_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # ENHANCED: Before removing scripts, extract structured content
            # Look for portfolio blocks specifically
            portfolio_blocks = []
            
            # Look for common portfolio container patterns
            portfolio_containers = soup.find_all(['div'], class_=re.compile(r'portfolio|isotope|block|main-block', re.I))
            
            for container in portfolio_containers:
                # Look for company names in headings within this container
                headings = container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                for heading in headings:
                    company_name = heading.get_text(strip=True)
                    if company_name and len(company_name) > 1:
                        # Get more context from the container
                        container_text = container.get_text(strip=True)
                        
                        portfolio_blocks.append({
                            'company_name': company_name,
                            'context': container_text[:200] if container_text else '',  # First 200 chars of context
                            'html_tag': heading.name,
                            'parent_classes': container.get('class', []),
                            'container_id': container.get('id', ''),
                            'full_html': str(container)[:500]  # First 500 chars of HTML for debugging
                        })
                        
                        print(f"📊 Found portfolio company: '{company_name}' in {heading.name} tag")
            
            # Also look for company names in image alt text and filenames
            for img in soup.find_all('img'):
                img_src = img.get('src', '')
                img_alt = img.get('alt', '')
                
                # Extract company name from image filename
                if img_src:
                    # Look for patterns like /portfolio/CompanyName.jpg
                    import os
                    filename = os.path.basename(img_src)
                    company_from_filename = os.path.splitext(filename)[0]
                    
                    # Check if this looks like a company name
                    if (company_from_filename and 
                        len(company_from_filename) > 2 and 
                        company_from_filename.isalpha() and
                        company_from_filename not in ['image', 'logo', 'photo', 'pic']):
                        
                        # Find the parent container
                        parent_container = img.find_parent(['div'], class_=re.compile(r'portfolio|isotope|block|main-block', re.I))
                        if parent_container:
                            portfolio_blocks.append({
                                'company_name': company_from_filename.upper(),  # Convert to uppercase like AROHAN
                                'context': parent_container.get_text(strip=True)[:200],
                                'html_tag': 'img',
                                'parent_classes': parent_container.get('class', []),
                                'container_id': parent_container.get('id', ''),
                                'source': 'image_filename',
                                'image_src': img_src
                            })
                            
                            print(f"📊 Found portfolio company from image: '{company_from_filename.upper()}' from {img_src}")
            
            # Remove duplicates based on company name
            seen_companies = set()
            unique_portfolio_blocks = []
            for block in portfolio_blocks:
                company_key = block['company_name'].upper()
                if company_key not in seen_companies:
                    seen_companies.add(company_key)
                    unique_portfolio_blocks.append(block)
            
            portfolio_blocks = unique_portfolio_blocks
            
            # Remove script and style elements
            for script in soup(["script", "style", "noscript"]):
                script.decompose()
            
            # Extract body content
            body = soup.find('body')
            if not body:
                return None
            
            # ENHANCED: Get structured text content preserving headings
            # This helps maintain company names in their context
            structured_text = self.extract_structured_text(body)
            
            # Get clean text content with better formatting
            text_content = body.get_text(separator=' ', strip=True)
            # Clean up excessive whitespace
            text_content = ' '.join(text_content.split())
            
            # Extract links information (filter out navigation links)
            links_info = []
            for a in body.find_all('a', href=True):
                link_text = a.get_text(strip=True)
                if link_text and not self.is_navigation_content(link_text):
                    links_info.append({
                        'text': link_text, 
                        'href': a.get('href', ''),
                        'title': a.get('title', ''),
                        'aria-label': a.get('aria-label', ''),
                        'data-id': a.get('data-id', '')
                    })
            
            # Extract comprehensive image information (unchanged)
            images_info = []
            for img in body.find_all('img'):
                if img.get('src') or img.get('data-src'):
                    img_info = self.extract_image_info(img)
                    images_info.append(img_info)
            
            # ENHANCED: Extract relevant information with portfolio structure
            content_data = {
                'text': text_content,
                'structured_text': structured_text,  # NEW: Preserve structure
                'portfolio_blocks': portfolio_blocks,  # NEW: Specific portfolio info
                'text_length': len(text_content),
                'links': links_info,
                'images': images_info,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"Scraped content: {len(content_data['text'])} chars, {len(content_data['links'])} links, {len(content_data['images'])} images, {len(portfolio_blocks)} portfolio blocks")
            
            # Debug: Show what portfolio companies we found
            if portfolio_blocks:
                company_names = [block['company_name'] for block in portfolio_blocks]
                print(f"📊 Portfolio companies found: {', '.join(company_names)}")
            
            return content_data
            
        except Exception as e:
            print(f"Error scraping page: {e}")
            return None

    def extract_structured_text(self, element):
        """Extract text while preserving heading structure"""
        structured_parts = []
        
        for child in element.descendants:
            if child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                text = child.get_text(strip=True)
                if text and not self.is_navigation_content(text):
                    structured_parts.append(f"[{child.name.upper()}]{text}[/{child.name.upper()}]")
            elif child.name == 'p':
                text = child.get_text(strip=True)
                if text and not self.is_navigation_content(text):
                    structured_parts.append(f"[P]{text}[/P]")
        
        return ' '.join(structured_parts)

    def compare_images(self, old_images, new_images):
        """Compare images with detailed attribute tracking"""
        changes = []
        
        # Create dictionaries for comparison using unique identifiers
        old_images_dict = {}
        new_images_dict = {}
        
        # Process old images
        for img in old_images:
            key = img.get('unique_id', img.get('src', ''))
            old_images_dict[key] = img
            
        # Process new images
        for img in new_images:
            key = img.get('unique_id', img.get('src', ''))
            new_images_dict[key] = img
        
        # Find new images
        new_image_keys = set(new_images_dict.keys()) - set(old_images_dict.keys())
        if new_image_keys:
            new_image_details = []
            for key in new_image_keys:
                img = new_images_dict[key]
                
                # Skip if this appears to be a navigation-related image
                if (img.get('alt') and self.is_navigation_content(img['alt'])) or \
                   (img.get('title') and self.is_navigation_content(img['title'])):
                    continue
                
                context_info = []
                
                if img['alt']:
                    context_info.append(f"Alt: '{img['alt']}'")
                if img['title']:
                    context_info.append(f"Title: '{img['title']}'")
                if img['data-id']:
                    context_info.append(f"Data-ID: '{img['data-id']}'")
                if img['aria-label']:
                    context_info.append(f"Aria-Label: '{img['aria-label']}'")
                if img['data-caption']:
                    context_info.append(f"Caption: '{img['data-caption']}'")
                
                context_str = " | ".join(context_info) if context_info else "No additional context"
                
                new_image_details.append({
                    'src': img['src'],
                    'alt': img['alt'],
                    'title': img['title'],
                    'data_id': img['data-id'],
                    'context': context_str,
                    'all_attributes': img
                })
            
            if new_image_details:  # Only create change if we have non-navigation images
                change_data = {
                    'type': 'new_images',
                    'description': f'{len(new_image_details)} new images found',
                    'details': new_image_details,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Add AI analysis for new images
                if self.ai_analyzer:
                    print("🤖 Running AI analysis on new images...")
                    ai_analysis = self.ai_analyzer.analyze_portfolio_changes(change_data)
                    if ai_analysis:
                        change_data['ai_analysis'] = ai_analysis
                        print(f"AI Analysis completed: {ai_analysis.get('analysis_summary', 'No summary')}")
                
                changes.append(change_data)
        
        # Find removed images - ENHANCED with detailed reporting
        removed_image_keys = set(old_images_dict.keys()) - set(new_images_dict.keys())
        if removed_image_keys:
            removed_image_details = []
            potential_removed_companies = []
            
            for key in removed_image_keys:
                img = old_images_dict[key]
                
                # Skip if this appears to be a navigation-related image
                if (img.get('alt') and self.is_navigation_content(img['alt'])) or \
                   (img.get('title') and self.is_navigation_content(img['title'])):
                    print(f"🔍 Filtered removed navigation image: {img.get('alt', img.get('src', 'Unknown'))}")
                    continue
                
                context_info = []
                
                if img['alt']:
                    context_info.append(f"Alt: '{img['alt']}'")
                if img['title']:
                    context_info.append(f"Title: '{img['title']}'")
                if img['data-id']:
                    context_info.append(f"Data-ID: '{img['data-id']}'")
                if img['aria-label']:
                    context_info.append(f"Aria-Label: '{img['aria-label']}'")
                if img['data-caption']:
                    context_info.append(f"Caption: '{img['data-caption']}'")
                
                context_str = " | ".join(context_info) if context_info else "No additional context"
                
                # Extract potential company name from image
                potential_company = self.extract_company_from_image(img)
                if potential_company:
                    potential_removed_companies.append(potential_company)
                
                removed_image_details.append({
                    'src': img['src'],
                    'alt': img['alt'],
                    'title': img['title'],
                    'data_id': img['data-id'],
                    'context': context_str,
                    'potential_company': potential_company,
                    'all_attributes': img
                })
            
            if removed_image_details:
                # Create enhanced description showing what was removed
                description_parts = [f'{len(removed_image_details)} images removed']
                
                if potential_removed_companies:
                    company_names = ', '.join(potential_removed_companies)
                    description_parts.append(f"Potential companies: {company_names}")
                
                # Show some examples of what was removed
                example_alts = [img['alt'] for img in removed_image_details[:3] if img['alt']]
                if example_alts:
                    description_parts.append(f"Examples: {', '.join(example_alts)}")
                
                change_data = {
                    'type': 'removed_images',
                    'description': ' | '.join(description_parts),
                    'details': removed_image_details,
                    'potential_companies': potential_removed_companies,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Add AI analysis for removed images
                if self.ai_analyzer:
                    print("🤖 Running AI analysis on removed images...")
                    ai_analysis = self.ai_analyzer.analyze_portfolio_changes(change_data)
                    if ai_analysis:
                        change_data['ai_analysis'] = ai_analysis
                        print(f"AI Analysis completed: {ai_analysis.get('analysis_summary', 'No summary')}")
                
                changes.append(change_data)
                print(f"🗑️ REMOVED IMAGES: {change_data['description']}")
        
        # Find modified images (same source but different attributes)
        common_keys = set(old_images_dict.keys()) & set(new_images_dict.keys())
        modified_images = []
        
        for key in common_keys:
            old_img = old_images_dict[key]
            new_img = new_images_dict[key]
            
            # Skip navigation images
            if (old_img.get('alt') and self.is_navigation_content(old_img['alt'])) or \
               (new_img.get('alt') and self.is_navigation_content(new_img['alt'])):
                continue
            
            # Check for attribute changes
            attribute_changes = []
            attributes_to_check = ['alt', 'title', 'data-id', 'class', 'id', 'aria-label', 'data-caption']
            
            for attr in attributes_to_check:
                old_val = old_img.get(attr, '')
                new_val = new_img.get(attr, '')
                
                if old_val != new_val:
                    attribute_changes.append({
                        'attribute': attr,
                        'old_value': old_val,
                        'new_value': new_val
                    })
            
            if attribute_changes:
                modified_images.append({
                    'src': new_img['src'],
                    'unique_id': key,
                    'changes': attribute_changes,
                    'old_context': self.build_image_context(old_img),
                    'new_context': self.build_image_context(new_img)
                })
        
        if modified_images:
            # Enhanced description for modified images
            description_parts = [f'{len(modified_images)} images modified']
            
            # Show what types of changes occurred
            change_types = set()
            for img in modified_images:
                for change in img['changes']:
                    change_types.add(change['attribute'])
            
            if change_types:
                description_parts.append(f"Changed attributes: {', '.join(change_types)}")
            
            changes.append({
                'type': 'modified_images',
                'description': ' | '.join(description_parts),
                'details': modified_images,
                'timestamp': datetime.now().isoformat()
            })
        
        return changes
    
    def extract_company_from_image(self, img):
        """Extract potential company name from image attributes or filename"""
        potential_company = None
        
        # Try to extract from alt text
        if img.get('alt'):
            alt_text = img['alt'].strip()
            if alt_text and len(alt_text) > 2 and not self.is_navigation_content(alt_text):
                # Check if alt text looks like a company name
                if alt_text.isupper() or alt_text.istitle():
                    potential_company = alt_text
        
        # Try to extract from filename
        if not potential_company and img.get('src'):
            import os
            filename = os.path.basename(img['src'])
            company_from_filename = os.path.splitext(filename)[0]
            
            if (company_from_filename and 
                len(company_from_filename) > 2 and 
                company_from_filename.replace('-', '').replace('_', '').isalnum() and
                company_from_filename.lower() not in ['image', 'logo', 'photo', 'pic', 'banner']):
                potential_company = company_from_filename.upper()
        
        # Try to extract from title
        if not potential_company and img.get('title'):
            title_text = img['title'].strip()
            if title_text and len(title_text) > 2 and not self.is_navigation_content(title_text):
                if title_text.isupper() or title_text.istitle():
                    potential_company = title_text
        
        return potential_company
    
    def extract_company_from_link(self, link):
        """Extract potential company name from link text or URL"""
        potential_company = None
        
        # Try to extract from link text
        if link.get('text'):
            link_text = link['text'].strip()
            if link_text and len(link_text) > 2 and not self.is_navigation_content(link_text):
                # Check if link text looks like a company name
                if link_text.isupper() or link_text.istitle():
                    # Avoid common button/action words
                    action_words = ['visit', 'site', 'learn', 'more', 'read', 'view', 'click', 'here']
                    if not any(word in link_text.lower() for word in action_words):
                        potential_company = link_text
        
        # Try to extract from URL
        if not potential_company and link.get('href'):
            url = link['href']
            # Extract domain or path segments that might contain company names
            import re
            # Look for patterns like /company/CompanyName or domain names
            url_parts = re.findall(r'/([A-Za-z][A-Za-z0-9]+)', url)
            for part in url_parts:
                if (len(part) > 2 and 
                    part.lower() not in ['www', 'com', 'org', 'net', 'portfolio', 'company', 'about'] and
                    not part.isdigit()):
                    potential_company = part.upper()
                    break
        
        # Try to extract from title
        if not potential_company and link.get('title'):
            title_text = link['title'].strip()
            if title_text and len(title_text) > 2 and not self.is_navigation_content(title_text):
                if title_text.isupper() or title_text.istitle():
                    potential_company = title_text
        
        return potential_company
    
    def compare_content(self, old_content, new_content):
        """Compare two content snapshots and find differences - FIXED VERSION"""
        if not old_content or not new_content:
            return []
            
        changes = []
        
        # Compare text content with detailed before/after tracking
        old_text = old_content.get('text', '').strip()
        new_text = new_content.get('text', '').strip()
        
        if old_text != new_text:
            # Split into paragraphs for detailed comparison
            old_paragraphs = [p.strip() for p in old_text.split('\n') if p.strip()]
            new_paragraphs = [p.strip() for p in new_text.split('\n') if p.strip()]
            
            # Find the differences using difflib for detailed comparison
            differ = difflib.SequenceMatcher(None, old_paragraphs, new_paragraphs)
            
            text_changes = []
            for tag, i1, i2, j1, j2 in differ.get_opcodes():
                if tag == 'delete':
                    for i in range(i1, i2):
                        if len(old_paragraphs[i]) > 5:
                            # Skip if this is navigation content
                            if self.is_navigation_content(old_paragraphs[i]):
                                continue
                                
                            removed_text = old_paragraphs[i]
                            potential_companies = self.extract_company_names(removed_text)
                            
                            text_changes.append({
                                'type': 'removed',
                                'content': old_paragraphs[i][:200],
                                'position': i,
                                'potential_companies': potential_companies,
                                'is_company_related': len(potential_companies) > 0
                            })
                elif tag == 'insert':
                    for j in range(j1, j2):
                        if len(new_paragraphs[j]) > 5:
                            # Skip if this is navigation content
                            if self.is_navigation_content(new_paragraphs[j]):
                                continue
                                
                            added_text = new_paragraphs[j]
                            potential_companies = self.extract_company_names(added_text)
                            
                            text_changes.append({
                                'type': 'added',
                                'content': new_paragraphs[j][:200],
                                'position': j,
                                'potential_companies': potential_companies,
                                'is_company_related': len(potential_companies) > 0
                            })
                elif tag == 'replace':
                    # Handle replacements with navigation filtering
                    for i in range(i1, i2):
                        if len(old_paragraphs[i]) > 5 and not self.is_navigation_content(old_paragraphs[i]):
                            removed_text = old_paragraphs[i]
                            potential_companies = self.extract_company_names(removed_text)
                            
                            text_changes.append({
                                'type': 'removed',
                                'content': old_paragraphs[i][:200],
                                'position': i,
                                'potential_companies': potential_companies,
                                'is_company_related': len(potential_companies) > 0
                            })
                    for j in range(j1, j2):
                        if len(new_paragraphs[j]) > 5 and not self.is_navigation_content(new_paragraphs[j]):
                            added_text = new_paragraphs[j]
                            potential_companies = self.extract_company_names(added_text)
                            
                            text_changes.append({
                                'type': 'added',
                                'content': new_paragraphs[j][:200],
                                'position': j,
                                'potential_companies': potential_companies,
                                'is_company_related': len(potential_companies) > 0
                            })
            
            # Apply additional filtering for navigation content
            text_changes = self.filter_navigation_changes(text_changes)
            
            if text_changes:
                # Create enhanced description with more details about what changed
                added_count = len([c for c in text_changes if c["type"] == "added"])
                removed_count = len([c for c in text_changes if c["type"] == "removed"])
                
                description_parts = [f'Text content changed - {added_count} additions, {removed_count} removals']
                
                # Show potential company-related changes
                company_related_changes = [c for c in text_changes if c.get("is_company_related")]
                if company_related_changes:
                    all_companies = []
                    for change in company_related_changes:
                        all_companies.extend(change.get("potential_companies", []))
                    
                    if all_companies:
                        unique_companies = list(set(all_companies))
                        description_parts.append(f"Potential companies involved: {', '.join(unique_companies[:5])}")  # Limit to first 5
                
                # Show examples of changes
                if added_count > 0:
                    added_examples = [c['content'][:50] for c in text_changes if c["type"] == "added"][:2]
                    if added_examples:
                        description_parts.append(f"Added examples: {' | '.join(added_examples)}")
                
                if removed_count > 0:
                    removed_examples = [c['content'][:50] for c in text_changes if c["type"] == "removed"][:2]
                    if removed_examples:
                        description_parts.append(f"Removed examples: {' | '.join(removed_examples)}")
                
                change_data = {
                    'type': 'text_change',
                    'description': ' | '.join(description_parts),
                    'details': text_changes,
                    'before_after': {
                        'before': old_text[:1000],
                        'after': new_text[:1000]
                    },
                    'company_related_count': len(company_related_changes),
                    'timestamp': new_content['timestamp']
                }
                
                # Add AI analysis for text changes
                if self.ai_analyzer:
                    print("🤖 Running AI analysis on text changes...")
                    ai_analysis = self.ai_analyzer.analyze_portfolio_changes(change_data)
                    if ai_analysis:
                        change_data['ai_analysis'] = ai_analysis
                        print(f"AI Analysis completed: {ai_analysis.get('analysis_summary', 'No summary')}")
                
                changes.append(change_data)
                print(f"📝 TEXT CHANGES: {change_data['description']}")
        
        # Compare links (with navigation filtering) - FIXED
        old_links = {f"{link['href']}|{link['text']}": link for link in old_content.get('links', [])}
        new_links = {f"{link['href']}|{link['text']}": link for link in new_content.get('links', [])}
        
        # Find new links (already filtered during scraping)
        new_link_keys = set(new_links.keys()) - set(old_links.keys())
        if new_link_keys:
            new_link_details = []
            for key in new_link_keys:
                link = new_links[key]
                # Additional check to ensure no navigation links slip through
                if not self.is_navigation_content(link['text']):
                    new_link_details.append({
                        'url': link['href'],
                        'text': link['text'],
                        'title': link.get('title', ''),
                        'aria_label': link.get('aria-label', ''),
                        'data_id': link.get('data-id', '')
                    })
            
            if new_link_details:  # Only create change if we have non-navigation links
                change_data = {
                    'type': 'new_links',
                    'description': f'{len(new_link_details)} new links found',
                    'details': new_link_details,
                    'timestamp': new_content['timestamp']
                }
                
                # Add AI analysis for new links
                if self.ai_analyzer:
                    print("🤖 Running AI analysis on new links...")
                    ai_analysis = self.ai_analyzer.analyze_portfolio_changes(change_data)
                    if ai_analysis:
                        change_data['ai_analysis'] = ai_analysis
                        print(f"AI Analysis completed: {ai_analysis.get('analysis_summary', 'No summary')}")
                
                changes.append(change_data)
        
        # Find removed links - ENHANCED with detailed reporting - THIS WAS THE MAIN ISSUE
        removed_link_keys = set(old_links.keys()) - set(new_links.keys())
        if removed_link_keys:
            removed_link_details = []
            potential_removed_companies = []
            navigation_links_filtered = 0
            
            for key in removed_link_keys:
                link = old_links[key]
                
                # Filter out navigation links from removed links too
                if self.is_navigation_content(link['text']):
                    navigation_links_filtered += 1
                    print(f"🔍 Filtered removed navigation link: {link['text']}")
                    continue
                
                # Try to extract company name from link text or URL
                potential_company = self.extract_company_from_link(link)
                if potential_company:
                    potential_removed_companies.append(potential_company)
                
                removed_link_details.append({
                    'url': link['href'],
                    'text': link['text'],
                    'title': link.get('title', ''),
                    'aria_label': link.get('aria-label', ''),
                    'data_id': link.get('data-id', ''),
                    'potential_company': potential_company
                })
            
            if removed_link_details:  # Only create change if we have non-navigation links
                # Create enhanced description showing what was removed
                description_parts = [f'{len(removed_link_details)} links removed']
                
                if potential_removed_companies:
                    company_names = ', '.join(potential_removed_companies)
                    description_parts.append(f"Potential companies: {company_names}")
                
                # Show examples of removed link text
                example_texts = [link['text'][:50] for link in removed_link_details[:3] if link['text']]
                if example_texts:
                    description_parts.append(f"Examples: {', '.join(example_texts)}")
                
                if navigation_links_filtered > 0:
                    description_parts.append(f"({navigation_links_filtered} navigation links filtered)")
                
                change_data = {
                    'type': 'removed_links',
                    'description': ' | '.join(description_parts),
                    'details': removed_link_details,
                    'potential_companies': potential_removed_companies,
                    'navigation_filtered': navigation_links_filtered,
                    'timestamp': new_content['timestamp']
                }
                
                # Add AI analysis for removed links
                if self.ai_analyzer:
                    print("🤖 Running AI analysis on removed links...")
                    ai_analysis = self.ai_analyzer.analyze_portfolio_changes(change_data)
                    if ai_analysis:
                        change_data['ai_analysis'] = ai_analysis
                        print(f"AI Analysis completed: {ai_analysis.get('analysis_summary', 'No summary')}")
                
                changes.append(change_data)
                print(f"🗑️ REMOVED LINKS: {change_data['description']}")
        
        # Compare images with enhanced tracking
        image_changes = self.compare_images(
            old_content.get('images', []), 
            new_content.get('images', [])
        )
        changes.extend(image_changes)
        
        # Compare portfolio blocks specifically
        portfolio_changes = self.compare_portfolio_blocks(
            old_content.get('portfolio_blocks', []),
            new_content.get('portfolio_blocks', [])
        )
        changes.extend(portfolio_changes)
        
        return changes

    def compare_portfolio_blocks(self, old_blocks, new_blocks):
        """Compare portfolio blocks to detect company additions/removals"""
        changes = []
        
        # Create dictionaries for comparison
        old_companies = {block['company_name']: block for block in old_blocks}
        new_companies = {block['company_name']: block for block in new_blocks}
        
        # Debug: Print what companies we found
        print(f"DEBUG - Old companies: {list(old_companies.keys())}")
        print(f"DEBUG - New companies: {list(new_companies.keys())}")
        
        # Find new companies
        new_company_names = set(new_companies.keys()) - set(old_companies.keys())
        if new_company_names:
            new_company_details = []
            for name in new_company_names:
                block = new_companies[name]
                new_company_details.append({
                    'name': name,
                    'context': block['context'],
                    'html_tag': block['html_tag'],
                    'parent_classes': block['parent_classes']
                })
            
            # Enhanced description with company names
            company_names_str = ', '.join(new_company_names)
            change_data = {
                'type': 'new_portfolio_companies',
                'description': f'{len(new_company_names)} new portfolio companies found: {company_names_str}',
                'details': new_company_details,
                'company_names': list(new_company_names),  # Add this for easy access
                'timestamp': datetime.now().isoformat()
            }
            
            # Add AI analysis for new portfolio companies
            if self.ai_analyzer:
                print("🤖 Running AI analysis on new portfolio companies...")
                ai_analysis = self.ai_analyzer.analyze_portfolio_changes(change_data)
                if ai_analysis:
                    change_data['ai_analysis'] = ai_analysis
                    print(f"AI Analysis completed: {ai_analysis.get('analysis_summary', 'No summary')}")
            
            changes.append(change_data)
            print(f"✅ NEW COMPANIES DETECTED: {company_names_str}")
        
        # Find removed companies - THIS WAS ALSO MISSING PROPER HANDLING
        removed_company_names = set(old_companies.keys()) - set(new_companies.keys())
        if removed_company_names:
            removed_company_details = []
            for name in removed_company_names:
                block = old_companies[name]
                removed_company_details.append({
                    'name': name,
                    'context': block['context'],
                    'html_tag': block['html_tag'],
                    'parent_classes': block['parent_classes']
                })
            
            # Enhanced description with company names
            company_names_str = ', '.join(removed_company_names)
            change_data = {
                'type': 'removed_portfolio_companies',
                'description': f'{len(removed_company_names)} portfolio companies removed: {company_names_str}',
                'details': removed_company_details,
                'company_names': list(removed_company_names),  # Add this for easy access
                'timestamp': datetime.now().isoformat()
            }
            
            # Add AI analysis for removed portfolio companies
            if self.ai_analyzer:
                print("🤖 Running AI analysis on removed portfolio companies...")
                ai_analysis = self.ai_analyzer.analyze_portfolio_changes(change_data)
                if ai_analysis:
                    change_data['ai_analysis'] = ai_analysis
                    print(f"AI Analysis completed: {ai_analysis.get('analysis_summary', 'No summary')}")
            
            changes.append(change_data)
            print(f"🗑️ REMOVED COMPANIES DETECTED: {company_names_str}")
        
        return changes

    def extract_company_names(self, text):
        """Extract potential company names from text using various patterns"""
        import re
        
        potential_companies = []
        
        # Pattern 1: All uppercase words (like APTUS)
        uppercase_pattern = r'\b[A-Z]{2,}\b'
        uppercase_matches = re.findall(uppercase_pattern, text)
        potential_companies.extend(uppercase_matches)
        
        # Pattern 2: Title case words that could be company names
        title_case_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        title_matches = re.findall(title_case_pattern, text)
        
        # Filter title case matches to avoid common words
        common_words = {'The', 'And', 'Or', 'But', 'For', 'With', 'From', 'To', 'Of', 'In', 'On', 'At', 'By'}
        title_matches = [match for match in title_matches if match not in common_words and len(match) > 3]
        potential_companies.extend(title_matches)
        
        # Pattern 3: Look for HTML heading tags (h1, h2, h3, etc.) content
        heading_pattern = r'<h[1-6][^>]*>(.*?)</h[1-6]>'
        heading_matches = re.findall(heading_pattern, text, re.IGNORECASE)
        potential_companies.extend([match.strip() for match in heading_matches if match.strip()])
        
        # Pattern 4: Words immediately after common company indicators
        company_indicators = ['Company', 'Corp', 'Ltd', 'Inc', 'LLC', 'Holdings', 'Group', 'Industries']
        for indicator in company_indicators:
            pattern = rf'\b(\w+)\s+{indicator}\b'
            matches = re.findall(pattern, text, re.IGNORECASE)
            potential_companies.extend(matches)
        
        # Remove duplicates and filter out very short matches
        potential_companies = list(set([company for company in potential_companies if len(company) > 2]))
        
        return potential_companies

    def build_image_context(self, img):
        """Build context string for an image based on its attributes"""
        context_parts = []
        
        if img['alt']:
            context_parts.append(f"Alt: '{img['alt']}'")
        if img['title']:
            context_parts.append(f"Title: '{img['title']}'")
        if img['data-id']:
            context_parts.append(f"Data-ID: '{img['data-id']}'")
        if img['aria-label']:
            context_parts.append(f"Aria-Label: '{img['aria-label']}'")
        if img['data-caption']:
            context_parts.append(f"Caption: '{img['data-caption']}'")
        if img['class']:
            context_parts.append(f"Class: '{img['class']}'")
        
        return " | ".join(context_parts) if context_parts else "No context attributes"
    
    def monitor_loop(self):
        """Main monitoring loop"""
        print(f"Starting monitoring of {self.url}")
        if self.ai_analyzer:
            print("🤖 AI analysis enabled for portfolio company detection")
        print("🔍 Navigation content filtering enabled")
        
        # Initial scrape
        self.current_content = self.scrape_page()
        if self.current_content:
            print("Initial scrape completed")
            
        # Wait 2 minutes before first comparison
        time.sleep(120)  # 2 minutes
        
        while self.running:
            try:
                # Scrape new content
                new_content = self.scrape_page()
                
                if new_content and self.current_content:
                    # Compare with previous content
                    detected_changes = self.compare_content(self.current_content, new_content)
                    
                    if detected_changes:
                        print(f"Changes detected at {datetime.now()}: {len(detected_changes)} changes")
                        for change in detected_changes:
                            print(f"  - {change['type']}: {change['description']}")
                            # Print AI analysis if available
                            if change.get('ai_analysis'):
                                ai = change['ai_analysis']
                                if ai.get('new_companies_detected'):
                                    print(f"    🤖 AI: New companies detected - {[c['name'] for c in ai.get('companies', [])]}")
                        
                        self.changes.extend(detected_changes)
                        
                        # Keep only last 50 changes to prevent memory issues
                        if len(self.changes) > 50:
                            self.changes = self.changes[-50:]
                    else:
                        print(f"No changes detected at {datetime.now()}")
                    
                    # Update current content
                    self.previous_content = self.current_content
                    self.current_content = new_content
                
                # Wait 1 minute before next check
                time.sleep(60)  # 1 minute
                
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(60)
    
    def start_monitoring(self):
        """Start the monitoring process"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop the monitoring process"""
        self.running = False
        if self.driver:
            self.driver.quit()
        print("Monitoring stopped")
    
    def get_changes(self):
        """Get the list of detected changes"""
        return self.changes

# Flask web application
app = Flask(__name__)

# Initialize monitor with API key
monitor = WebChangeMonitor(api_key=os.environ.get("API_KEY"))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/changes')
def get_changes():
    return jsonify({
        'changes': monitor.get_changes(),
        'monitoring': monitor.running,
        'url': monitor.url,
        'ai_enabled': monitor.ai_analyzer is not None
    })

@app.route('/api/start')
def start_monitoring():
    if not monitor.running:
        monitor.start_monitoring()
        return jsonify({'status': 'started', 'message': 'Monitoring started with AI analysis and navigation filtering'})
    return jsonify({'status': 'already_running', 'message': 'Monitoring already running'})

@app.route('/api/debug')
def debug_info():
    """Debug endpoint to see current content"""
    return jsonify({
        'current_content_length': len(monitor.current_content.get('text', '')) if monitor.current_content else 0,
        'previous_content_length': len(monitor.previous_content.get('text', '')) if monitor.previous_content else 0,
        'total_changes': len(monitor.changes),
        'monitoring': monitor.running,
        'last_check': monitor.current_content.get('timestamp') if monitor.current_content else None,
        'current_images': len(monitor.current_content.get('images', [])) if monitor.current_content else 0,
        'ai_enabled': monitor.ai_analyzer is not None,
        'navigation_filtering': True
    })

@app.route('/api/stop')
def stop_monitoring():
    if monitor.running:
        monitor.stop_monitoring()
        return jsonify({'status': 'stopped', 'message': 'Monitoring stopped'})
    return jsonify({'status': 'not_running', 'message': 'Monitoring not running'})

if __name__ == '__main__':
    print("Enhanced Web Change Monitor with AI Analysis & Navigation Filtering")
    print("==================================================================")
    print("Features:")
    print("- Text change tracking")
    print("- Link monitoring")
    print("- Enhanced image monitoring with alt, title, data-id tracking")
    print("- Image attribute change detection")
    print("- 🤖 AI-powered portfolio company detection")
    print("- DeepSeek AI integration for investment analysis")
    print("- 🔍 Navigation content filtering")
    print("- ✅ FIXED: Removed content detection (images, links, text, companies)")
    print("- Automatic filtering of menu/nav changes")
    print("Starting Flask server...")
    print("Visit http://localhost:5000 to view the dashboard")
    print("Press Ctrl+C to stop")
    
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
        monitor.stop_monitoring()