from app.models import PostData
import googlenews_scraper


async def scrape_linkedin_posts(url: str, month: int, headless: bool = True) -> list[PostData]: