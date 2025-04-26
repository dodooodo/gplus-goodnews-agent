from playwright.async_api import async_playwright
from datetime import datetime
from app.models import PostData
from app.utils import get_date_from_url


async def scrape_linkedin_posts(url: str, month: int, headless: bool = True) -> list[PostData]:
    post_data_list = []

    async with async_playwright() as p:
        # print('async with async_playwright() as p:')

        browser = await p.chromium.launch(headless=headless)
        page = await browser.new_page()
        await page.goto(url)
        #  ('await page.goto(url)')

        loop_limit = 0
        while True:
            loop_limit += 1
            if loop_limit > 50:
                break

            posts = await page.query_selector_all('div[data-id="entire-feed-card-link"]')
            # print(f"posts = {posts}")
            if not posts:
                break

            last_post = posts[-1]
            post_url = await get_post_url(last_post)
            utc_date = get_date_from_url(post_url)

            if not check_time_in_month(utc_date, month):
                break

            await last_post.scroll_into_view_if_needed()
            # print(len(posts), loop_limit)

        # 收集目標月份的貼文
        for post in posts:
            post_url = await get_post_url(post)
            utc_date = get_date_from_url(post_url)
            if check_time_in_month(utc_date, month):
                # get texts
                text = await post.inner_text()

                # get img urls
                img_eles = await post.query_selector_all("img")
                img_links = []
                for img in img_eles:
                    src = await img.get_attribute("src")
                    if src:
                        img_links.append(src)
                
                # organize results
                post_data_list.append(PostData(url=post_url, text=text, img_links=img_links))

        await browser.close()

    return post_data_list


def check_time_in_month(utc_date: str, month: int) -> bool:
    try:
        post_time = datetime.strptime(utc_date, '%a, %d %b %Y %H:%M:%S GMT')
        return month == post_time.month and post_time.year == datetime.now().year
    except Exception:
        return False


async def get_post_url(post) -> str:
    try:
        link = await post.query_selector('a[data-id="main-feed-card__full-link"]')
        return await link.get_attribute('href') if link else ""
    except Exception:
        return ""

