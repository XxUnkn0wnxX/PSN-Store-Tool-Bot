import aiohttp
import re
from urllib.parse import urlparse
from api import APIError

DECIMAL_RE = re.compile(r"\d+")

class PSPrices:
    def __init__(self, url: str) -> None:
        parsed = urlparse(url)
        match = DECIMAL_RE.search(parsed.path)

        if not match:
            raise APIError("Invalid URL!")

        self.game_id = match.group()

        segments = [segment for segment in parsed.path.split('/') if segment]
        region_segment = next((seg for seg in segments if seg.startswith('region-')), None)

        if region_segment:
            path = f"/{region_segment}/game/buy/{self.game_id}"
        else:
            path = f"/game/buy/{self.game_id}"

        scheme = parsed.scheme or "https"
        netloc = parsed.netloc or "psprices.com"
        self.url = f"{scheme}://{netloc}{path}"
    
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    async def obtain_skuid(self) -> str:
        async with aiohttp.ClientSession() as session:
            res = await session.get(self.url, allow_redirects=True, headers=self.HEADERS)

            # product_id = url.split("productId=")[1].split("&")[0]
            product_id = res.url.query.get("productId", "FAIL!")
            if product_id == "FAIL!":
                raise APIError("FAIL!")
            
            return product_id
