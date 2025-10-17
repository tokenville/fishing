import aiohttp
import asyncio
import logging
import time
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Mapping of base currencies to CoinGecko IDs
COINGECKO_IDS = {
    'TAC': 'tac',
}

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# Price caching to reduce API calls
PRICE_CACHE_TTL = 10  # Cache prices for 10 seconds
_price_cache: Dict[str, Tuple[float, float]] = {}  # {currency: (price, timestamp)}
_cache_lock = asyncio.Lock()

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

async def get_crypto_price(base_currency, use_cache=True):
    """
    Get current price for any supported cryptocurrency with caching and retry mechanism.

    Args:
        base_currency: Currency symbol (e.g., 'TAC', 'BTC')
        use_cache: WhTACer to use cached price (default: True)

    Returns:
        Current price in USD

    Note:
        Prices are cached for PRICE_CACHE_TTL seconds to reduce API calls.
        Set use_cache=False to force fresh API call.
    """
    if base_currency not in COINGECKO_IDS:
        logger.error(f"Unsupported currency: {base_currency}")
        raise ValueError(f"Unsupported currency: {base_currency}")

    # Check cache first
    if use_cache:
        async with _cache_lock:
            if base_currency in _price_cache:
                cached_price, cached_time = _price_cache[base_currency]
                age = time.time() - cached_time
                if age < PRICE_CACHE_TTL:
                    return cached_price
                else:
                    logger.debug(f"Cache expired for {base_currency} (age: {age:.1f}s > {PRICE_CACHE_TTL}s)")

    coingecko_id = COINGECKO_IDS[base_currency]
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': coingecko_id,
        'vs_currencies': 'usd'
    }
    
    for attempt in range(MAX_RETRIES):
        try:            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    
                    if response.status == 429:
                        retry_after = response.headers.get('retry-after', RETRY_DELAY)
                        logger.warning(f"Rate limited for {base_currency}! Retry after: {retry_after}s. Headers: {dict(response.headers)}")
                        
                        if attempt < MAX_RETRIES - 1:
                            wait_time = max(int(retry_after) if retry_after.isdigit() else RETRY_DELAY, RETRY_DELAY)
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise aiohttp.ClientResponseError(response.request_info, response.history, status=429, message=f"Rate limited by CoinGecko API after {MAX_RETRIES} attempts")
                    
                    response.raise_for_status()
                    data = await response.json()
            
            price = data[coingecko_id]['usd']

            # Update cache
            async with _cache_lock:
                _price_cache[base_currency] = (float(price), time.time())

            return float(price)
            
        except aiohttp.ClientError as e:
            logger.warning(f"Network error on attempt {attempt + 1} fetching {base_currency} price: {e}")
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)  # Exponential backoff
                await asyncio.sleep(wait_time)
                continue
            else:
                logger.error(f"Failed to fetch {base_currency} price after {MAX_RETRIES} attempts due to network error: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1} fetching {base_currency} price: {e}")
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                await asyncio.sleep(wait_time)
                continue
            else:
                logger.error(f"Failed to fetch {base_currency} price after {MAX_RETRIES} attempts due to unexpected error: {e}")
                raise
    
    # This should never be reached, but just in case
    logger.error(f"Exhausted all retry attempts for {base_currency}")
    raise RuntimeError(f"Failed to fetch {base_currency} price after {MAX_RETRIES} attempts")

async def get_tac_price():
    """Get current TAC/USDT price from CoinGecko (backward compatibility)"""
    return await get_crypto_price('TAC')


async def warm_up_price_cache():
    """
    Pre-fetch and cache prices for all supported currencies.
    This reduces initial API calls when users start fishing.

    Returns:
        Number of successfully cached currencies
    """
    success_count = 0

    for currency in COINGECKO_IDS.keys():
        try:
            await get_crypto_price(currency, use_cache=False)
            success_count += 1
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning(f"Failed to warm up cache for {currency}: {e}")
    return success_count


async def get_cache_stats() -> dict:
    """
    Get statistics about the price cache.

    Returns:
        Dictionary with cache statistics
    """
    async with _cache_lock:
        now = time.time()
        stats = {
            'total_cached': len(_price_cache),
            'currencies': {}
        }

        for currency, (price, cached_time) in _price_cache.items():
            age = now - cached_time
            stats['currencies'][currency] = {
                'price': price,
                'age_seconds': round(age, 1),
                'is_fresh': age < PRICE_CACHE_TTL
            }

        return stats


# ==================== LEGACY IMPORTS ====================
# All PnL and time calculation functions have been moved to fishing_calculations.py
# These imports provide backward compatibility during migration

from src.utils.fishing_calculations import (
    calculate_pnl,
    calculate_pnl_percent,
    calculate_dollar_pnl,
    calculate_pnl_dollars,
    get_pnl_color,
    get_fishing_time_seconds,
    get_fishing_duration_seconds,
    format_time_fishing,
    format_fishing_duration_from_entry,
    format_fishing_duration
)

__all__ = [
    'get_crypto_price',
    'get_tac_price',
    'get_price_error_message',
    'warm_up_price_cache',
    'get_cache_stats',
    'PRICE_CACHE_TTL',
    # Legacy exports for backward compatibility
    'calculate_pnl',
    'calculate_pnl_percent',
    'calculate_dollar_pnl',
    'calculate_pnl_dollars',
    'get_pnl_color',
    'get_fishing_time_seconds',
    'get_fishing_duration_seconds',
    'format_time_fishing',
    'format_fishing_duration_from_entry',
    'format_fishing_duration'
]
