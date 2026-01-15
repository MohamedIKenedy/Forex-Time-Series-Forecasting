import redis
from config import settings
import asyncio
from typing import Dict, Any
from services.conn_management import manager

class CacheService:
    def __init__(self):
        self.redis = redis.from_url(settings.redis_url)
    
    async def get(self, key: str):
        return self.redis.get(key)
    
    async def set(self, key: str, value, expire: int = 300):
        self.redis.setex(key, expire, value)
    
    async def get_latest_price(self, ticker: str):
        return await self.get(f"latest:{ticker}")
    
    async def set_latest_price(self, ticker: str, data):
        await self.set(f"latest:{ticker}", data, expire=60) 

    
    async def cache_message(ticker: str, message: Dict[str, Any]):
        """Callback to cache messages and broadcast via WebSocket"""
        global latest_data_cache
        latest_data_cache[ticker] = message
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(manager.broadcast({
                "type": "price_update",
                "ticker": ticker,
                "data": message
            }))
            loop.close()
        except:
            pass