from pydantic import BaseModel
from typing import List


class PostData(BaseModel):
    url: str
    text: str
    img_links: List[str] | None = None


class AnalysisRequest(BaseModel):
    url: str
    month: int
    language: str = "ch"  # "ch" or "en"


class PostAnalysis(BaseModel):
    href: str
    Headline: str
    Contents: str
    Good_News_Category: str


class AnalysisResponse(BaseModel):
    results: List[PostAnalysis]


class GoogleNewsResponse(BaseModel):
    url: str
    title: str
    description: str