import requests
from bs4 import BeautifulSoup
import csv
import time
import json
import re
import os
import random
import pandas as pd
from datetime import datetime
from urllib.parse import urljoin, urlparse

class KeyboardScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.8,image/avif,image/webp,image/apng,*/*;q=0.7',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        self.keyboard_parts = []
        self.vendor_list = []
        self.websites_scraped = 0
        self.failed_websites = []
        self.categories = [
            'kit', 'pcb', 'case', 'plate', 'switch', 'keycap', 'stabilizer', 
            'lube', 'foam', 'cable', 'accessory'
        ]
        
        # Load the vendor list or create it if it doesn't exist
        self.load_vendor_list()
        
    def load_vendor_list(self):
        """Load the vendor list from a JSON file or create one if it doesn't exist"""
        if os.path.exists('keyboard_vendors.json'):
            with open('keyboard_vendors.json', 'r') as f:
                self.vendor_list = json.load(f)
            print(f"Loaded {len(self.vendor_list)} vendors from JSON file.")
        else:
            # Start with a small core list of popular vendors
            self.vendor_list = [
                {"name": "KBDfans", "url": "https://kbdfans.com", "categories": ["kit", "pcb", "case", "plate", "switch", "keycap", "stabilizer"]},
                {"name": "NovelKeys", "url": "https://novelkeys.com", "categories": ["kit", "switch", "keycap", "stabilizer", "lube"]},
                {"name": "Keychron", "url": "https://www.keychron.com", "categories": ["kit", "switch", "keycap"]},
                {"name": "CannonKeys", "url": "https://cannonkeys.com", "categories": ["kit", "pcb", "case", "switch", "keycap"]},
                {"name": "Drop", "url": "https://drop.com", "categories": ["kit", "switch", "keycap"]}
            ]
            
            # Save the initial vendor list
            with open('keyboard_vendors.json', 'w') as f:
                json.dump(self.vendor_list, f, indent=4)
            
            print(f"Created initial vendor list with {len(self.vendor_list)} vendors.")
    
    def save_vendor_list(self):
        """Save the current vendor list to a JSON file"""
        with open('keyboard_vendors.json', 'w') as f:
            json.dump(self.vendor_list, f, indent=4)
        print(f"Saved vendor list with {len(self.vendor_list)} vendors.")
    
    def add_vendor(self, name, url, categories=None):
        """Add a new vendor to the list if it doesn't already exist"""
        if not categories:
            categories = ["kit", "pcb", "case", "plate", "switch", "keycap", "stabilizer"]
        
        # Normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Check if vendor already exists
        for vendor in self.vendor_list:
            parsed1 = urlparse(vendor['url']).netloc.replace('www.', '')
            parsed2 = urlparse(url).netloc.replace('www.', '')
            if parsed1 == parsed2:
                print(f"Vendor {name} ({url}) already exists in list.")
                return False
        
        # Add new vendor
        self.vendor_list.append({
            "name": name,
            "url": url,
            "categories": categories,
            "discovered": datetime.now().strftime('%Y-%m-%d')
        })
        
        # Save the updated vendor list
        self.save_vendor_list()
        print(f"Added {name} ({url}) to vendor list.")
        return True
    
    def discover_keyboard_vendors(self, num_to_discover=10, search_depth=2):
        """
        Search the web for keyboard vendors and add them to the vendor list
        
        Args:
            num_to_discover: Maximum number of new vendors to discover
            search_depth: How many search result pages to check
        """
        print("Starting keyboard vendor discovery...")
        
        # Search terms to find keyboard shops
        search_terms = [
            "custom mechanical keyboard shop",
            "mechanical keyboard parts vendor",
            "custom keyboard kit store",
            "keyboard switches keycaps store",
            "DIY keyboard parts shop",
            "mechanical keyboard components store",
            "custom keycap vendor",
            "mechanical keyboard PCB vendor",
            "custom keyboard case shop",
            "keyboard stabilizers vendor",
            "mechanical keyboard vendor site",
            "keyboard group buy site"
        ]
        
        # Vendor keywords to help verify we're looking at a real keyboard shop
        vendor_keywords = [
            "mechanical keyboard", "custom keyboard", "keyboard kit",
            "keycap", "switch", "stabilizer", "pcb", "plate", 
            "keyboard", "shop", "store", "buy", "shipping", "group buy"
        ]
        
        discovered_count = 0
        
        # Try each search term until we've discovered enough vendors
        for search_term in search_terms:
            if discovered_count >= num_to_discover:
                break
                
            print(f"Searching for: {search_term}")
            
            # Create Google search URL
            search_url = f"https://www.google.com/search?q={search_term.replace(' ', '+')}"
            
            try:
                # Get the search results page
                response = requests.get(search_url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                # Parse search results
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all search result links
                search_results = soup.select('a')
                
                # Process search results
                for result in search_results:
                    # Skip if we've found enough
                    if discovered_count >= num_to_discover:
                        break
                        
                    # Get href attribute
                    href = result.get('href', '')
                    
                    # Skip irrelevant links
                    if not href.startswith('http') and not href.startswith('/url?q='):
                        continue
                    
                    # Extract URL from Google search results
                    if href.startswith('/url?q='):
                        href = href.split('/url?q=')[1].split('&')[0]
                    
                    # Skip common non-vendor sites
                    skip_domains = ['google.com', 'youtube.com', 'reddit.com', 'wikipedia.org', 
                                'amazon.com', 'ebay.com', 'instagram.com', 'facebook.com',
                                'twitter.com', 'pinterest.com', 'tiktok.com', 'etsy.com']
                    
                    if any(domain in href for domain in skip_domains):
                        continue
                    
                    try:
                        # Parse domain
                        domain = urlparse(href).netloc
                        
                        # Skip if no domain
                        if not domain:
                            continue
                        
                        # Visit the website to verify it's a keyboard vendor
                        print(f"  Checking potential vendor: {domain}")
                        
                        site_response = requests.get(href, headers=self.headers, timeout=10)
                        site_soup = BeautifulSoup(site_response.text, 'html.parser')
                        
                        # Check if this looks like a keyboard vendor
                        site_text = site_soup.get_text().lower()
                        keyboard_score = sum(1 for keyword in vendor_keywords if keyword in site_text)
                        
                        # If at least 4 keywords are found, consider it a keyboard vendor
                        if keyboard_score >= 4:
                            # Get title for name
                            title = site_soup.title.string if site_soup.title else domain
                            name = title.split('|')[0].strip() if '|' in title else title.strip()
                            name = name.split('-')[0].strip() if '-' in name else name
                            
                            # Try to determine categories
                            categories = []
                            for category in self.categories:
                                if category in site_text or category + 's' in site_text:
                                    categories.append(category)
                            
                            # If no categories were found, use defaults
                            if not categories:
                                categories = ["kit", "switch", "keycap"]
                            
                            # Add the vendor
                            if self.add_vendor(name, href, categories):
                                discovered_count += 1
                                print(f"  Added new vendor: {name} ({href})")
                        else:
                            print(f"  Not a keyboard vendor (score: {keyboard_score}/10)")
                            
                    except Exception as e:
                        print(f"  Error checking {href}: {e}")
                    
                    # Respect websites with a delay
                    time.sleep(random.uniform(1.0, 2.0))
                    
            except Exception as e:
                print(f"Error during vendor discovery: {e}")
        
        print(f"Discovery complete. Added {discovered_count} new vendors.")
    
    def validate_vendors(self):
        """Validate that all vendors in the list are actually keyboard-related websites"""
        print("Validating vendor list...")
        
        # Keywords that indicate a site is keyboard-related
        keyboard_keywords = [
            "mechanical keyboard", "custom keyboard", "keyboard kit",
            "keycap", "switch", "stabilizer", "pcb", "plate"
        ]
        
        valid_vendors = []
        removed_vendors = []
        
        for vendor in self.vendor_list:
            try:
                print(f"Checking {vendor['name']} ({vendor['url']})...")
                
                # Try to visit the vendor site
                response = requests.get(vendor['url'], headers=self.headers, timeout=10)
                
                # Check if the site is up and accessible
                if response.status_code == 200:
                    # Check if it seems to be keyboard-related
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text = soup.get_text().lower()
                    
                    # Count how many keyboard keywords appear
                    keyword_count = sum(1 for keyword in keyboard_keywords if keyword in text)
                    
                    if keyword_count >= 2:
                        valid_vendors.append(vendor)
                        print(f"  ✓ Valid keyboard vendor ({keyword_count} keywords found)")
                    else:
                        removed_vendors.append(vendor)
                        print(f"  ✗ Not a keyboard vendor ({keyword_count} keywords found)")
                else:
                    removed_vendors.append(vendor)
                    print(f"  ✗ Site returned status code {response.status_code}")
            
            except Exception as e:
                removed_vendors.append(vendor)
                print(f"  ✗ Error checking site: {e}")
            
            # Be respectful with request timing
            time.sleep(random.uniform(1.0, 2.0))
        
        # Update the vendor list with only valid vendors
        self.vendor_list = valid_vendors
        
        # Save the updated vendor list
        self.save_vendor_list()
        
        print(f"Validation complete. Kept {len(valid_vendors)} vendors, removed {len(removed_vendors)} vendors.")
    
    def categorize_product(self, name, description=''):
        """Categorize a product based on its name and description"""
        name_lower = name.lower()
        description_lower = description.lower() if description else ''
        
        # Define keywords for each category
        category_keywords = {
            'kit': ['kit', 'diy', 'barebones', 'barebone', 'build', 'keyboard set', 'starter'],
            'pcb': ['pcb', 'circuit board', 'printed circuit', 'hotswap', 'hot swap', 'controller', 'microcontroller'],
            'case': ['case', 'housing', 'shell', 'frame', 'enclosure'],
            'plate': ['plate', 'mounting plate', 'switch plate', 'aluminum plate', 'brass plate', 'fr4', 'carbon fiber'],
            'switch': ['switch', 'switches', 'gateron', 'cherry', 'kailh', 'outemu', 'durock', 'boba', 'glorious panda', 'holy panda', 'linear', 'tactile', 'clicky'],
            'keycap': ['keycap', 'key cap', 'pbt', 'abs', 'doubleshot', 'double shot', 'dye sub', 'dye-sub', 'backlit', 'shine-through', 'artisan'],
            'stabilizer': ['stabilizer', 'stab', 'stabs', 'screw-in', 'clip-in', 'plate mount', 'durock', 'cherry', 'costar'],
            'lube': ['lube', 'lubricant', 'krytox', 'tribosys', 'grease', '205g0', '3203', '3204'],
            'foam': ['foam', 'dampener', 'dampening', 'sound', 'silencing', 'isolation'],
            'cable': ['cable', 'usb', 'aviator', 'coiled', 'braided', 'connector', 'usb-c'],
            'accessory': ['accessory', 'puller', 'switch tester', 'keypuller', 'tool', 'brush', 'mod', 'band-aid', 'o-ring', 'o ring', 'wrist rest', 'deskmat', 'desk mat']
        }
        
        # Check product name and description against category keywords
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in name_lower or (description_lower and keyword in description_lower):
                    return category
        
        # Default category if no match is found
        return 'other'
        
    def scrape_vendor(self, vendor, max_products=50):
        """Scrape products from a vendor"""
        try:
            print(f"Scraping {vendor['name']} ({vendor['url']})...")
            
            # Try to load the main page
            response = requests.get(vendor['url'], headers=self.headers, timeout=10)
            response.raise_for_status()
            
            # Find category URLs
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Common category link texts
            category_link_texts = [
                'keyboard', 'kit', 'diy', 'pcb', 'case', 'plate', 'switch', 'keycap', 
                'stabilizer', 'stab', 'lube', 'accessory', 'part', 'component'
            ]
            
            # Try to find category links
            category_links = []
            for link in soup.find_all('a', href=True):
                link_text = link.text.lower().strip()
                link_href = link['href']
                
                # Skip empty links, social media, external links, etc.
                if not link_href or link_href.startswith('#') or 'javascript:' in link_href:
                    continue
                
                # Check if the link contains any category keywords
                for keyword in category_link_texts:
                    if keyword in link_text or keyword in link_href.lower():
                        # Make sure the URL is absolute
                        absolute_url = urljoin(vendor['url'], link_href)
                        # Only add if it's from the same domain
                        if urlparse(absolute_url).netloc == urlparse(vendor['url']).netloc:
                            category_links.append({
                                'url': absolute_url,
                                'text': link_text
                            })
                            break
            
            # If we found category links, scrape each one
            if category_links:
                products_found = 0
                
                for category in category_links:
                    if products_found >= max_products:
                        break
                        
                    try:
                        # Scrape the category page
                        category_url = category['url']
                        print(f"  - Scraping category: {category['text']} ({category_url})")
                        
                        cat_response = requests.get(category_url, headers=self.headers, timeout=10)
                        cat_response.raise_for_status()
                        
                        cat_soup = BeautifulSoup(cat_response.text, 'html.parser')
                        
                        # Look for products - various class names used across different sites
                        product_containers = []
                        
                        # Try different product container selectors (covering most e-commerce platforms)
                        for selector in [
                            'div.product', 'div.product-item', 'div.product-card', 'div.product_box',
                            'div.grid-product', 'div.card', 'div.item', 'li.product', 'article.product',
                            'div.col-sm-4', 'div.col-md-4', 'div.collection-item', 'div.product-grid-item'
                        ]:
                            containers = cat_soup.select(selector)
                            if containers:
                                product_containers.extend(containers)
                                break
                        
                        # If we still don't have products, try a broader approach
                        if not product_containers:
                            # Look for product images with links
                            for img in cat_soup.find_all('img'):
                                parent_a = img.find_parent('a')
                                if parent_a and 'href' in parent_a.attrs:
                                    container = parent_a.find_parent('div')
                                    if container:
                                        product_containers.append(container)
                        
                        print(f"    Found {len(product_containers)} potential products")
                        
                        # Process each product
                        for product in product_containers:
                            try:
                                # Extract name - look for common product title elements
                                name_elem = None
                                for selector in ['h2', 'h3', 'h4', '.title', '.product-title', '.name', '.product-name', '.product__title']:
                                    found = product.select_one(selector)
                                    if found:
                                        name_elem = found
                                        break
                                
                                # If we still don't have a name, try the alt text of the image
                                if not name_elem:
                                    img = product.find('img')
                                    if img and 'alt' in img.attrs:
                                        name = img['alt'].strip()
                                    else:
                                        # Skip this product if we can't find a name
                                        continue
                                else:
                                    name = name_elem.text.strip()
                                
                                # Extract price - look for common price elements
                                price = None
                                price_elem = None
                                for selector in ['.price', '.product-price', '.money', '[data-price]', '.amount', '.product__price']:
                                    found = product.select_one(selector)
                                    if found:
                                        price_elem = found
                                        break
                                
                                if price_elem:
                                    price_text = price_elem.text.strip()
                                    # Try to extract the price using regex
                                    price_match = re.search(r'[\$£€](\d+(?:\.\d+)?)', price_text)
                                    if price_match:
                                        price = float(price_match.group(1))
                                        
                                # Extract link
                                link = None
                                link_elem = product.find('a')
                                if link_elem and 'href' in link_elem.attrs:
                                    link = urljoin(category_url, link_elem['href'])
                                
                                # Extract image
                                img_url = None
                                img_elem = product.find('img')
                                if img_elem:
                                    # Try different image attributes
                                    for attr in ['src', 'data-src', 'data-srcset', 'data-lazy-src']:
                                        if attr in img_elem.attrs:
                                            img_src = img_elem[attr]
                                            if img_src:
                                                # Handle comma-separated srcset
                                                if ',' in img_src:
                                                    img_src = img_src.split(',')[0].strip().split(' ')[0]
                                                img_url = urljoin(category_url, img_src)
                                                break
                                
                                # Determine category from product name and link
                                product_category = self.categorize_product(name, category['text'])
                                
                                # Add to keyboard parts list if we have at least a name and link
                                if name and link:
                                    self.keyboard_parts.append({
                                        'name': name,
                                        'price': price if price is not None else 0.0,
                                        'category': product_category,
                                        'url': link,
                                        'image_url': img_url or '',
                                        'source': vendor['name'],
                                        'source_url': vendor['url'],
                                        'scrape_date': datetime.now().strftime('%Y-%m-%d')
                                    })
                                    
                                    products_found += 1
                                    
                                    # Break if we've reached the max products
                                    if products_found >= max_products:
                                        break
                                    
                            except Exception as e:
                                print(f"      Error parsing product: {e}")
                            
                        # Add a delay between category pages
                        time.sleep(random.uniform(1.0, 2.0))
                        
                    except Exception as e:
                        print(f"    Error scraping category {category['text']}: {e}")
                
                print(f"  Scraped {products_found} products from {vendor['name']}")
                self.websites_scraped += 1
                
            else:
                # If we couldn't find category links, try to find products on the main page
                print(f"  No category links found, trying to find products on main page")
                
                # Look for products - various class names used across different sites
                product_containers = []
                
                # Try different product container selectors
                for selector in [
                    'div.product', 'div.product-item', 'div.product-card', 'div.product_box',
                    'div.grid-product', 'div.card', 'div.item', 'li.product', 'article.product',
                    'div.col-sm-4', 'div.col-md-4', 'div.collection-item', 'div.product-grid-item'
                ]:
                    containers = soup.select(selector)
                    if containers:
                        product_containers.extend(containers)
                        break
                
                print(f"  Found {len(product_containers)} potential products on main page")
                
                # Process each product (similar to category page processing)
                products_found = 0
                for product in product_containers[:max_products]:
                    try:
                        # Extract name
                        name_elem = None
                        for selector in ['h2', 'h3', 'h4', '.title', '.product-title', '.name', '.product-name', '.product__title']:
                            found = product.select_one(selector)
                            if found:
                                name_elem = found
                                break
                        
                        if not name_elem:
                            img = product.find('img')
                            if img and 'alt' in img.attrs:
                                name = img['alt'].strip()
                            else:
                                continue
                        else:
                            name = name_elem.text.strip()
                        
                        # Extract price
                        price = None
                        price_elem = None
                        for selector in ['.price', '.product-price', '.money', '[data-price]', '.amount', '.product__price']:
                            found = product.select_one(selector)
                            if found:
                                price_elem = found
                                break
                        
                        if price_elem:
                            price_text = price_elem.text.strip()
                            price_match = re.search(r'[\$£€](\d+(?:\.\d+)?)', price_text)
                            if price_match:
                                price = float(price_match.group(1))
                                
                        # Extract link
                        link = None
                        link_elem = product.find('a')
                        if link_elem and 'href' in link_elem.attrs:
                            link = urljoin(vendor['url'], link_elem['href'])
                        
                        # Extract image
                        img_url = None
                        img_elem = product.find('img')
                        if img_elem:
                            for attr in ['src', 'data-src', 'data-srcset', 'data-lazy-src']:
                                if attr in img_elem.attrs:
                                    img_src = img_elem[attr]
                                    if img_src:
                                        if ',' in img_src:
                                            img_src = img_src.split(',')[0].strip().split(' ')[0]
                                        img_url = urljoin(vendor['url'], img_src)
                                        break
                        
                        # Determine category from product name
                        product_category = self.categorize_product(name)
                        
                        # Add to keyboard parts list
                        if name and link:
                            self.keyboard_parts.append({
                                'name': name,
                                'price': price if price is not None else 0.0,
                                'category': product_category,
                                'url': link,
                                'image_url': img_url or '',
                                'source': vendor['name'],
                                'source_url': vendor['url'],
                                'scrape_date': datetime.now().strftime('%Y-%m-%d')
                            })
                            
                            products_found += 1
                            
                    except Exception as e:
                        print(f"    Error parsing product: {e}")
                
                if products_found > 0:
                    print(f"  Scraped {products_found} products from {vendor['name']} main page")
                    self.websites_scraped += 1
                else:
                    print(f"  Could not find any products on {vendor['name']}")
                    self.failed_websites.append(vendor['name'])
            
        except Exception as e:
            print(f"Error scraping {vendor['name']}: {e}")
            self.failed_websites.append(vendor['name'])
        
        # Add a delay between vendors
        time.sleep(random.uniform(2.0, 3.0))
    
    def export_to_csv(self, filename='keyboard_parts.csv'):
        """Export scraped data to CSV file"""
        if not self.keyboard_parts:
            print("No data to export.")
            return
        
        # Define the CSV fields
        fields = ['name', 'price', 'category', 'url', 'image_url', 'source', 'source_url', 'scrape_date']
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fields)
                writer.writeheader()
                writer.writerows(self.keyboard_parts)
            
            print(f"Data exported to {filename}")
            print(f"Total keyboard parts exported: {len(self.keyboard_parts)}")
        except Exception as e:
            print(f"Error exporting data to CSV: {e}")
    
    def find_keyboard_vendors_from_reddit(self, num_to_discover=10):
        """
        Parse r/MechanicalKeyboards and related subreddits to find keyboard vendors
        """
        print("Searching Reddit for keyboard vendors...")
        
        reddit_urls = [
            "https://www.reddit.com/r/MechanicalKeyboards/wiki/vendor_list",
            "https://www.reddit.com/r/MechanicalKeyboards/wiki/recommendedsellers"
        ]
        
        discovered_count = 0
        
        for url in reddit_urls:
            if discovered_count >= num_to_discover:
                break
                
            print(f"Checking {url}")
            
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find all links in the wiki page
                for link in soup.select('a[href]'):
                    href = link.get('href')
                    
                    # Skip if we've found enough
                    if discovered_count >= num_to_discover:
                        break
                    
                    # Skip Reddit, Wiki links and other common non-vendor sites
                    if not href.startswith(('http://', 'https://')):
                        continue
                        
                    skip_domains = ['reddit.com', 'youtube.com', 'wikipedia.org',
                                'amazon.com', 'ebay.com', 'aliexpress.com']
                    
                    if any(domain in href for domain in skip_domains):
                        continue
                    
                    # Get link text as potential vendor name
                    name = link.text.strip()
                    if not name or len(name) < 3:
                        # If no text, use the domain as name
                        name = urlparse(href).netloc
                    
                    # Add as a vendor
                    if self.add_vendor(name, href):
                        discovered_count += 1
                        
            except Exception as e:
                print(f"Error scraping Reddit vendor list: {e}")
        
        print(f"Found {discovered_count} new vendors from Reddit.")
        
    def find_keyboard_vendors_from_kbd_news(self):
        """
        Parse the KBD.news vendor database which has 500+ vendors
        """
        print("Fetching vendor list from KBD.news...")
        
        url = "https://kbd.news/vendors"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # The site has vendor links
            vendors_added = 0
            
            # Look for vendor links
            for link in soup.select('a[href]'):
                href = link.get('href')
                
                # Skip non-external links
                if not href.startswith(('http://', 'https://')) or 'kbd.news' in href:
                    continue
                
                # Get potential vendor name
                name = link.text.strip()
                if not name or len(name) < 2:
                    name = urlparse(href).netloc.replace('www.', '')
                
                # Try to infer categories from the context
                parent_text = link.parent.get_text().lower() if link.parent else ""
                categories = []
                for category in self.categories:
                    if category in parent_text:
                        categories.append(category)
                
                # Add the vendor
                if self.add_vendor(name, href, categories if categories else None):
                    vendors_added += 1
            
            print(f"Added {vendors_added} vendors from KBD.news")
            
        except Exception as e:
            print(f"Error fetching vendors from KBD.news: {e}")
    
    def find_keyboard_vendor_by_name(self, vendor_name):
        """
        Search for a specific keyboard vendor by name and add it to our list
        
        Args:
            vendor_name: The name of the vendor to search for
        """
        print(f"Searching for keyboard vendor: {vendor_name}")
        
        search_url = f"https://www.google.com/search?q={vendor_name.replace(' ', '+')}+mechanical+keyboard+official+site"
        
        try:
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the first few search results
            results = []
            
            for g in soup.select('div.g'):
                link = g.select_one('a')
                if not link or not link.get('href'):
                    continue
                
                href = link.get('href')
                if href.startswith('/url?') or href.startswith('/search?'):
                    continue
                
                # Extract title
                title = g.select_one('h3')
                title_text = title.text if title else ""
                
                results.append({
                    'title': title_text,
                    'url': href
                })
                
                if len(results) >= 3:
                    break
            
            # Check each result to see if it's the vendor we're looking for
            for result in results:
                domain = urlparse(result['url']).netloc.lower()
                name_parts = vendor_name.lower().split()
                
                # Check if domain contains parts of the vendor name
                if any(part in domain for part in name_parts if len(part) > 2):
                    # Likely a match
                    self.add_vendor(vendor_name, result['url'])
                    print(f"Added {vendor_name} ({result['url']})")
                    return True
            
            print(f"Could not find {vendor_name} in search results")
            return False
            
        except Exception as e:
            print(f"Error searching for {vendor_name}: {e}")
            return False
    
    def add_dummy_data(self):
        """Add dummy data for testing purposes"""
        print("Adding dummy data...")
        
        # No dummy data - empty list
        dummy_data = []
        
        self.keyboard_parts.extend(dummy_data)
        print(f"Added {len(dummy_data)} dummy keyboard parts")
    
    def run(self, num_vendors=10, max_products_per_vendor=25, discover_vendors=True, add_dummy_data=False):
        """Run the scraper for multiple vendors"""
        # Optionally discover new vendors first
        if discover_vendors:
            # Try to find specific vendors by name if provided
            for vendor_name in ["NLandKeys", "QwertyKeys", "Keebmonkey", "Cannonkeys"]:
                self.find_keyboard_vendor_by_name(vendor_name)
            
            # Get vendors from Reddit and KBD.news
            self.find_keyboard_vendors_from_reddit()
            self.find_keyboard_vendors_from_kbd_news()
        
        print(f"Starting scraper for up to {num_vendors} vendors, {max_products_per_vendor} products each...")
        
        # Randomize the vendor list to get a variety
        random.shuffle(self.vendor_list)
        
        # Limit to the specified number of vendors
        vendors_to_scrape = self.vendor_list[:num_vendors]
        
        # Scrape each vendor
        for vendor in vendors_to_scrape:
            self.scrape_vendor(vendor, max_products_per_vendor)
            
        # Optionally add dummy data (disabled by default)
        if add_dummy_data:
            print("Adding dummy data as requested...")
            self.add_dummy_data()
        elif len(self.keyboard_parts) < 1:
            print("Warning: No keyboard parts found.")
        
        # Export the data to CSV
        self.export_to_csv()
        
        # Print summary
        print("\nScraping Summary:")
        print(f"Vendors attempted: {len(vendors_to_scrape)}")
        print(f"Vendors successfully scraped: {self.websites_scraped}")
        print(f"Total keyboard parts found: {len(self.keyboard_parts)}")
        
        if self.failed_websites:
            print(f"Failed websites ({len(self.failed_websites)}): {', '.join(self.failed_websites)}")
        
        # Generate category statistics
        self.generate_category_stats()
        
        return self.keyboard_parts
    
    def generate_category_stats(self):
        """Generate statistics about parts by category"""
        if not self.keyboard_parts:
            print("No data to analyze.")
            return
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(self.keyboard_parts)
        
        # Count parts by category
        category_counts = df['category'].value_counts()
        
        print("\nParts by Category:")
        for category, count in category_counts.items():
            print(f"{category}: {count}")
        
        # Price statistics by category
        print("\nPrice Statistics by Category:")
        for category in category_counts.index:
            category_df = df[df['category'] == category]
            prices = category_df['price'].dropna()
            
            if not prices.empty and prices.sum() > 0:
                avg_price = prices.mean()
                min_price = prices.min()
                max_price = prices.max()
                
                print(f"{category}:")
                print(f"  Average: ${avg_price:.2f}")
                print(f"  Range: ${min_price:.2f} - ${max_price:.2f}")

if __name__ == "__main__":
    # Record start time
    start_time = datetime.now()
    
    # Create the scraper
    scraper = KeyboardScraper()
    
    # Run the scraper with parameters:
    # - Number of vendors to scrape (default: 10)
    # - Maximum products per vendor (default: 25)
    # - Whether to discover new vendors first (default: True)
    # - Whether to add dummy data (default: False)
    
    # You can adjust these parameters as needed
    num_vendors = 50      # Increase this for more comprehensive scraping
    max_products = 100    # Increase this to get more products per vendor
    
    keyboard_parts = scraper.run(
        num_vendors=num_vendors, 
        max_products_per_vendor=max_products, 
        discover_vendors=True, 
        add_dummy_data=False
    )
    
    # Record end time and calculate duration
    end_time = datetime.now()
    duration = end_time - start_time
    
    # Format duration nicely
    hours, remainder = divmod(duration.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    duration_str = f"{hours}h {minutes}m {seconds}s"
    
    print("\nScraping completed!")
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Finished at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time elapsed: {duration_str}")
    print(f"Parts collected: {len(keyboard_parts)}")
    
    if len(keyboard_parts) > 0:
        print(f"Average time per part: {duration.total_seconds() / len(keyboard_parts):.2f} seconds")
        print(f"Average time per vendor: {duration.total_seconds() / num_vendors:.2f} seconds")
    
    print("\nDone! You can view the data in 'keyboard_parts.csv'")