import os
import asyncio
from classes.bot import Bot
from models.models import BotInitializer
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

async def main():
    bot_initializer = BotInitializer(
        binance_api_key=os.getenv('BINANCE_API_KEY'),
        binance_api_secret=os.getenv('BINANCE_API_SECRET'),
    )
    bot_itself = Bot(bot_initializer)
    await bot_itself.start() 

if __name__ == "__main__":
    asyncio.run(main())