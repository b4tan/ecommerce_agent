from typing import Optional
from pydantic import BaseModel, HttpUrl

class ProductCard(BaseModel):
    asin: str
    title: str
    final_price: Optional[float] = None
    currency: Optional[str] = None
    rating: Optional[float] = None
    image_url: Optional[HttpUrl] = None
    url: Optional[HttpUrl] = None
