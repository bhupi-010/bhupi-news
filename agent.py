import json
import os
import hashlib
import logging
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from bs4 import BeautifulSoup

# Optional AI summary
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

load_dotenv()

# ==============================
# CONFIGURATION
# ==============================
NEWS_DIR = "news"
INDEX_FILE = "news-index.json"

API_KEY = os.getenv("NEWS_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ENABLE_AI = os.getenv("ENABLE_AI_SUMMARY", "false").lower() == "true"

# Maximum number of articles to add to the system per run
MAX_ARTICLES_PER_RUN = 3

# ==============================
# LOGGING SETUP
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ==============================
# UTILITIES
# ==============================

def ensure_dirs():
    os.makedirs(NEWS_DIR, exist_ok=True)

def load_index():
    if os.path.exists(INDEX_FILE):
        try:
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

def save_index(index):
    # Sort by full date timestamp descending to ensure the newest is on top
    index.sort(key=lambda x: x["date"], reverse=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()

def clean_html(text):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text()

def generate_slug(title):
    return "".join(
        c for c in title.lower() if c.isalnum() or c == " "
    ).strip().replace(" ", "-")[:80]

# ==============================
# AI SUMMARY (Optional)
# ==============================

def generate_ai_summary(content):
    if not ENABLE_AI or not OPENAI_API_KEY or not OpenAI:
        return content
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a developer-focused tech blog writer. "
                        "Summarize this news article in 2-3 paragraphs. "
                        "Highlight usefulness for developers, AI enthusiasts, and web engineers."
                    ),
                },
                {"role": "user", "content": content[:4000]},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.warning(f"AI summary failed: {e}")
        return content

# ==============================
# ADD NEWS ITEM
# ==============================

def add_news_item(title, description, content, source_url, date=None, category="Tech", tags=None):
    """Add a news article to the repository."""
    ensure_dirs()

    if not date:
        date = datetime.now().isoformat()

    url_hash = hash_url(source_url)
    index = load_index()

    # Deduplicate by URL hash
    if any(item.get("id") == url_hash for item in index):
        return False

    slug = generate_slug(title)

    # Slug collision fallback
    if any(item.get("slug") == slug for item in index):
        slug = f"{slug}-{url_hash[:6]}"

    # Clean HTML & optionally summarise
    content = clean_html(content)
    content = generate_ai_summary(content)

    filepath = os.path.join(NEWS_DIR, f"{slug}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("---\n")
        f.write(f'title: "{title}"\n')
        f.write(f'date: "{date}"\n')
        f.write(f'description: "{description}"\n')
        f.write(f'category: "{category}"\n')
        f.write(f'source: "{source_url}"\n')
        if tags:
            f.write(f"tags: {tags}\n")
        f.write("---\n\n")
        f.write(content + "\n")

    item = {
        "id": url_hash,
        "title": title,
        "slug": slug,
        "date": date,
        "description": description,
        "category": category,
        "source": source_url,
        "tags": tags or [],
    }
    index.append(item)
    save_index(index)
    logging.info(f"  ✔ Added [{category}]: {title[:70]}")
    return True

# ==============================
# FETCH FROM APIS
# ==============================

def fetch_top_ai_news_newsapi():
    """Fetch highly relevant developer & AI news using NewsAPI /v2/everything"""
    if not API_KEY:
        return []
    
    # We target one solid combined query covering free AI tools, AI IDEs, and React
    query = '("free AI IDE" OR "Cursor IDE" OR "Windsurf IDE" OR "React" OR "Next.js" OR "frontend developer" OR "coding tool") AND ("new" OR "release" OR "update" OR "free")'
    from_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT00:00:00")
    
    url = (
        "https://newsapi.org/v2/everything"
        f"?q={requests.utils.quote(query)}"
        "&language=en"
        "&sortBy=publishedAt"
        "&pageSize=15" # Fetch slightly more and take the very best un-added ones
        f"&from={from_date}"
        f"&apiKey={API_KEY}"
    )
    
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        if data.get("status") == "ok":
            return data.get("articles", [])
        return []
    except Exception as e:
        logging.error(f"NewsAPI fetch failed: {e}")
        return []

def fetch_top_ai_news_gnews():
    """Fetch highly relevant developer news using GNews"""
    if not GNEWS_API_KEY:
        return []

    query = '"free AI IDE" OR "React Next.js" OR "coding tools"'
    from_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%dT00:00:00")
    
    url = (
        "https://gnews.io/api/v4/search"
        f"?q={requests.utils.quote(query)}"
        "&lang=en"
        "&sortBy=publishedAt"
        "&max=10"
        f"&from={from_date}"
        f"&apikey={GNEWS_API_KEY}"
    )
    
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        return data.get("articles", [])
    except Exception as e:
        logging.error(f"GNews fetch failed: {e}")
        return []

# ==============================
# MAIN AGENT
# ==============================

def run_news_agent():
    logging.info("=" * 55)
    logging.info("  Targeted Dev & AI News Aggregator — Starting")
    logging.info("=" * 55)

    all_raw_articles = []
    
    if API_KEY:
        all_raw_articles.extend(fetch_top_ai_news_newsapi())
    if GNEWS_API_KEY:
        all_raw_articles.extend(fetch_top_ai_news_gnews())
        
    # Sort ALL articles by published time descending (newest first)
    # Ensure they have publishedAt before sorting
    for art in all_raw_articles:
        if "publishedAt" not in art:
            art["publishedAt"] = datetime.now().isoformat()
            
    all_raw_articles.sort(key=lambda x: x["publishedAt"], reverse=True)

    added = 0
    for art in all_raw_articles:
        if added >= MAX_ARTICLES_PER_RUN:
            break
            
        title = art.get("title") or ""
        description = art.get("description") or ""
        source_url = art.get("url") or ""

        if not title or not description or not source_url:
            continue
        if "[Removed]" in title or "[Removed]" in description:
            continue

        content = art.get("content") or description

        # Prepend image if available
        img = art.get("urlToImage") or art.get("image")
        if img:
            content = f"![Featured Image]({img})\n\n{content}"

        content += f"\n\n[Read original article]({source_url})"

        # We keep the full datetime so the frontend can sort newly generated ones on top
        date = art.get("publishedAt") 
        
        # Determine strict category based on keywords
        cat = "Dev News"
        lower_title = title.lower() + description.lower()
        if "ai" in lower_title or "artificial intelligence" in lower_title:
            cat = "AI Tools"
        if "react" in lower_title or "next.js" in lower_title or "javascript" in lower_title:
            cat = "Frontend"

        # Auto-tags: source domain + category slug
        tags = []
        try:
            domain = source_url.split("//")[1].split("/")[0].replace("www.", "")
            tags.append(domain)
        except Exception:
            pass
        tags.append(cat.replace(" ", "-").lower())

        if add_news_item(title, description, content, source_url, date=date, category=cat, tags=tags):
            added += 1

    logging.info("=" * 55)
    logging.info(f"  DONE — Total new top articles added: {added}")
    logging.info("=" * 55)

# ==============================
# SYNC INDEX
# ==============================

def sync_index():
    index = load_index()
    ensure_dirs()

    clean_index = []
    removed = 0
    for item in index:
        slug = item.get("slug")
        if slug and os.path.exists(os.path.join(NEWS_DIR, f"{slug}.md")):
            clean_index.append(item)
        else:
            removed += 1

    if removed > 0:
        save_index(clean_index)
        logging.info(f"Synced index — removed {removed} orphaned entries.")
    else:
        logging.info("Index is clean and in sync.")

if __name__ == "__main__":
    logging.info(f"News Agent started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    run_news_agent()
    sync_index()
