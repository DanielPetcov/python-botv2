import aiohttp
async def recive_market():
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.upbit.com/v1/market/all") as response:
            data = await response.json()
            print(f"Received {len(data)} markets")