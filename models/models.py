from pydantic import BaseModel

class BotInitializer(BaseModel):
    binance_api_key: str
    binance_api_secret: str