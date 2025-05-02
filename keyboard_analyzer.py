import pandas as pd
import matplotlib.pyplot as plt
import os
from tabulate import tabulate
import webbrowser
import seaborn as sns
import json
from datetime import datetime
import concurrent.futures

class KeyboardAnalyzer:
    def __init__(self, csv_file='keyboard_parts.csv'):
        """Initialize the analyzer with the scraped data"""
        self.csv_file = csv_file
        self.df = None
        self.favorites = []
        self.compared_parts = []
        self.load_data()
        self.load_favorites()
        
        # Define category colors for consistent visualization
        self.category_colors = {
            'kit': '#FF6B6B',
            'pcb': '#4ECDC4',
            'case': '#FFD166',
            'plate': '#70C1B3',
            'switch': '#6B5CA5',
            'keycap': '#FF9F1C',
            'stabilizer': '#48BFE3',
            'lube': '#64B6AC',
            'foam': '#9381FF',
            'cable': '#F08080',
            'accessory': '#B8B8FF',
            'other': '#CCCCCC'
        }
        
        # Define category icons for visualization
        self.category_icons = {
            'kit': '⌨️',
            'pcb': '🔌',
            'case': '📦',
            'plate': '🛡️',
            'switch': '🔘',
            'keycap': '🎮',
            'stabilizer': '📊',
            'lube': '💧',
            'foam': '🧽',
            'cable': '🔌',
            'accessory': '🔧',
            'other': '📝'
        }
        
        # Check image URLs for validity
        self.image_status_cache = {}
    
    def load_data(self):
        """Load the keyboard parts data from CSV"""
        if not os.path.exists(self.csv_file):
            print(f"Error: {self.csv_file} not found.")
            return
        
        try:
            self.df = pd.read_csv(self.csv_file)
            print(f"Loaded {len(self.df)} keyboard parts from {self.csv_file}")
            
            # Convert price to float if needed
            if 'price' in self.df.columns:
                self.df['price'] = pd.to_numeric(self.df['price'], errors='coerce').fillna(0)
                
            # Ensure category is available for filtering
            if 'category' not in self.df.columns:
                self.df['category'] = 'other'
                
            # Clean up image URLs
            if 'image_url' in self.df.columns:
                self.df['image_url'] = self.df['image_url'].fillna('')
                # Remove empty image URLs or placeholder URLs
                self.df['image_url'] = self.df['image_url'].apply(
                    lambda x: x if x and not x.endswith(('placeholder.png', 'placeholder.jpg', 'no-image.png')) else ''
                )
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def verify_image_urls(self, max_workers=10):
        """Check image URLs to see if they're valid (in parallel)"""
        import requests
        from concurrent.futures import ThreadPoolExecutor
        
        print("Verifying image URLs (this may take a while)...")
        
        def check_url(url):
            if not url:
                return url, False
            
            try:
                response = requests.head(url, timeout=5)
                return url, response.status_code == 200
            except:
                return url, False
        
        # Get unique image URLs
        urls = self.df['image_url'].unique()
        valid_urls = set()
        
        # Check URLs in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(executor.map(check_url, urls))
            
        # Update cache with results
        for url, is_valid in results:
            self.image_status_cache[url] = is_valid
            if is_valid:
                valid_urls.add(url)
        
        # Update DataFrame with only valid image URLs
        self.df['valid_image'] = self.df['image_url'].apply(lambda x: x in valid_urls)
        
        print(f"Found {len(valid_urls)} valid images out of {len(urls)} unique URLs")
    
    def load_favorites(self):
        """Load saved favorites from JSON file"""
        if os.path.exists('keyboard_favorites.json'):
            try:
                with open('keyboard_favorites.json', 'r') as f:
                    self.favorites = json.load(f)
                print(f"Loaded {len(self.favorites)} favorites")
            except Exception as e:
                print(f"Error loading favorites: {e}")
                self.favorites = []
        else:
            self.favorites = []
    
    def save_favorites(self):
        """Save favorites to JSON file"""
        try:
            with open('keyboard_favorites.json', 'w') as f:
                json.dump(self.favorites, f, indent=4)
            print(f"Saved {len(self.favorites)} favorites")
        except Exception as e:
            print(f"Error saving favorites: {e}")
    
    def add_to_favorites(self, part_id):
        """Add a part to favorites"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        if part_id < 0 or part_id >= len(self.df):
            print(f"Invalid part ID. Must be between 0 and {len(self.df)-1}.")
            return
        
        part = self.df.iloc[part_id].to_dict()
        
        # Check if already in favorites
        if any(fav.get('url') == part['url'] for fav in self.favorites):
            print("This part is already in your favorites.")
            return
        
        # Add timestamp
        part['added_on'] = datetime.now().strftime('%Y-%m-%d')
        
        self.favorites.append(part)
        self.save_favorites()
        print(f"Added {part['name']} to favorites")
    
    def remove_from_favorites(self, fav_id):
        """Remove a part from favorites"""
        if not self.favorites or fav_id < 0 or fav_id >= len(self.favorites):
            print(f"Invalid favorite ID. Must be between 0 and {len(self.favorites)-1}.")
            return
        
        removed = self.favorites.pop(fav_id)
        self.save_favorites()
        print(f"Removed {removed['name']} from favorites")
    
    def show_favorites(self):
        """Display all favorite parts"""
        if not self.favorites:
            print("No favorites saved.")
            return
        
        print("=== Your Favorite Keyboard Parts ===")
        table_data = []
        for i, part in enumerate(self.favorites):
            # Format price with proper handling of zero/missing values
            price_str = f"${part.get('price', 0):.2f}" if part.get('price', 0) > 0 else "Price unavailable"
            
            table_data.append([
                i, 
                part.get('name', 'Unknown'),
                price_str,
                part.get('category', 'other'),
                part.get('source', 'Unknown'),
                part.get('added_on', 'Unknown')
            ])
        
        headers = ['ID', 'Name', 'Price', 'Category', 'Source', 'Added On']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
    
    def add_to_comparison(self, part_id):
        """Add a part to comparison list"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        if part_id < 0 or part_id >= len(self.df):
            print(f"Invalid part ID. Must be between 0 and {len(self.df)-1}.")
            return
        
        # Get the part
        part = self.df.iloc[part_id].to_dict()
        
        # Check if already in comparison
        if any(p.get('url') == part['url'] for p in self.compared_parts):
            print("This part is already in your comparison list.")
            return
        
        # Add to comparison list
        self.compared_parts.append(part)
        print(f"Added {part['name']} to comparison list")
        
        # Show current comparison count
        print(f"You now have {len(self.compared_parts)} items in your comparison list")
    
    def clear_comparison(self):
        """Clear the comparison list"""
        self.compared_parts = []
        print("Comparison list cleared")
    
    def show_comparison(self):
        """Show comparison of selected parts"""
        if len(self.compared_parts) < 2:
            print("You need at least 2 parts to compare. Use add_to_comparison() to add parts.")
            return
        
        print(f"=== Comparing {len(self.compared_parts)} Keyboard Parts ===")
        
        # Create a table for basic info
        basic_data = []
        for part in self.compared_parts:
            # Format price with proper handling of zero/missing values
            price_str = f"${part.get('price', 0):.2f}" if part.get('price', 0) > 0 else "Price unavailable"
            
            basic_data.append([
                part.get('name', 'Unknown'),
                price_str,
                part.get('category', 'other'),
                part.get('source', 'Unknown'),
                part.get('source_url', '')
            ])
        
        headers = ['Name', 'Price', 'Category', 'Source', 'Source Website']
        print(tabulate(basic_data, headers=headers, tablefmt='grid'))
        
        # Show links for each part
        print("\nProduct Links:")
        for i, part in enumerate(self.compared_parts):
            print(f"{i+1}. {part.get('name', 'Unknown')}: {part.get('url', 'No URL available')}")
        
        # Provide a recommendation if parts are in the same category
        categories = set(part.get('category', 'other') for part in self.compared_parts)
        if len(categories) == 1:
            category = next(iter(categories))
            prices = [part.get('price', 0) for part in self.compared_parts if part.get('price', 0) > 0]
            
            if prices:  # Only provide recommendation if we have valid prices
                avg_price = sum(prices) / len(prices)
                best_value_idx = -1
                best_value_score = 0
                
                # Find best value (using price and source reputation as factors)
                for i, part in enumerate(self.compared_parts):
                    if part.get('price', 0) > 0:  # Only consider parts with valid prices
                        # Simple value score: higher is better
                        price_ratio = part.get('price', 0) / avg_price
                        
                        # Favor prices that are lower but not too far from average
                        if price_ratio < 1:
                            value_score = 1 + (1 - price_ratio)
                        else:
                            value_score = 1 / price_ratio
                            
                        if value_score > best_value_score:
                            best_value_score = value_score
                            best_value_idx = i
                
                if best_value_idx >= 0:
                    print(f"\nRecommendation: Based on price comparison, {self.compared_parts[best_value_idx]['name']} appears to offer the best value.")
        
        # Offer to open product pages
        choice = input("\nWould you like to open any of these product pages in your browser? (Enter number or 'n' to skip): ")
        if choice.lower() != 'n':
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self.compared_parts):
                    url = self.compared_parts[idx].get('url', '')
                    if url:
                        print(f"Opening {url} in your browser...")
                        webbrowser.open(url)
                    else:
                        print("No URL available for this product.")
                else:
                    print("Invalid number.")
            except ValueError:
                print("Invalid input.")
    
    def show_basic_stats(self):
        """Display basic statistics about the keyboard parts"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        print("=== Keyboard Parts Overview ===")
        print(f"Total parts: {len(self.df)}")
        
        # Count by category
        print("\nParts by Category:")
        category_counts = self.df['category'].value_counts()
        for category, count in category_counts.items():
            print(f"{category}: {count}")
        
        # Price statistics (excluding zeros)
        valid_prices = self.df[self.df['price'] > 0]['price']
        if not valid_prices.empty:
            price_stats = valid_prices.describe()
            print("\nPrice Statistics (excluding items with no price):")
            print(f"Average: ${price_stats['mean']:.2f}")
            print(f"Minimum: ${price_stats['min']:.2f}")
            print(f"Maximum: ${price_stats['max']:.2f}")
            print(f"Median: ${price_stats['50%']:.2f}")
        else:
            print("\nNo valid price data available.")
        
        # Count by source
        print("\nTop 10 Sources:")
        source_counts = self.df['source'].value_counts().head(10)
        for source, count in source_counts.items():
            print(f"{source}: {count}")
        
        # Check for missing data
        missing_prices = len(self.df[self.df['price'] <= 0])
        missing_images = len(self.df[self.df['image_url'] == ''])
        
        print("\nData Quality:")
        print(f"Items with missing/invalid prices: {missing_prices} ({missing_prices/len(self.df)*100:.1f}%)")
        print(f"Items with missing images: {missing_images} ({missing_images/len(self.df)*100:.1f}%)")
        
        # Recent additions
        if 'scrape_date' in self.df.columns:
            self.df['scrape_date'] = pd.to_datetime(self.df['scrape_date'], errors='coerce')
            if not self.df['scrape_date'].isna().all():
                latest_date = self.df['scrape_date'].max()
                recent_items = len(self.df[self.df['scrape_date'] == latest_date])
                print(f"\nRecently added: {recent_items} items on {latest_date.strftime('%Y-%m-%d')}")
    
    def plot_category_distribution(self):
        """Plot the distribution of parts by category"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        plt.figure(figsize=(12, 8))
        
        # Count products by category
        category_counts = self.df['category'].value_counts()
        
        # Sort categories by count
        category_counts = category_counts.sort_values(ascending=False)
        
        # Get colors for each category
        colors = [self.category_colors.get(cat, '#CCCCCC') for cat in category_counts.index]
        
        # Create the bar chart
        ax = category_counts.plot(kind='bar', color=colors)
        
        plt.title('Keyboard Parts by Category', fontsize=16)
        plt.xlabel('Category', fontsize=14)
        plt.ylabel('Number of Parts', fontsize=14)
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels to the bars
        for i, v in enumerate(category_counts):
            ax.text(i, v + 0.5, str(v), ha='center', fontsize=12)
        
        plt.tight_layout()
        plt.savefig('category_distribution.png')
        plt.close()
        
        print("Category distribution plot saved as 'category_distribution.png'")
        
        # Also create a pie chart for categories
        plt.figure(figsize=(10, 10))
        plt.pie(category_counts, labels=category_counts.index, colors=colors,
                autopct='%1.1f%%', startangle=140, shadow=True)
        plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
        plt.title('Keyboard Parts by Category', fontsize=16)
        
        plt.tight_layout()
        plt.savefig('category_pie.png')
        plt.close()
        
        print("Category pie chart saved as 'category_pie.png'")
    
    def plot_price_distribution(self, category=None):
        """Plot the distribution of part prices"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        # Filter by category if specified
        if category:
            df_filtered = self.df[self.df['category'] == category]
            title_suffix = f" for {category.capitalize()} Parts"
            filename_prefix = f"{category}_"
            if df_filtered.empty:
                print(f"No parts found in category '{category}'")
                return
        else:
            df_filtered = self.df
            title_suffix = ""
            filename_prefix = ""
        
        # Filter out zero prices
        df_filtered = df_filtered[df_filtered['price'] > 0]
        
        if df_filtered.empty:
            print("No valid price data to display.")
            return
        
        plt.figure(figsize=(12, 8))
        
        # Create the histogram
        sns.histplot(df_filtered['price'], bins=20, kde=True)
        
        plt.title(f'Price Distribution{title_suffix}', fontsize=16)
        plt.xlabel('Price ($)', fontsize=14)
        plt.ylabel('Number of Parts', fontsize=14)
        plt.grid(True, alpha=0.3)
        
        # Add statistics as text
        price_stats = df_filtered['price'].describe()
        stats_text = f"Mean: ${price_stats['mean']:.2f}\n"
        stats_text += f"Median: ${price_stats['50%']:.2f}\n"
        stats_text += f"Min: ${price_stats['min']:.2f}\n"
        stats_text += f"Max: ${price_stats['max']:.2f}"
        
        plt.annotate(stats_text, xy=(0.7, 0.8), xycoords='axes fraction', 
                    bbox=dict(boxstyle="round,pad=0.5", fc="white", alpha=0.8))
        
        plt.tight_layout()
        plt.savefig(f'{filename_prefix}price_distribution.png')
        plt.close()
        
        print(f"Price distribution plot saved as '{filename_prefix}price_distribution.png'")
    
    def plot_price_by_category(self):
        """Plot the average price by category"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        # Filter out zero prices
        df_filtered = self.df[self.df['price'] > 0]
        
        if df_filtered.empty:
            print("No valid price data to display.")
            return
        
        # Calculate average price by category
        category_avg_price = df_filtered.groupby('category')['price'].mean().sort_values(ascending=False)
        
        plt.figure(figsize=(12, 8))
        
        # Get colors for each category
        colors = [self.category_colors.get(cat, '#CCCCCC') for cat in category_avg_price.index]
        
        # Create the bar chart
        ax = category_avg_price.plot(kind='bar', color=colors)
        
        plt.title('Average Price by Category', fontsize=16)
        plt.xlabel('Category', fontsize=14)
        plt.ylabel('Average Price ($)', fontsize=14)
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels to the bars
        for i, v in enumerate(category_avg_price):
            ax.text(i, v + 1, f"${v:.2f}", ha='center', fontsize=12)
        
        plt.tight_layout()
        plt.savefig('price_by_category.png')
        plt.close()
        
        print("Average price by category plot saved as 'price_by_category.png'")
    
    def plot_source_comparison(self, top_n=10):
        """Plot comparison of parts by source"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        # Get top N sources by count
        top_sources = self.df['source'].value_counts().head(top_n).index
        df_filtered = self.df[self.df['source'].isin(top_sources)]
        
        if df_filtered.empty:
            print("No valid source data to display.")
            return
        
        plt.figure(figsize=(14, 10))
        
        # Plot 1: Part Count by Source
        plt.subplot(2, 1, 1)
        source_counts = df_filtered['source'].value_counts()
        ax1 = source_counts.plot(kind='bar', color='skyblue')
        plt.title(f'Top {top_n} Sources by Part Count', fontsize=16)
        plt.xlabel('Source', fontsize=14)
        plt.ylabel('Number of Parts', fontsize=14)
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels
        for i, v in enumerate(source_counts):
            ax1.text(i, v + 0.5, str(v), ha='center', fontsize=12)
        
        # Plot 2: Category Distribution by Source
        plt.subplot(2, 1, 2)
        
        # Create a crosstab (pivot table) of source and category
        category_by_source = pd.crosstab(df_filtered['source'], df_filtered['category'])
        
        # Sort the table by total count
        category_by_source = category_by_source.loc[source_counts.index]
        
        # Plot stacked bar chart
        category_by_source.plot(kind='bar', stacked=True, figsize=(14, 8), 
                               colormap='tab20')
        
        plt.title(f'Category Distribution by Source (Top {top_n})', fontsize=16)
        plt.xlabel('Source', fontsize=14)
        plt.ylabel('Number of Parts', fontsize=14)
        plt.xticks(rotation=45, ha='right')
        plt.legend(title='Category', bbox_to_anchor=(1.05, 1), loc='upper left')
        
        plt.tight_layout()
        plt.savefig('source_comparison.png')
        plt.close()
        
        print("Source comparison plot saved as 'source_comparison.png'")
    
    def find_parts_in_category(self, category, min_price=0, max_price=float('inf')):
        """Find parts within a specific category and price range"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        if category not in self.df['category'].unique():
            print(f"No parts found in category '{category}'")
            matching_categories = [cat for cat in self.df['category'].unique() 
                                if category.lower() in cat.lower()]
            if matching_categories:
                print(f"Did you mean: {', '.join(matching_categories)}?")
            return
        
        # Use min_price only if it's greater than 0
        price_filter = (self.df['category'] == category)
        if min_price > 0:
            price_filter = price_filter & (self.df['price'] >= min_price)
        if max_price < float('inf'):
            price_filter = price_filter & (self.df['price'] <= max_price)
            
        # Filter items with price = 0 only if min_price > 0
        if min_price > 0:
            price_filter = price_filter & (self.df['price'] > 0)
            
        results = self.df[price_filter]
        
        if results.empty:
            print(f"No {category} parts found in the price range ${min_price} - ${max_price}")
            return
        
        print(f"Found {len(results)} {category} parts in the price range ${min_price} - ${max_price}:")
        results_sorted = results.sort_values('price')
        
        # Display results in a nice table
        table_data = []
        for i, (_, row) in enumerate(results_sorted.iterrows()):
            # Format price with proper handling of zero/missing values
            price_str = f"${row['price']:.2f}" if row['price'] > 0 else "Price unavailable"
            
            table_data.append([
                i, row['name'], price_str, row['source'], row['url']
            ])
        
        headers = ['ID', 'Name', 'Price', 'Source', 'URL']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        return results_sorted
    
    def find_parts_by_price(self, min_price=0, max_price=float('inf')):
        """Find parts within a specific price range across all categories"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        # Handle price filtering properly
        if min_price > 0:
            results = self.df[(self.df['price'] >= min_price) & (self.df['price'] <= max_price)]
        else:
            # If min_price is 0, include all items with valid prices
            results = self.df[self.df['price'] <= max_price]
        
        if results.empty:
            print(f"No parts found in the price range ${min_price} - ${max_price}")
            return
        
        print(f"Found {len(results)} parts in the price range ${min_price} - ${max_price}:")
        results_sorted = results.sort_values('price')
        
        # Display results in a nice table
        table_data = []
        for i, (_, row) in enumerate(results_sorted.iterrows()):
            # Format price with proper handling of zero/missing values
            price_str = f"${row['price']:.2f}" if row['price'] > 0 else "Price unavailable"
            
            table_data.append([
                i, row['name'], price_str, row['category'], row['source']
            ])
        
        headers = ['ID', 'Name', 'Price', 'Category', 'Source']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        return results_sorted
    
    def find_parts_by_keyword(self, keyword):
        """Find parts containing a specific keyword in name or category"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        # Case-insensitive search in name and category columns
        keyword = keyword.lower()
        results = self.df[
            self.df['name'].str.lower().str.contains(keyword) | 
            self.df['category'].str.lower().str.contains(keyword)
        ]
        
        if results.empty:
            print(f"No parts found containing '{keyword}'")
            return
        
        print(f"Found {len(results)} parts containing '{keyword}':")
        results_sorted = results.sort_values('price')
        
        # Display results in a nice table
        table_data = []
        for i, (_, row) in enumerate(results_sorted.iterrows()):
            # Format price with proper handling of zero/missing values
            price_str = f"${row['price']:.2f}" if row['price'] > 0 else "Price unavailable"
            
            table_data.append([
                i, row['name'], price_str, row['category'], row['source']
            ])
        
        headers = ['ID', 'Name', 'Price', 'Category', 'Source']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        return results_sorted
    
    def find_parts_by_source(self, source_name):
        """Find parts from a specific source vendor"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        # Case-insensitive search for source
        source_name = source_name.lower()
        
        # Find matching sources
        matching_sources = [src for src in self.df['source'].unique() 
                           if source_name in src.lower()]
        
        if not matching_sources:
            print(f"No sources found matching '{source_name}'")
            return
        
        # If multiple matches, let user choose
        if len(matching_sources) > 1:
            print(f"Found multiple sources matching '{source_name}':")
            for i, src in enumerate(matching_sources):
                count = len(self.df[self.df['source'] == src])
                print(f"{i+1}. {src} ({count} parts)")
            
            choice = input("Enter the number of the source to view (or 'a' for all): ")
            if choice.lower() == 'a':
                # Use all matching sources
                pass
            else:
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(matching_sources):
                        matching_sources = [matching_sources[idx]]
                    else:
                        print("Invalid choice. Showing all matching sources.")
                except ValueError:
                    print("Invalid input. Showing all matching sources.")
        
        # Filter by chosen source(s)
        results = self.df[self.df['source'].isin(matching_sources)]
        
        print(f"Found {len(results)} parts from {', '.join(matching_sources)}:")
        results_sorted = results.sort_values(['category', 'price'])
        
        # Display results in a nice table
        table_data = []
        for i, (_, row) in enumerate(results_sorted.iterrows()):
            # Format price with proper handling of zero/missing values
            price_str = f"${row['price']:.2f}" if row['price'] > 0 else "Price unavailable"
            
            table_data.append([
                i, row['name'], price_str, row['category'], row['source']
            ])
        
        headers = ['ID', 'Name', 'Price', 'Category', 'Source']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        return results_sorted
    
    def compare_parts(self, part_ids):
        """Compare specific parts by their IDs"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        if not part_ids or len(part_ids) < 2:
            print("Please provide at least 2 part IDs to compare.")
            return
        
        if max(part_ids) >= len(self.df) or min(part_ids) < 0:
            print(f"Invalid part ID. IDs must be between 0 and {len(self.df)-1}.")
            return
        
        # Get the selected parts
        selected = self.df.iloc[part_ids]
        
        # Clear current comparison and add these parts
        self.compared_parts = []
        for _, row in selected.iterrows():
            self.compared_parts.append(row.to_dict())
        
        # Show the comparison
        self.show_comparison()
    
    def list_all_parts(self, sort_by='price', category=None, include_invalid_prices=True, max_items=100):
        """List all parts, sorted by the specified column and optionally filtered by category"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        if sort_by not in self.df.columns:
            print(f"Invalid sort column. Available columns: {list(self.df.columns)}")
            return
        
        # Filter by category if specified
        if category:
            df_filtered = self.df[self.df['category'] == category]
            if df_filtered.empty:
                print(f"No parts found in category '{category}'")
                return
        else:
            df_filtered = self.df
        
        # Filter out invalid prices if requested
        if not include_invalid_prices:
            df_filtered = df_filtered[df_filtered['price'] > 0]
            if df_filtered.empty:
                print("No parts found with valid prices")
                return
        
        # Sort and display
        sorted_df = df_filtered.sort_values(sort_by)
        
        # Limit the number of items shown to avoid overwhelming the console
        if len(sorted_df) > max_items:
            print(f"Found {len(sorted_df)} parts. Showing first {max_items}.")
            sorted_df = sorted_df.head(max_items)
        else:
            print(f"Found {len(sorted_df)} parts.")
            
        print(f"All parts sorted by {sort_by}:" + (f" (Category: {category})" if category else ""))
        
        # Add an ID column for reference
        sorted_df = sorted_df.reset_index(drop=True)
        
        # Display table with ID column for reference
        table_data = []
        for i, row in sorted_df.iterrows():
            # Format price with proper handling of zero/missing values
            price_str = f"${row['price']:.2f}" if row['price'] > 0 else "Price unavailable"
            
            table_data.append([
                i, row['name'], price_str, row['category'], row['source']
            ])
        
        headers = ['ID', 'Name', 'Price', 'Category', 'Source']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        return sorted_df
    
    def open_part_url(self, part_id):
        """Open the URL for a specific part in the web browser"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        if part_id < 0 or part_id >= len(self.df):
            print(f"Invalid part ID. Must be between 0 and {len(self.df)-1}.")
            return
        
        # Get the URL
        part = self.df.iloc[part_id]
        url = part['url']
        
        if not url or url == 'Unknown':
            print(f"No URL available for part: {part['name']}")
            return
        
        print(f"Opening URL for {part['name']}: {url}")
        webbrowser.open(url)
    
    def export_filtered_results(self, filtered_df, filename='filtered_parts.csv'):
        """Export filtered results to a new CSV file"""
        if filtered_df is None or filtered_df.empty:
            print("No data to export.")
            return
        
        try:
            filtered_df.to_csv(filename, index=False)
            print(f"Exported {len(filtered_df)} parts to {filename}")
        except Exception as e:
            print(f"Error exporting data: {e}")
    
    def generate_recommendations(self, budget, category=None):
        """Generate part recommendations based on budget and optionally category"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        # Filter by category if specified
        if category:
            df_filtered = self.df[self.df['category'] == category]
            if df_filtered.empty:
                print(f"No parts found in category '{category}'")
                return
        else:
            df_filtered = self.df
        
        # Only consider items with valid prices
        df_filtered = df_filtered[df_filtered['price'] > 0]
        
        if df_filtered.empty:
            print("No parts with valid prices found.")
            return
        
        # Find parts within budget
        in_budget = df_filtered[df_filtered['price'] <= budget]
        
        if in_budget.empty:
            print(f"No {'parts' if not category else category} found within budget ${budget}")
            
            # Suggest closest options above budget
            above_budget = df_filtered[df_filtered['price'] > budget].sort_values('price')
            if not above_budget.empty:
                next_option = above_budget.iloc[0]
                print(f"The closest option is {next_option['name']} at ${next_option['price']:.2f} (${next_option['price'] - budget:.2f} above your budget)")
            return
        
        # Get top recommendations (highest price within budget, assuming higher price = better quality)
        # Group by category and get the top item in each
        if category:
            # If category specified, just get top 5 in that category
            top_recs = in_budget.sort_values('price', ascending=False).head(5)
        else:
            # Otherwise, try to get recommendations across categories
            categories = in_budget['category'].unique()
            top_recs = pd.DataFrame()
            
            for cat in categories:
                cat_items = in_budget[in_budget['category'] == cat]
                if not cat_items.empty:
                    # Get the top item in each category
                    top_cat_item = cat_items.sort_values('price', ascending=False).head(1)
                    top_recs = pd.concat([top_recs, top_cat_item])
            
            # If we have too many categories, limit to top 5 by price
            if len(top_recs) > 5:
                top_recs = top_recs.sort_values('price', ascending=False).head(5)
        
        print(f"Top Recommended {'Parts' if not category else category.capitalize()} (Budget: ${budget}):")
        table_data = []
        for i, (_, row) in enumerate(top_recs.iterrows()):
            price_str = f"${row['price']:.2f}"
            
            table_data.append([
                i, row['name'], price_str, row['category'], row['source'], row['url']
            ])
        
        headers = ['ID', 'Name', 'Price', 'Category', 'Source', 'URL']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        
        return top_recs
    
    def build_custom_keyboard(self, budget):
        """Suggest a complete keyboard build within the specified budget"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        # Filter out items with invalid prices
        df_valid = self.df[self.df['price'] > 0]
        
        if df_valid.empty:
            print("No parts with valid prices found.")
            return
        
        print(f"=== Custom Keyboard Build (Budget: ${budget}) ===")
        
        # Define essential components and allocate budget percentage
        essential_categories = {
            'kit': 0.40,  # 40% of budget for kit or (case + pcb + plate)
            'switch': 0.30,  # 30% of budget for switches
            'keycap': 0.20,  # 20% of budget for keycaps
            'stabilizer': 0.05,  # 5% of budget for stabilizers
            'lube': 0.03,  # 3% of budget for lube
            'accessory': 0.02  # 2% of budget for accessories
        }
        
        # First, check if there are complete kits available
        kit_budget = budget * essential_categories['kit']
        kits = df_valid[(df_valid['category'] == 'kit') & (df_valid['price'] <= kit_budget)]
        
        total_cost = 0
        selected_parts = {}
        
        if not kits.empty:
            # Use the most expensive kit within budget
            selected_kit = kits.sort_values('price', ascending=False).iloc[0]
            selected_parts['kit'] = selected_kit
            total_cost += selected_kit['price']
            print(f"Selected Kit (${selected_kit['price']:.2f}):")
            print(f"  {selected_kit['name']} from {selected_kit['source']}")
            
            # If we're using a kit, we don't need separate case, pcb, plate
            remaining_categories = {k: v for k, v in essential_categories.items() if k not in ['kit']}
            remaining_budget = budget - total_cost
        else:
            # No suitable kit found, try to find individual components
            print("No suitable keyboard kit found within budget. Looking for individual components...")
            
            # First, find a case
            case_budget = budget * 0.15
            cases = df_valid[(df_valid['category'] == 'case') & (df_valid['price'] <= case_budget)]
            if cases.empty:
                print("Could not find a suitable case within budget.")
                return
            
            selected_case = cases.sort_values('price', ascending=False).iloc[0]
            selected_parts['case'] = selected_case
            total_cost += selected_case['price']
            print(f"Selected Case (${selected_case['price']:.2f}):")
            print(f"  {selected_case['name']} from {selected_case['source']}")
            
            # Next, find a PCB
            pcb_budget = budget * 0.15
            pcbs = df_valid[(df_valid['category'] == 'pcb') & (df_valid['price'] <= pcb_budget)]
            if pcbs.empty:
                print("Could not find a suitable PCB within budget.")
                return
            
            selected_pcb = pcbs.sort_values('price', ascending=False).iloc[0]
            selected_parts['pcb'] = selected_pcb
            total_cost += selected_pcb['price']
            print(f"Selected PCB (${selected_pcb['price']:.2f}):")
            print(f"  {selected_pcb['name']} from {selected_pcb['source']}")
            
            # Next, find a plate
            plate_budget = budget * 0.10
            plates = df_valid[(df_valid['category'] == 'plate') & (df_valid['price'] <= plate_budget)]
            if not plates.empty:
                selected_plate = plates.sort_values('price', ascending=False).iloc[0]
                selected_parts['plate'] = selected_plate
                total_cost += selected_plate['price']
                print(f"Selected Plate (${selected_plate['price']:.2f}):")
                print(f"  {selected_plate['name']} from {selected_plate['source']}")
            else:
                print("No suitable plate found within budget. This might be included with the case or PCB.")
            
            # Remove kit, case, pcb, plate from remaining categories
            remaining_categories = {k: v for k, v in essential_categories.items() 
                                 if k not in ['kit', 'case', 'pcb', 'plate']}
            remaining_budget = budget - total_cost
        
        # Calculate new adjusted budgets based on remaining budget
        total_weight = sum(remaining_categories.values())
        adjusted_categories = {k: (v / total_weight) * remaining_budget for k, v in remaining_categories.items()}
        
        # Find switches
        switch_budget = adjusted_categories.get('switch', 0)
        if switch_budget > 0:
            switches = df_valid[(df_valid['category'] == 'switch') & (df_valid['price'] <= switch_budget)]
            if not switches.empty:
                selected_switch = switches.sort_values('price', ascending=False).iloc[0]
                selected_parts['switch'] = selected_switch
                total_cost += selected_switch['price']
                print(f"Selected Switches (${selected_switch['price']:.2f}):")
                print(f"  {selected_switch['name']} from {selected_switch['source']}")
            else:
                print("Could not find suitable switches within budget.")
        
        # Find keycaps
        keycap_budget = adjusted_categories.get('keycap', 0)
        if keycap_budget > 0:
            keycaps = df_valid[(df_valid['category'] == 'keycap') & (df_valid['price'] <= keycap_budget)]
            if not keycaps.empty:
                selected_keycap = keycaps.sort_values('price', ascending=False).iloc[0]
                selected_parts['keycap'] = selected_keycap
                total_cost += selected_keycap['price']
                print(f"Selected Keycaps (${selected_keycap['price']:.2f}):")
                print(f"  {selected_keycap['name']} from {selected_keycap['source']}")
            else:
                print("Could not find suitable keycaps within budget.")
        
        # Find stabilizers
        stab_budget = adjusted_categories.get('stabilizer', 0)
        if stab_budget > 0:
            stabs = df_valid[(df_valid['category'] == 'stabilizer') & (df_valid['price'] <= stab_budget)]
            if not stabs.empty:
                selected_stab = stabs.sort_values('price', ascending=False).iloc[0]
                selected_parts['stabilizer'] = selected_stab
                total_cost += selected_stab['price']
                print(f"Selected Stabilizers (${selected_stab['price']:.2f}):")
                print(f"  {selected_stab['name']} from {selected_stab['source']}")
            else:
                print("Could not find suitable stabilizers within budget. They might be included with the kit.")
        
        # Find lube
        lube_budget = adjusted_categories.get('lube', 0)
        if lube_budget > 0:
            lubes = df_valid[(df_valid['category'] == 'lube') & (df_valid['price'] <= lube_budget)]
            if not lubes.empty:
                selected_lube = lubes.sort_values('price', ascending=False).iloc[0]
                selected_parts['lube'] = selected_lube
                total_cost += selected_lube['price']
                print(f"Selected Lube (${selected_lube['price']:.2f}):")
                print(f"  {selected_lube['name']} from {selected_lube['source']}")
        
        # Summary
        print("\n=== Build Summary ===")
        print(f"Total Cost: ${total_cost:.2f}")
        print(f"Remaining Budget: ${budget - total_cost:.2f}")
        
        # Ask if user wants to add these parts to comparison
        choice = input("\nWould you like to add these parts to your comparison list? (y/n): ")
        if choice.lower() == 'y':
            self.compared_parts = list(selected_parts.values())
            print(f"Added {len(selected_parts)} parts to comparison list")
        
        return selected_parts
    
    def suggest_compatible_parts(self, part_id):
        """Suggest parts that are compatible with a selected part"""
        if self.df is None or self.df.empty:
            print("No data available.")
            return
        
        if part_id < 0 or part_id >= len(self.df):
            print(f"Invalid part ID. Must be between 0 and {len(self.df)-1}.")
            return
        
        # Get the selected part
        selected_part = self.df.iloc[part_id]
        print(f"Finding compatible parts for: {selected_part['name']} ({selected_part['category']})")
        
        # Define compatibility rules based on part category
        if selected_part['category'] == 'kit':
            # For kits, suggest compatible switches, keycaps, lube
            print("\nA keyboard kit typically includes a case, PCB, and plate. You'll need:")
            compatible_categories = ['switch', 'keycap', 'stabilizer', 'lube']
        elif selected_part['category'] == 'case':
            # For cases, suggest compatible PCBs, plates
            print("\nFor this case, you'll need:")
            compatible_categories = ['pcb', 'plate', 'switch', 'keycap', 'stabilizer', 'lube']
        elif selected_part['category'] == 'pcb':
            # For PCBs, suggest compatible cases, plates, switches
            print("\nFor this PCB, you'll need:")
            compatible_categories = ['case', 'plate', 'switch', 'keycap', 'stabilizer', 'lube']
        elif selected_part['category'] == 'switch':
            # For switches, suggest compatible PCBs, lube
            print("\nFor these switches, consider:")
            compatible_categories = ['lube', 'keycap']
        elif selected_part['category'] == 'keycap':
            # For keycaps, suggest compatible switches
            print("\nThese keycaps would pair well with:")
            compatible_categories = ['switch', 'kit', 'case']
        else:
            # For other categories, suggest generally popular items
            print("\nPopular parts to pair with this:")
            compatible_categories = ['kit', 'switch', 'keycap']
        
        # Show suggestions for each compatible category
        for category in compatible_categories:
            # Only consider items with valid prices
            category_parts = self.df[(self.df['category'] == category) & (self.df['price'] > 0)]
            category_parts = category_parts.sort_values('price', ascending=False).head(3)
            
            if not category_parts.empty:
                print(f"\n{category.capitalize()} suggestions:")
                
                for i, (_, part) in enumerate(category_parts.iterrows()):
                    print(f"  {i+1}. {part['name']} - ${part['price']:.2f} from {part['source']}")
                    
                    # Offer to add to comparison
                    if i == 0:  # Only for the first item to keep things clean
                        add = input(f"    Add {part['name']} to comparison list? (y/n): ")
                        if add.lower() == 'y':
                            self.add_to_comparison(part.name)

def main():
    analyzer = KeyboardAnalyzer()
    
    if analyzer.df is not None and not analyzer.df.empty:
        # Optionally verify images (can be slow)
        verify_images = input("Would you like to verify all image URLs? This can take some time but improves the viewing experience (y/n): ")
        if verify_images.lower() == 'y':
            analyzer.verify_image_urls()
        
        while True:
            print("\n=== Keyboard Parts Analyzer ===")
            print("1. Show basic statistics")
            print("2. Plot category distribution")
            print("3. Plot price distribution")
            print("4. Plot price by category")
            print("5. Plot source comparison")
            print("6. Find parts by category and price")
            print("7. Find parts by price")
            print("8. Find parts by keyword")
            print("9. Find parts by source")
            print("10. List all parts")
            print("11. Compare parts")
            print("12. View comparison list")
            print("13. Open part URL")
            print("14. Generate recommendations")
            print("15. Build custom keyboard within budget")
            print("16. Suggest compatible parts")
            print("17. Manage favorites")
            print("18. Export filtered results")
            print("19. Exit")
            
            choice = input("\nEnter your choice (1-19): ")
            
            if choice == '1':
                analyzer.show_basic_stats()
            
            elif choice == '2':
                analyzer.plot_category_distribution()
            
            elif choice == '3':
                category = input("Filter by category? (leave empty for all): ")
                analyzer.plot_price_distribution(category if category else None)
            
            elif choice == '4':
                analyzer.plot_price_by_category()
            
            elif choice == '5':
                try:
                    top_n = int(input("Number of top sources to show (default 10): ") or 10)
                    analyzer.plot_source_comparison(top_n)
                except ValueError:
                    print("Invalid input. Using default value of 10.")
                    analyzer.plot_source_comparison(10)
            
            elif choice == '6':
                try:
                    category = input("Enter category: ")
                    min_price = float(input("Enter minimum price (0 for any): $") or 0)
                    max_price = float(input("Enter maximum price (empty for any): $") or float('inf'))
                    results = analyzer.find_parts_in_category(category, min_price, max_price)
                    
                    if results is not None and not results.empty:
                        export = input("Export results to CSV? (y/n): ")
                        if export.lower() == 'y':
                            filename = input("Enter filename (default: filtered_parts.csv): ") or "filtered_parts.csv"
                            analyzer.export_filtered_results(results, filename)
                except ValueError:
                    print("Invalid input. Please enter numeric values for prices.")
            
            elif choice == '7':
                try:
                    min_price = float(input("Enter minimum price (0 for any): $") or 0)
                    max_price = float(input("Enter maximum price (empty for any): $") or float('inf'))
                    results = analyzer.find_parts_by_price(min_price, max_price)
                    
                    if results is not None and not results.empty:
                        export = input("Export results to CSV? (y/n): ")
                        if export.lower() == 'y':
                            filename = input("Enter filename (default: filtered_parts.csv): ") or "filtered_parts.csv"
                            analyzer.export_filtered_results(results, filename)
                except ValueError:
                    print("Invalid input. Please enter numeric values for prices.")
            
            elif choice == '8':
                keyword = input("Enter keyword to search for: ")
                if keyword:
                    results = analyzer.find_parts_by_keyword(keyword)
                    
                    if results is not None and not results.empty:
                        export = input("Export results to CSV? (y/n): ")
                        if export.lower() == 'y':
                            filename = input("Enter filename (default: filtered_parts.csv): ") or "filtered_parts.csv"
                            analyzer.export_filtered_results(results, filename)
                else:
                    print("Please enter a keyword to search for.")
            
            elif choice == '9':
                source = input("Enter source name to search for: ")
                if source:
                    results = analyzer.find_parts_by_source(source)
                    
                    if results is not None and not results.empty:
                        export = input("Export results to CSV? (y/n): ")
                        if export.lower() == 'y':
                            filename = input("Enter filename (default: filtered_parts.csv): ") or "filtered_parts.csv"
                            analyzer.export_filtered_results(results, filename)
                else:
                    print("Please enter a source name to search for.")
            
            elif choice == '10':
                sort_options = {
                    '1': 'price',
                    '2': 'name',
                    '3': 'category',
                    '4': 'source'
                }
                
                print("Sort by:")
                print("1. Price")
                print("2. Name")
                print("3. Category")
                print("4. Source")
                
                sort_choice = input("Enter sort option (1-4): ")
                category_filter = input("Filter by category? (leave empty for all): ")
                include_invalid = input("Include parts with missing prices? (y/n, default: y): ") or 'y'
                
                if sort_choice in sort_options:
                    analyzer.list_all_parts(
                        sort_options[sort_choice], 
                        category_filter if category_filter else None,
                        include_invalid_prices=(include_invalid.lower() == 'y')
                    )
                else:
                    print("Invalid sort option.")
            
            elif choice == '11':
                try:
                    # First list all parts for reference
                    max_display = int(input("Maximum number of parts to display (default 50): ") or 50)
                    analyzer.list_all_parts(max_items=max_display)
                    
                    # Get part IDs to compare
                    ids_input = input("Enter part IDs to compare (comma-separated, e.g., 0,3,5): ")
                    ids = [int(id_str.strip()) for id_str in ids_input.split(',')]
                    
                    analyzer.compare_parts(ids)
                except ValueError:
                    print("Invalid input. Please enter numeric IDs separated by commas.")
            
            elif choice == '12':
                if analyzer.compared_parts:
                    analyzer.show_comparison()
                else:
                    print("No parts in comparison list yet. Use option 11 to add parts.")
            
            elif choice == '13':
                try:
                    # First list all parts for reference
                    max_display = int(input("Maximum number of parts to display (default 50): ") or 50)
                    analyzer.list_all_parts(max_items=max_display)
                    
                    # Get part ID to open
                    id_input = input("Enter part ID to open URL: ")
                    id_num = int(id_input.strip())
                    
                    analyzer.open_part_url(id_num)
                except ValueError:
                    print("Invalid input. Please enter a numeric ID.")
            
            elif choice == '14':
                try:
                    budget = float(input("Enter your budget: $"))
                    category = input("Filter by category? (leave empty for all): ")
                    analyzer.generate_recommendations(budget, category if category else None)
                except ValueError:
                    print("Invalid input. Please enter a numeric value for budget.")
            
            elif choice == '15':
                try:
                    budget = float(input("Enter your budget for a complete keyboard: $"))
                    analyzer.build_custom_keyboard(budget)
                except ValueError:
                    print("Invalid input. Please enter a numeric value for budget.")
            
            elif choice == '16':
                try:
                    # List all parts for reference
                    max_display = int(input("Maximum number of parts to display (default 50): ") or 50)
                    analyzer.list_all_parts(max_items=max_display)
                    
                    # Get part ID for compatibility suggestions
                    id_input = input("Enter part ID to find compatible parts: ")
                    id_num = int(id_input.strip())
                    
                    analyzer.suggest_compatible_parts(id_num)
                except ValueError:
                    print("Invalid input. Please enter a numeric ID.")
            
            elif choice == '17':
                while True:
                    print("\n=== Favorites Management ===")
                    print("1. View favorites")
                    print("2. Add to favorites")
                    print("3. Remove from favorites")
                    print("4. Back to main menu")
                    
                    fav_choice = input("\nEnter your choice (1-4): ")
                    
                    if fav_choice == '1':
                        analyzer.show_favorites()
                    
                    elif fav_choice == '2':
                        try:
                            # List all parts for reference
                            max_display = int(input("Maximum number of parts to display (default 50): ") or 50)
                            analyzer.list_all_parts(max_items=max_display)
                            
                            # Get part ID to add
                            id_input = input("Enter part ID to add to favorites: ")
                            id_num = int(id_input.strip())
                            
                            analyzer.add_to_favorites(id_num)
                        except ValueError:
                            print("Invalid input. Please enter a numeric ID.")
                    
                    elif fav_choice == '3':
                        try:
                            # Show favorites for reference
                            analyzer.show_favorites()
                            
                            if analyzer.favorites:
                                # Get favorite ID to remove
                                id_input = input("Enter favorite ID to remove: ")
                                id_num = int(id_input.strip())
                                
                                analyzer.remove_from_favorites(id_num)
                        except ValueError:
                            print("Invalid input. Please enter a numeric ID.")
                    
                    elif fav_choice == '4':
                        break
                    
                    else:
                        print("Invalid choice. Please enter a number between 1 and 4.")
            
            elif choice == '18':
                # Select what to export
                print("\nWhat would you like to export?")
                print("1. All parts")
                print("2. Filtered by category")
                print("3. Filtered by price range")
                print("4. Filtered by keyword")
                print("5. Filtered by source")
                print("6. Favorites")
                print("7. Comparison list")
                
                export_choice = input("\nEnter your choice (1-7): ")
                
                try:
                    if export_choice == '1':
                        filename = input("Enter filename (default: all_parts.csv): ") or "all_parts.csv"
                        analyzer.export_filtered_results(analyzer.df, filename)
                    
                    elif export_choice == '2':
                        category = input("Enter category to filter by: ")
                        filtered = analyzer.df[analyzer.df['category'] == category]
                        
                        if filtered.empty:
                            print(f"No parts found in category '{category}'")
                        else:
                            filename = input(f"Enter filename (default: {category}_parts.csv): ") or f"{category}_parts.csv"
                            analyzer.export_filtered_results(filtered, filename)
                    
                    elif export_choice == '3':
                        min_price = float(input("Enter minimum price (0 for any): $") or 0)
                        max_price = float(input("Enter maximum price (empty for any): $") or float('inf'))
                        
                        if min_price > 0:
                            filtered = analyzer.df[(analyzer.df['price'] >= min_price) & (analyzer.df['price'] <= max_price)]
                        else:
                            filtered = analyzer.df[analyzer.df['price'] <= max_price]
                        
                        if filtered.empty:
                            print(f"No parts found in the price range ${min_price} - ${max_price}")
                        else:
                            filename = input("Enter filename (default: price_filtered_parts.csv): ") or "price_filtered_parts.csv"
                            analyzer.export_filtered_results(filtered, filename)
                    
                    elif export_choice == '4':
                        keyword = input("Enter keyword to filter by: ")
                        
                        filtered = analyzer.df[
                            analyzer.df['name'].str.lower().str.contains(keyword.lower()) | 
                            analyzer.df['category'].str.lower().str.contains(keyword.lower())
                        ]
                        
                        if filtered.empty:
                            print(f"No parts found containing '{keyword}'")
                        else:
                            filename = input(f"Enter filename (default: {keyword}_parts.csv): ") or f"{keyword}_parts.csv"
                            analyzer.export_filtered_results(filtered, filename)
                    
                    elif export_choice == '5':
                        source_name = input("Enter source name to filter by: ")
                        
                        # Case-insensitive source matching
                        matching_sources = [src for src in analyzer.df['source'].unique() 
                                        if source_name.lower() in src.lower()]
                        
                        if not matching_sources:
                            print(f"No sources found matching '{source_name}'")
                        else:
                            filtered = analyzer.df[analyzer.df['source'].isin(matching_sources)]
                            filename = input(f"Enter filename (default: {source_name}_parts.csv): ") or f"{source_name}_parts.csv"
                            analyzer.export_filtered_results(filtered, filename)
                    
                    elif export_choice == '6':
                        if not analyzer.favorites:
                            print("No favorites to export.")
                        else:
                            # Convert favorites to DataFrame
                            fav_df = pd.DataFrame(analyzer.favorites)
                            filename = input("Enter filename (default: favorite_parts.csv): ") or "favorite_parts.csv"
                            analyzer.export_filtered_results(fav_df, filename)
                    
                    elif export_choice == '7':
                        if not analyzer.compared_parts:
                            print("No parts in comparison list to export.")
                        else:
                            # Convert comparison list to DataFrame
                            comp_df = pd.DataFrame(analyzer.compared_parts)
                            filename = input("Enter filename (default: comparison_parts.csv): ") or "comparison_parts.csv"
                            analyzer.export_filtered_results(comp_df, filename)
                    
                    else:
                        print("Invalid choice.")
                
                except ValueError:
                    print("Invalid input. Please enter numeric values where required.")
            
            elif choice == '19':
                print("Exiting the Keyboard Parts Analyzer. Goodbye!")
                break
            
            else:
                print("Invalid choice. Please enter a number between 1 and 19.")
            
            input("\nPress Enter to continue...")
    else:
        print("No data available. Please make sure the keyboard_parts.csv file exists and is not empty.")
        print("You can run the keyboard_scraper.py script to gather keyboard parts data first.")
        
        # Offer to run the scraper
        run_scraper = input("Would you like to run the keyboard scraper now? (y/n): ")
        if run_scraper.lower() == 'y':
            try:
                from keyboard_scraper import KeyboardScraper
                print("\nRunning keyboard scraper...")
                scraper = KeyboardScraper()
                scraper.run()
                print("\nScraper completed. Please restart the analyzer to load the new data.")
            except ImportError:
                print("Could not import the keyboard scraper. Make sure keyboard_scraper.py is in the same directory.")
            except Exception as e:
                print(f"Error running the scraper: {e}")

if __name__ == "__main__":
    main()