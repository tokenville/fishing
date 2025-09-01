import requests
from datetime import datetime, timezone

# Mapping of base currencies to CoinGecko IDs
COINGECKO_IDS = {
    'ETH': 'ethereum',
    'BTC': 'bitcoin', 
    'SOL': 'solana',
    'ADA': 'cardano',
    'MATIC': 'matic-network',
    'AVAX': 'avalanche-2',
    'LINK': 'chainlink',
    'DOT': 'polkadot'
}

# Fallback prices for testing
FALLBACK_PRICES = {
    'ETH': 2500.0,
    'BTC': 45000.0,
    'SOL': 100.0,
    'ADA': 0.5,
    'MATIC': 1.2,
    'AVAX': 35.0,
    'LINK': 15.0,
    'DOT': 7.0
}

def get_crypto_price(base_currency):
    """Get current price for any supported cryptocurrency"""
    try:
        if base_currency not in COINGECKO_IDS:
            print(f"Unsupported currency: {base_currency}")
            raise ValueError(f"Unsupported currency: {base_currency}")
            
        coingecko_id = COINGECKO_IDS[base_currency]
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': coingecko_id,
            'vs_currencies': 'usd'
        }
        
        print(f"Fetching {base_currency} price from CoinGecko...")
        response = requests.get(url, params=params, timeout=10)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 429:
            print(f"Rate limited! Headers: {dict(response.headers)}")
            raise requests.exceptions.HTTPError("Rate limited by CoinGecko API")
            
        response.raise_for_status()
        
        data = response.json()
        price = data[coingecko_id]['usd']
        print(f"Successfully fetched {base_currency} price: ${price}")
        
        return float(price)
    
    except requests.exceptions.RequestException as e:
        print(f"Network error fetching {base_currency} price: {e}")
        # Use more realistic fallback prices instead of 1.0
        fallback = FALLBACK_PRICES.get(base_currency, FALLBACK_PRICES.get('ETH', 2500.0))
        print(f"Using fallback price {fallback} for {base_currency}")
        return fallback
    except Exception as e:
        print(f"Unexpected error fetching {base_currency} price: {e}")
        # Use more realistic fallback prices instead of 1.0
        fallback = FALLBACK_PRICES.get(base_currency, FALLBACK_PRICES.get('ETH', 2500.0))
        print(f"Using fallback price {fallback} for {base_currency}")
        return fallback

def get_eth_price():
    """Get current ETH/USDT price from CoinGecko (backward compatibility)"""
    return get_crypto_price('ETH')

def calculate_pnl(entry_price, exit_price, leverage=2.0):
    """Calculate P&L with leverage"""
    price_change_percent = ((exit_price - entry_price) / entry_price) * 100
    leveraged_pnl = price_change_percent * leverage
    
    return leveraged_pnl

def get_pnl_color(pnl_percent):
    """Get color indicator for P&L"""
    if pnl_percent > 0:
        return "🟢"
    elif pnl_percent < 0:
        return "🔴"
    else:
        return "⚪"

def calculate_dollar_pnl(entry_price, exit_price, leverage=2.0, stake_usd=1000.0):
    """Calculate P&L in dollars based on stake amount"""
    price_change_percent = ((exit_price - entry_price) / entry_price)
    leveraged_change = price_change_percent * leverage
    dollar_pnl = stake_usd * leveraged_change
    
    return dollar_pnl


def format_time_fishing(entry_time):
    """Format time spent fishing"""
    try:
        from datetime import datetime, timezone
        
        # Parse entry_time if it's a string
        if isinstance(entry_time, str):
            # Remove timezone info from string if present
            if 'T' in entry_time:
                # ISO format
                entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            else:
                # SQLite format (YYYY-MM-DD HH:MM:SS)
                entry_dt = datetime.strptime(entry_time, '%Y-%m-%d %H:%M:%S')
        else:
            entry_dt = entry_time
        
        # Use local time for comparison since database stores local timestamps
        now = datetime.now()
        
        # Ensure entry_dt is timezone-naive for proper comparison
        if hasattr(entry_dt, 'tzinfo') and entry_dt.tzinfo is not None:
            entry_dt = entry_dt.replace(tzinfo=None)
        
        diff = now - entry_dt
        
        total_seconds = int(diff.total_seconds())
        
        # Ensure we don't show negative time
        if total_seconds < 0:
            total_seconds = 0
        
        if total_seconds < 60:
            return f"{total_seconds}с"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}мин {seconds}с"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}ч {minutes}мин"
            
    except Exception as e:
        print(f"Error formatting time: {e}")
        return "неизвестно"
