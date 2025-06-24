import aiohttp
import asyncio
from typing import Dict, List
import pandas as pd
from datetime import datetime, timedelta

class MarketDataService:
    """
    Handles real-time market data ingestion and preprocessing.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = None
        
        # S&P 500 tickers (top 50 for demo)
        self.tickers = [
            'AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'TSLA', 'GOOG', 'META',
            'UNH', 'XOM', 'LLY', 'JNJ', 'V', 'PG', 'JPM', 'MA', 'AVGO', 'HD',
            'CVX', 'MRK', 'ABBV', 'COST', 'PEP', 'KO', 'WMT', 'BAC', 'TMO',
            'CRM', 'ACN', 'MCD', 'CSCO', 'DHR', 'ABT', 'ADBE', 'TXN', 'NEE',
            'VZ', 'CMCSA', 'NFLX', 'RTX', 'NKE', 'QCOM', 'AMD', 'T', 'LOW',
            'AMGN', 'UPS', 'PM', 'HON', 'IBM'
        ]
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_intraday_data(self, symbol: str, interval: str = '5min') -> pd.DataFrame:
        """Fetch intraday price data for a symbol."""
        url = "https://www.alphavantage.co/query"
        params = {
            'function': 'TIME_SERIES_INTRADAY',
            'symbol': symbol,
            'interval': interval,
            'apikey': self.api_key,
            'outputsize': 'compact'
        }
        
        async with self.session.get(url, params=params) as response:
            data = await response.json()
            
            if 'Time Series (5min)' in data:
                ts_data = data['Time Series (5min)']
                df = pd.DataFrame.from_dict(ts_data, orient='index')
                df.index = pd.to_datetime(df.index)
                df = df.astype(float)
                df.columns = ['open', 'high', 'low', 'close', 'volume']
                return df.sort_index()
            
            return pd.DataFrame()
    
    async def get_latest_returns(self, lookback_days: int = 252) -> pd.DataFrame:
        """
        Fetch latest return data for entropy calculation.
        This is the main data pipeline feeding the entropy engine.
        """
        # Simulate concurrent API calls (in production, use proper rate limiting)
        tasks = []
        for symbol in self.tickers:
            task = asyncio.create_task(self.fetch_intraday_data(symbol))
            tasks.append(task)
            
            # Rate limiting - don't hammer the API
            if len(tasks) % 10 == 0:
                await asyncio.sleep(0.1)
        
        # Collect all price data
        price_data = {}
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for symbol, result in zip(self.tickers, results):
            if isinstance(result, pd.DataFrame) and not result.empty:
                price_data[symbol] = result['close']
        
        if not price_data:
            return pd.DataFrame()
        
        # Combine into single DataFrame
        prices_df = pd.DataFrame(price_data)
        prices_df = prices_df.dropna()
        
        # Calculate returns
        returns_df = prices_df.pct_change().dropna()
        
        # Return the most recent lookback_days
        if len(returns_df) > lookback_days:
            returns_df = returns_df.tail(lookback_days)
        
        return returns_df