from pydantic import BaseModel, Field
from typing import Optional, List

class Article(BaseModel):
    title: str = Field(..., description="The title of the article")
    articleUrl: Optional[str] = Field(None, description="The url of the article")
    imageUrl: Optional[str] = Field(None, description="The url of the article's image")
    excerpt: Optional[str] = Field(None, description="A short excerpt from the article")
    
class ArticleList(BaseModel):
    articles: List[Article] = Field(..., description="A list of articles")  