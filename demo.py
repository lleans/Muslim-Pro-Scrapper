import MuslimProAPI
import asyncio

client = MuslimProAPI.Search()

async def asd():
    location = "Tokyo"
    data = await client.search(location)
    print("Showing prayertime for "+location)
    print("-" * 50)
    print(data.origin)
    print(data.raw)
    for i in range(6): #Prayers of moslem time
        print(data.raw[i])
    print("-" * 50)
    
loop = asyncio.get_event_loop()
loop.run_until_complete(asd())