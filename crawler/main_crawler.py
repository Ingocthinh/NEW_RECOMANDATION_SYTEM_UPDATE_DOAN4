import feedparser
import requests
from bs4 import BeautifulSoup
from newspaper import Article
import sqlite3
import datetime
import time
import os
import re
import sys

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

RSS_FEEDS = {
    "CÔNG NGHỆ": "https://vnexpress.net/rss/so-hoa.rss",
    "KINH TẾ": "https://vnexpress.net/rss/kinh-doanh.rss",
    "THỂ THAO": "https://vnexpress.net/rss/the-thao.rss",
    "SỨC KHỎE": "https://vnexpress.net/rss/suc-khoe.rss",
    "GIẢI TRÍ": "https://vnexpress.net/rss/giai-tri.rss",
    "GIÁO DỤC": "https://vnexpress.net/rss/giao-duc.rss",
    "DU LỊCH": "https://vnexpress.net/rss/du-lich.rss",
    "PHÁP LUẬT": "https://vnexpress.net/rss/phap-luat.rss"
}

# VnExpress category page URLs for deep crawling
CATEGORY_PAGES = {
    "CÔNG NGHỆ": "https://vnexpress.net/so-hoa",
    "KINH TẾ": "https://vnexpress.net/kinh-doanh",
    "THỂ THAO": "https://vnexpress.net/the-thao",
    "SỨC KHỎE": "https://vnexpress.net/suc-khoe",
    "GIẢI TRÍ": "https://vnexpress.net/giai-tri",
    "GIÁO DỤC": "https://vnexpress.net/giao-duc",
    "DU LỊCH": "https://vnexpress.net/du-lich",
    "PHÁP LUẬT": "https://vnexpress.net/phap-luat"
}

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "news.db")
TARGET = 5000
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS News (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            image_url TEXT,
            category TEXT NOT NULL,
            source TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            published_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def get_count():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM News")
    count = cur.fetchone()[0]
    conn.close()
    return count

def is_url_exists(url):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM News WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def crawl_article(url, category):
    if is_url_exists(url):
        return False
    try:
        article = Article(url, language='vi')
        article.download()
        article.parse()

        title = article.title
        content = article.text
        summary = article.summary or article.meta_description
        image_url = article.top_image
        published_at = article.publish_date or datetime.datetime.now()
        source = "VnExpress"

        if not content or len(content) < 50:
            response = requests.get(url, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            content_div = soup.find('article', class_='fck_detail') or soup.find('div', class_='content-detail')
            if content_div:
                content = content_div.get_text(separator='\n').strip()
            else:
                return False

        if not title or len(content) < 50:
            return False

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO News (title, content, summary, image_url, category, source, url, published_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, content, summary, image_url, category, source, url,
              published_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(published_at, 'strftime') else str(published_at)))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False

def get_article_urls_from_page(page_url):
    """Scrape article URLs from a VnExpress category page."""
    urls = []
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.content, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('https://vnexpress.net/') and href.endswith('.html'):
                if href not in urls:
                    urls.append(href)
    except Exception as e:
        print(f"  Error fetching page: {e}")
    return urls

def run_crawler():
    print("=" * 60)
    print(f"  MASS CRAWLER - Target: {TARGET} articles")
    print("=" * 60)
    init_db()

    # Phase 1: RSS Feeds
    print("\n[PHASE 1] Crawling RSS feeds...")
    for category, rss_url in RSS_FEEDS.items():
        count = get_count()
        if count >= TARGET:
            break
        print(f"\n  Category: {category}")
        feed = feedparser.parse(rss_url)
        new = 0
        for entry in feed.entries:
            if crawl_article(entry.link, category):
                new += 1
            time.sleep(0.5)
        print(f"  -> {new} new articles | Total: {get_count()}")

    # Phase 2: Deep crawl category pages (paginated)
    print("\n[PHASE 2] Deep crawling category pages...")
    for category, base_url in CATEGORY_PAGES.items():
        count = get_count()
        if count >= TARGET:
            print(f"\n  Target {TARGET} reached! Stopping.")
            break

        print(f"\n  Deep crawling: {category}")
        total_new = 0

        # Crawl multiple pages (p1 to p80)
        for page in range(1, 81):
            current = get_count()
            if current >= TARGET:
                break

            page_url = f"{base_url}-p{page}" if page > 1 else base_url
            urls = get_article_urls_from_page(page_url)

            if not urls:
                print(f"    Page {page}: no articles found, moving on")
                break

            page_new = 0
            for url in urls:
                if crawl_article(url, category):
                    page_new += 1
                    total_new += 1
                time.sleep(0.3)

            print(f"    Page {page}: +{page_new} | Total: {get_count()}")

            if page_new == 0 and page > 3:
                break  # No new articles, stop this category

        print(f"  -> {category}: {total_new} new articles")

    final = get_count()
    print("\n" + "=" * 60)
    print(f"  CRAWLING COMPLETE! Total articles: {final}")
    print("=" * 60)

if __name__ == "__main__":
    run_crawler()
