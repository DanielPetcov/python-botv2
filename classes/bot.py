import asyncio
import aiohttp
from decimal import Decimal, ROUND_DOWN
from binance import Client as BinanceClient, ThreadedWebsocketManager
from models.models import BotInitializer
from functions import recive_market

class Bot:
    def __init__(self, bot_info: BotInitializer):
        self.binance_api_key = bot_info.binance_api_key
        self.binance_api_secret = bot_info.binance_api_secret
        self.exchange_info = None
        self.market = []
        self.trade_done_event = asyncio.Event()

    async def fetch_exchange_info(self):
        while True:
            try:
                print("[INFO] Fetching Binance exchangeInfo...")
                async with aiohttp.ClientSession() as session:
                    async with session.get('https://fapi.binance.com/fapi/v1/exchangeInfo') as response:
                        if response.status == 200:
                            self.exchange_info = await response.json()
                            print("[INFO] exchangeInfo updated.")
                        else:
                            print(f"[ERROR] Failed to fetch exchangeInfo: {response.status}")
            except Exception as e:
                print(f"[EXCEPTION] Fetching exchangeInfo: {e}")
            await asyncio.sleep(3600)  # every hour

    async def start(self):
        print("Bot started...")
        asyncio.create_task(self.fetch_exchange_info())

        previous_market = []
        while True:
            try:
                current_market = await recive_market()
                new_tokens = [m for m in current_market if m not in previous_market and m.endswith("-USDT")]
                previous_market = current_market

                for token in new_tokens:
                    print(f"[NEW TOKEN] Detected listing: {token}")
                    await self.trade_on_binance(token.replace("-USDT", ""))

                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[ERROR] Market fetch failed: {e}")
                await asyncio.sleep(3)

    def round_step(self, value, step):
        return float(Decimal(str(value)).quantize(Decimal(str(step)), rounding=ROUND_DOWN))

    async def trade_on_binance(self, coin):
        my_symbol = f"{coin.upper()}USDT"
        invest_percent = 60
        leverage = 20

        client = BinanceClient(self.binance_api_key, self.binance_api_secret)

        try:
            client.futures_change_leverage(symbol=my_symbol, leverage=leverage)
            symbol_price = float(client.get_symbol_ticker(symbol=my_symbol)['price'])
        except Exception as e:
            print(f"[ERROR] Price/leverage fetch failed: {e}")
            return

        if not self.exchange_info:
            print("[WARN] exchangeInfo not loaded yet.")
            return

        quantity_precision = 0
        tick_precision = "0.01"

        for symbol in self.exchange_info['symbols']:
            if symbol['symbol'] == my_symbol:
                quantity_precision = symbol['quantityPrecision']
                tick_precision = symbol['filters'][0]['tickSize']
                break

        balance = next((float(a['balance']) for a in client.futures_account_balance() if a['asset'] == 'USDT'), 0)
        if balance == 0:
            print("[ERROR] USDT balance is 0.")
            return

        invest_amount = (invest_percent * balance) / 100
        quantity = invest_amount / symbol_price
        rounded_quantity = round(quantity, quantity_precision)

        tp_pct = 100
        sl_pct = 70

        position_size = invest_amount * leverage
        delta_tp = (invest_amount * tp_pct / 100) / (position_size / symbol_price)
        delta_sl = (invest_amount * sl_pct / 100) / (position_size / symbol_price)

        tp_price = self.round_step(symbol_price + delta_tp, tick_precision)
        sl_price = self.round_step(symbol_price - delta_sl, tick_precision)

        print(f"[TRADE] {my_symbol} | Qty: {rounded_quantity} | Entry: {symbol_price:.4f} | TP: {tp_price} | SL: {sl_price}")

        try:
            client.futures_create_order(symbol=my_symbol, side='BUY', type='MARKET', quantity=str(rounded_quantity))
            tp_order = client.futures_create_order(
                symbol=my_symbol, side="SELL", type="TAKE_PROFIT_MARKET",
                quantity=str(rounded_quantity), stopPrice=str(tp_price)
            )
            sl_order = client.futures_create_order(
                symbol=my_symbol, side="SELL", type="STOP_MARKET",
                quantity=str(rounded_quantity), stopPrice=str(sl_price)
            )

            active_order_ids = {"tp": tp_order['orderId'], "sl": sl_order['orderId']}

            twm = ThreadedWebsocketManager(api_key=self.binance_api_key, api_secret=self.binance_api_secret)
            twm.start()

            def handle_socket_msg(msg):
                if msg['e'] == 'ORDER_TRADE_UPDATE':
                    order = msg['o']
                    order_id = order['i']
                    status = order['X']

                    if order_id in active_order_ids.values() and status == 'FILLED':
                        print(f"[FILLED] Order: {order_id}")
                        for label, oid in active_order_ids.items():
                            if oid != order_id:
                                try:
                                    client.futures_cancel_order(symbol=my_symbol, orderId=oid)
                                    print(f"[CANCELLED] {label} order {oid}")
                                except Exception as e:
                                    print(f"[ERROR] Cancel {label} order: {e}")
                        twm.stop()
                        asyncio.get_event_loop().call_soon_threadsafe(self.trade_done_event.set)

            twm.start_futures_user_socket(callback=handle_socket_msg)

            await self.trade_done_event.wait()
            self.trade_done_event.clear()

        except Exception as e:
            print(f"[ERROR] Trade failed: {e}")
