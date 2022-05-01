import MuslimProAPI
import asyncio
from loguru import logger

client = MuslimProAPI.Search()

async def asd():
    location = "Tokyo"
    data = await client.search(location)
    logger.info("Showing prayertime for "+location)
    logger.info("-" * 50)
    logger.info(data.origin)
    logger.info(data.raw)
    for i in range(6): #Prayers of moslem time
        logger.info(data.raw[i])
    logger.info("-" * 50)
    
loop = asyncio.get_event_loop()
loop.run_until_complete(asd())
loop.close()