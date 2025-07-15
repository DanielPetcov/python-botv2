
# Automation of opening binance positions

This is a bot written in python, that every second fetches data from *upbit api (bottom one)* and looks for listing of new coins.

```http
  GET api.upbit.com/v1/market/all
```

When a new coin is listed, opens a long position, take profit and stop loss for that specific coin.

To use that bot, clone it, update the env variables with your keys, run it an wait.

Good luck!

## Environment Variables

To run this project, you will need to add the following environment variables to your .env file

`BINANCE_API_KEY`

`BINANCE_API_SECRET`
