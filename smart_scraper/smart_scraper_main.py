from utils.browser_agent import WebScraperAgent
from utils.llm_extractor import process_with_llm
from schemas.article_schema import ArticleList
import asyncio
from IPython.display import Image as IPImage, display
import os
import json
import pandas
from tabulate import tabulate

async def webscraper(target_url, instructions):
    result = None
    screenshot_bytes = None
    scraper=WebScraperAgent()
    try:
        await scraper.init_browser()
        html_content = await scraper.scrape_content(target_url)
        
        if html_content:
            screenshot_bytes=await scraper.screenshot_buffer()
            result=await process_with_llm(
                html_content,
                instructions,
                source_url=target_url,
                truncate=True,
            )
    except Exception as e:
        print(f"Error in webscraper: {e}")
    finally:
        await scraper.close()   
        
    return result, screenshot_bytes  

 
