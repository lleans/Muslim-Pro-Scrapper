import asyncio

from MuslimProScrapper import Search
from MuslimProScrapper.const import AsrjuristicMethod, CalculationMethod

# Custom calculationMethod and asrjuristicMethod 
# client = MuslimProAPI.Search(calculation=CalculationMethod.SIHAT_KEMENAG_KEMENTERIAN_AGAMA_RI, asrjuristic=AsrjuristicMethod.STANDARD_SHAFI_MALIKI_HANBALI)

# Default just let it blank
client = Search()

async def asd():
    location = "Tokyo"
    data = await client.search(location)
    print(f"Showing prayertime for {location}")
    print("-" * 50)
    print(data.origin)
    print(data.raw)
    print(data.calculationMethod)
    print(data.asrjuristicMethod)
    print(data.raw[0].date)
    print(data.raw[0].prayertimes)
    print("-" * 50)
    
loop = asyncio.get_event_loop()
loop.run_until_complete(asd())