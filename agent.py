import json
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration
NEWS_DIR = "news"
INDEX_FILE = "news-index.json"
API_KEY = os.getenv("NEWS_API_KEY") # Read from .env local or GitHub Secrets

def ensure_dirs():
    if not os.path.exists(NEWS_DIR):
        os.makedirs(NEWS_DIR)

def load_index():
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

def save_index(index):
    # Sort by date descending
    index.sort(key=lambda x: x['date'], reverse=True)
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2)

def add_news_item(title, description, content, date=None, category="Tech"):
    ensure_dirs()
    
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
        
    # Generate slug (cleaner version)
    slug = "".join(c for c in title.lower() if c.isalnum() or c == ' ').strip().replace(' ', '-')
    
    # Check if already exists in index
    index = load_index()
    if any(item['slug'] == slug for item in index):
        return False

    # Save markdown file
    filepath = os.path.join(NEWS_DIR, f"{slug}.md")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        if "![image]" not in content and "http" in content: # Basic image check
             f.write(f"{content}\n\n")
        else:
             f.write(f"{content}\n\n")
    
    # Update index
    item = {
        "title": title,
        "slug": slug,
        "date": date,
        "description": description,
        "category": category
    }
    index.append(item)
    save_index(index)
    print(f"Added news item: {title}")
    return True

def fetch_tech_news():
    if not API_KEY:
        print("NEWS_API_KEY not found in environment. Skipping fetch.")
        return

    url = f"https://newsapi.org/v2/top-headlines?category=technology&language=en&apiKey={API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data.get("status") == "ok":
            articles = data.get("articles", [])
            added_count = 0
            
            for art in articles:
                if not art.get('title') or not art.get('description') or '[Removed]' in art['title']:
                    continue
                    
                title = art['title']
                desc = art['description']
                content = art.get('content', desc)
                if art.get('urlToImage'):
                    content = f"![{title}]({art['urlToImage']})\n\n{content}\n\n[Read full article at source]({art['url']})"
                else:
                    content = f"{content}\n\n[Read full article at source]({art['url']})"
                
                published_at = art['publishedAt'][:10] # Get YYYY-MM-DD
                
                if add_news_item(title, desc, content, date=published_at):
                    added_count += 1
            
            print(f"Successfully added {added_count} new news items.")
        else:
            print(f"Error from NewsAPI: {data.get('message')}")
    except Exception as e:
        print(f"Failed to fetch news: {e}")

if __name__ == "__main__":
    print(f"News Agent started at {datetime.now()}")
    fetch_tech_news()
