import requests
from bs4 import BeautifulSoup
import json
import os
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("demo_fetch")

OSRS_NEWS_URL = "https://secure.runescape.com/m=news/archive?oldschool=1"

def fetch_osrs_news():
    """
    Fetches the latest OSRS news headlines using requests/bs4.
    Simulates the MCP 'fetch' capability for documentation/news scraping.
    """
    logger.info(f"Fetching OSRS News from: {OSRS_NEWS_URL}")
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(OSRS_NEWS_URL, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # OSRS News Archive structure (approximate)
        news_items = []
        articles = soup.find_all('article', class_='news-article')
        
        if not articles:
             # Fallback for different DOM structure
             logger.warning("Standard article tags not found. Attempting fallback parse.")
             links = soup.find_all('a', class_='news-list-article__title-link')
             for link in links[:5]:
                 title = link.get_text(strip=True)
                 url = link['href']
                 news_items.append({"title": title, "url": url})
        else:
            for article in articles[:5]:
                title_tag = article.find('h3', class_='news-article__title')
                date_tag = article.find('time', class_='news-article__time')
                link_tag = article.find('a', class_='news-article__figure-link')
                
                if title_tag:
                    title = title_tag.get_text(strip=True)
                    date = date_tag.get_text(strip=True) if date_tag else "Unknown"
                    link = link_tag['href'] if link_tag else "#"
                    news_items.append({
                        "title": title,
                        "date": date,
                        "url": link
                    })

        return news_items

    except Exception as e:
        logger.error(f"Fetch Error: {e}")
        return []

def main():
    logger.info("--- Starting Fetch Demo ---")
    news = fetch_osrs_news()
    
    if news:
        logger.info(f"Successfully fetched {len(news)} articles:")
        print(json.dumps(news, indent=2))
        
        # Save to file
        with open("data/osrs_news.json", "w") as f:
            json.dump(news, f, indent=2)
        logger.info("Saved to data/osrs_news.json")
    else:
        logger.warning("No news found.")

if __name__ == "__main__":
    main()
