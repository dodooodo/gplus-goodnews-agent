from app.models import GoogleNewsResponse
from fastapi import HTTPException
import httpx
from bs4 import BeautifulSoup
from urllib.parse import unquote
from fake_headers import Headers
from datetime import datetime
from typing import AsyncGenerator, Optional
import asyncio
import random



class SearchResult:
    def __init__(self, url: str, title: str, description: str):
        self.url = url
        self.title = title
        self.description = description

    def __repr__(self):
        return f"SearchResult(url={self.url}, title={self.title}, description={self.description})"

def tbs_format(month: Optional[int]) -> Optional[str]:
    if month is None:
        return month
    
    if month in [1, 3, 5, 7, 8, 10, 12]:
        day = 31
    elif month in [2, 4, 6, 9, 11]:
        day = 30
    else:
        raise ValueError(f"Month Error: {month}")
        
    year = datetime.now().year
    return f"cdr:1,cd_min:{month}/01/{year},cd_max:{month}/{day}/{year},sbd:1"


async def get_useragent():
    """
    Generates a random user agent string mimicking the format of various software versions.

    The user agent string is composed of:
    - Lynx version: Lynx/x.y.z where x is 2-3, y is 8-9, and z is 0-2
    - libwww version: libwww-FM/x.y where x is 2-3 and y is 13-15
    - SSL-MM version: SSL-MM/x.y where x is 1-2 and y is 3-5
    - OpenSSL version: OpenSSL/x.y.z where x is 1-3, y is 0-4, and z is 0-9

    Returns:
        str: A randomly generated user agent string.
    """
    lynx_version = f"Lynx/{random.randint(2, 3)}.{random.randint(8, 9)}.{random.randint(0, 2)}"
    libwww_version = f"libwww-FM/{random.randint(2, 3)}.{random.randint(13, 15)}"
    ssl_mm_version = f"SSL-MM/{random.randint(1, 2)}.{random.randint(3, 5)}"
    openssl_version = f"OpenSSL/{random.randint(1, 3)}.{random.randint(0, 4)}.{random.randint(0, 9)}"
    return f"{lynx_version} {libwww_version} {ssl_mm_version} {openssl_version}"


async def search(
    term: str,
    num_results: int = 10,
    lang: Optional[str] = None,
    proxy: Optional[str] = None,
    advanced: bool = False,
    sleep_interval: float = 0,
    timeout: int = 5,
    safe: str = "active",
    region: Optional[str] = None,
    start_num: int = 0,
    unique: bool = False,
    month: Optional[int] = None
) -> AsyncGenerator[SearchResult | str, None]:
    """Async version of Google search"""
    
    proxies = {"https": proxy, "http": proxy} if proxy and (proxy.startswith("https") or proxy.startswith("http")) else None
    start = start_num
    fetched_results = 0
    fetched_links = set()

    async with httpx.AsyncClient(proxy=proxies, timeout=timeout) as client:
        while fetched_results < num_results:
            try:
                print({
                        "tbm": "nws",
                        "q": term,
                        "num": num_results + 2,
                        "hl": lang,
                        "start": start,
                        "safe": safe,
                        "gl": region,
                        "tbs": tbs_format(month),
                    })
                resp = await client.get(
                    "https://www.google.com/search",
                    headers={
                            "User-Agent": await get_useragent(),
                            "Accept": "*/*"
                    },
                    params={
                        "tbm": "nws",
                        "q": term,
                        "num": num_results + 2,
                        "hl": lang,
                        "start": start,
                        "safe": safe,
                        "gl": region,
                        "tbs": tbs_format(month),
                    },
                    cookies={
                        'CONSENT': 'PENDING+987',
                        'SOCS': 'CAESHAgBEhIaAB',
                    }
                )
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")
                # print(soup)
                result_block = soup.find_all("div", class_="ezO2md")
                new_results = 0
                # print('result_block:', result_block)
                for result in result_block:
                    print('fetched_links:', fetched_links)
                    link_tag = result.find("a", href=True)
                    title_tag = link_tag.find("span", class_="CVA68e") if link_tag else None
                    description_tag = result.find("span", class_="FrIlee")

                    if link_tag and title_tag and description_tag:
                        link = unquote(link_tag["href"].split("&")[0].replace("/url?q=", ""))
                        
                        if link in fetched_links and unique:
                            continue
                            
                        fetched_links.add(link)
                        title = title_tag.text if title_tag else ""
                        description = description_tag.text if description_tag else ""
                        
                        fetched_results += 1
                        new_results += 1
                        
                        if advanced:
                            # print('link:', link)
                            yield SearchResult(link, title, description)
                        else:
                            yield link

                        if fetched_results >= num_results:
                            break

                if new_results == 0:
                    break

                start += 10
                await asyncio.sleep(sleep_interval)

            except Exception as e:
                print(f"Error during search: {e}")
                break 


async def scrape_search_results(req: GoogleNewsResponse):
    try:
        results = []
        async for result in search(
            term=req.query,
            num_results=req.num_results,
            month=req.month,
            lang=req.language,
            advanced=True
        ):
            results.append(GoogleNewsResponse(
                url=result.url,
                title=result.title,
                description=result.description
            ))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def scrape_news_content(url: str, timeout: int = 10) -> str:
    """
    Scrapes news content from a given URL with intelligent site-specific handling.
    
    Args:
        url (str): The URL of the news article to scrape
        timeout (int): Timeout in seconds for the HTTP request
        
    Returns:
        str: The extracted news content text
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            # headers = {
            #     "User-Agent": await get_useragent(),
            #     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            #     "Accept-Language": "en-US,en;q=0.5",
            # }
            
            resp = await client.get(url, headers=Headers().generate())
            resp.raise_for_status()
            
            # If we got redirected, get the final URL
            final_url = str(resp.url)
            if final_url != url:
                print(f"Redirected from {url} to {final_url}")

            # print(final_url)
            
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Remove unwanted elements
            for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            # Common article content selectors
            content_selectors = [
                'article',  # Common article container
                '.article-content',  # Generic article content
                '.post-content',  # Blog posts
                '.entry-content',  # WordPress
                '.story-body',  # News sites
                '#article-body',  # ID-based selectors
                '.article-body',
                '.article__body',
                '.article-text',
                '.article-content',
                'main',  # Main content area
                '.content',  # Generic content
            ]
            
            # Try each selector until we find content
            content = None
            for selector in content_selectors:
                content = soup.select_one(selector)
                if content:
                    break
            
            # If no specific content found, try to get the main text
            if not content:
                content = soup.find('body')
            
            if content:
                # Get all paragraphs
                paragraphs = content.find_all('p')
                # Filter out short paragraphs (likely navigation or ads)
                text = '\n'.join(p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50)
                # print('Text:', text, '-'*100)
                return text
            print("Could not extract content from the page", '\n', '-'*100)
            return "Could not extract content from the page"
            
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 302:
            redirect_url = e.response.headers.get('location')
            if redirect_url:
                print(f"Handling 302 redirect to: {redirect_url}")
                return await scrape_news_content(redirect_url, timeout)
        print(f"HTTP error scraping {url}: {e}")
        return f"HTTP error: {str(e)}"
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return f"Error scraping content: {str(e)}"