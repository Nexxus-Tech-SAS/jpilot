import httpx

from app.config import settings

NEXXUS_BLOG_PATH = "/api/blog"
MAX_ARTICLES = 4


async def fetch_nexxus_blog_articles() -> list[dict]:
    url = f"{settings.nexxus_licensing_base_url.rstrip('/')}{NEXXUS_BLOG_PATH}"
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, list) or not data:
        raise ValueError("Nexxus blog API returned no articles")
    return data[:MAX_ARTICLES]
