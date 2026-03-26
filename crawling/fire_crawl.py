from firecrawl import Firecrawl
from dotenv import load_dotenv
import os

load_dotenv()

fire_api= os.getenv("FIRE_CRAWL_API")
firecrawl = Firecrawl(api_key=fire_api)

results = firecrawl.search(
    query="firecrawl",
    limit=3,
)
print(results)