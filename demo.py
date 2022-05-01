import MuslimProAPI
import asyncio
from loguru import logger

client = MuslimProAPI.Search

async def asd():
    data = await client.search("tokyo")
    logger.info(data.raw)
    
loop = asyncio.get_event_loop()
loop.run_until_complete(asd())
loop.close()