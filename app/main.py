# app/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.linkedin_scraper import scrape_linkedin_posts
from app.openai_analyzer import analyze_posts
# from app.gemini_analyzer import analyze_posts
from app.utils import parse_linkedin_url, parse_str_to_dict
from app.googlesearch_async import search, scrape_news_content
from typing import List, Optional
import asyncio

app = FastAPI()


class LIRequest(BaseModel):
    linkedin_url: str
    month: int  # 1 - 12
    language: str # ch, en


class GoogleNewsRequest(BaseModel):
    query: str
    num_results: int = 10
    month: Optional[int] = None
    language: str
    gs_language: Optional[str] = None


class CombinedRequest(BaseModel):
    linkedin_url: str
    google_query: str
    month: int  # 1 - 12
    language: str  # ch, en
    num_google_results: int = 10
    gs_language: Optional[str] = None


class ResponseModel(BaseModel):
    crawled_text: str
    headline: str
    contents: str
    headline_zh_tw: str
    contents_zh_tw: str
    category: str
    url: str
    img_links: List[str] | None = None



async def post_process_results(results: list[ResponseModel]) -> list[ResponseModel]:
    priority = {
        'Fund-raised': 0,
        'Business Collaboration': 1,
        'Product-launched': 2,
        'Awards': 3,
        'Activities': 4,
        'None': 5
    }
    results.sort(key=lambda d: priority[d.category])
    return results


@app.post("/scrape", response_model=List[ResponseModel])
async def linkedin_request(req: LIRequest):
    try:
        # Step 0: parse linkedin URL
        linkedin_url = parse_linkedin_url(req.linkedin_url)

        # Step 1: Scrape LinkedIn posts
        post_data_list = await scrape_linkedin_posts(req.linkedin_url, req.month)

        # Step 2: Analyze with OpenAI
        tasks = []
        for post in post_data_list:
            tasks.append(analyze_posts(post.text, req.language))
        
        gpt_responses = await asyncio.gather(*tasks)
        
        results = []
        for post, gpt_response in zip(post_data_list, gpt_responses):
            parsed = parse_str_to_dict(gpt_response)
            results.append(ResponseModel(
                crawled_text=post.text,
                headline=parsed.get("Headline", ""),
                contents=parsed.get("Content", ""),
                headline_zh_tw=parsed.get("Headline-zh-tw", ""),
                contents_zh_tw=parsed.get("Content-zh-tw", ""),
                category=parsed.get("Category", ""),
                url=post.url,
                img_links=post.img_links,
            ))
        
        results = await post_process_results(results)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search-news", response_model=List[ResponseModel])
async def google_search_news_request(req: GoogleNewsRequest):
    try:
        # step 1: google search
        search_result_list = []
        tasks = []
        async for result in search(
            term=req.query,
            num_results=req.num_results,
            month=req.month,
            lang=req.gs_language,
            advanced=True
        ):
            # print('result', result)
            # step 1.5: keep search results
            search_result_list.append(result)

            # step 2: get news contents
            tasks.append(asyncio.create_task(scrape_news_content(result.url)))
        news_content_list = await asyncio.gather(*tasks)

        # step 3: Analyze with OpenAI
        tasks = []
        for text in news_content_list:
            tasks.append(analyze_posts(text, req.language))
        gpt_responses = await asyncio.gather(*tasks)
        
        results = []
        for search_result, crawled_text, gpt_response in zip(search_result_list, news_content_list, gpt_responses):
            parsed = parse_str_to_dict(gpt_response)
            results.append(ResponseModel(
                crawled_text=crawled_text,
                headline=parsed.get("Headline", ""),
                contents=parsed.get("Content", ""),
                headline_zh_tw=parsed.get("Headline-zh-tw", ""),
                contents_zh_tw=parsed.get("Content-zh-tw", ""),
                category=parsed.get("Category", ""),
                url=search_result.url,
                # img_links=post.img_links,
            ))

        results = await post_process_results(results)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/combined-search", response_model=List[ResponseModel])
async def combined_search(req: CombinedRequest):
    try:
        print(req)
        # Run both scrapers concurrently
        tasks = []
        if req.linkedin_url:
            tasks.append(linkedin_request(LIRequest(linkedin_url=req.linkedin_url, month=req.month, language=req.language)))

        if req.google_query:
            tasks.append(google_search_news_request(GoogleNewsRequest(query=req.google_query, num_results=req.num_google_results, month=req.month, language=req.language, gs_language=req.gs_language)))

        # Wait for both tasks to complete
        results = await asyncio.gather(*tasks)

        # 解包結果
        linkedin_results = results[0] if req.linkedin_url else []
        google_results = results[1] if req.google_query and req.linkedin_url else results[0] if req.google_query else []
        
        # Combine and sort results
        combined_results = linkedin_results + google_results
        combined_results = await post_process_results(combined_results)
        
        return combined_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
