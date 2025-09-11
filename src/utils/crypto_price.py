import aiohttp
import asyncio
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

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

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Game-friendly error messages for price fetch failures
PRICE_ERROR_MESSAGES = [
    "🐟 The fish got away at the last moment! Market data slipped through our nets.",
    "🌊 Crypto currents are too strong right now! The fish escaped back to deeper waters.",
    "📡 Market signals are scrambled! The fish vanished in a cloud of digital bubbles.",
    "⚡ Lightning-fast market movements confused our fishing sonar! Try again in a moment.",
    "🎣 The fishing line got tangled in market volatility! Cast again when waters calm.",
    "🌪️ A crypto storm disrupted our fishing! The fish scattered back to their blockchain homes.",
    "🔄 Market currents changed direction! Our fishing data needs a moment to recalibrate.",
    "🐠 The fish school moved too fast! Market prices are swimming away from our hooks."
]

def get_price_error_message():
    """Get a random game-friendly error message for price fetch failures"""
    import random
    return random.choice(PRICE_ERROR_MESSAGES)

async def get_crypto_price(base_currency):
    """Get current price for any supported cryptocurrency with retry mechanism"""
    if base_currency not in COINGECKO_IDS:
        logger.error(f"Unsupported currency: {base_currency}")
        raise ValueError(f"Unsupported currency: {base_currency}")
        
    coingecko_id = COINGECKO_IDS[base_currency]
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': coingecko_id,
        'vs_currencies': 'usd'
    }
    
    logger.debug(f"Starting price fetch for {base_currency} (coingecko_id: {coingecko_id})")
    
    for attempt in range(MAX_RETRIES):
        try:
            logger.debug(f"Attempt {attempt + 1}/{MAX_RETRIES} fetching {base_currency} price from CoinGecko...")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    logger.debug(f"Response status: {response.status} for {base_currency}")
                    
                    if response.status == 429:
                        retry_after = response.headers.get('retry-after', RETRY_DELAY)
                        logger.warning(f"Rate limited for {base_currency}! Retry after: {retry_after}s. Headers: {dict(response.headers)}")
                        
                        if attempt < MAX_RETRIES - 1:
                            wait_time = max(int(retry_after) if retry_after.isdigit() else RETRY_DELAY, RETRY_DELAY)
                            logger.debug(f"Waiting {wait_time}s before retry for {base_currency}")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise aiohttp.ClientResponseError(response.request_info, response.history, status=429, message=f"Rate limited by CoinGecko API after {MAX_RETRIES} attempts")
                    
                    response.raise_for_status()
                    data = await response.json()
            
            price = data[coingecko_id]['usd']
            logger.debug(f"Successfully fetched {base_currency} price: ${price} on attempt {attempt + 1}")
            
            return float(price)
            
        except aiohttp.ClientError as e:
            logger.warning(f"Network error on attempt {attempt + 1} fetching {base_currency} price: {e}")
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)  # Exponential backoff
                logger.debug(f"Waiting {wait_time}s before retry for {base_currency}")
                await asyncio.sleep(wait_time)
                continue
            else:
                logger.error(f"Failed to fetch {base_currency} price after {MAX_RETRIES} attempts due to network error: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1} fetching {base_currency} price: {e}")
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                logger.debug(f"Waiting {wait_time}s before retry for {base_currency}")
                await asyncio.sleep(wait_time)
                continue
            else:
                logger.error(f"Failed to fetch {base_currency} price after {MAX_RETRIES} attempts due to unexpected error: {e}")
                raise
    
    # This should never be reached, but just in case
    logger.error(f"Exhausted all retry attempts for {base_currency}")
    raise RuntimeError(f"Failed to fetch {base_currency} price after {MAX_RETRIES} attempts")

async def get_eth_price():
    """Get current ETH/USDT price from CoinGecko (backward compatibility)"""
    return await get_crypto_price('ETH')

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


def get_fishing_time_seconds(entry_time):
    """Get fishing time in seconds"""
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
            
        return total_seconds
        
    except Exception as e:
        logger.error(f"Error calculating time seconds: {e}")
        return 0

def format_time_fishing(entry_time):
    """Format time spent fishing"""
    try:
        total_seconds = get_fishing_time_seconds(entry_time)
        
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
        logger.error(f"Error formatting time: {e}")
        return "неизвестно"
