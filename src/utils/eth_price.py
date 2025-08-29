import requests
import time

def get_eth_price():
    """Get current ETH/USDT price from CoinGecko"""
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            'ids': 'ethereum',
            'vs_currencies': 'usd'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        price = data['ethereum']['usd']
        
        return float(price)
    
    except Exception as e:
        print(f"Error fetching ETH price: {e}")
        # Fallback price for testing
        return 2500.0

def calculate_pnl(entry_price, exit_price, leverage=2.0):
    """Calculate P&L with leverage"""
    price_change_percent = ((exit_price - entry_price) / entry_price) * 100
    leveraged_pnl = price_change_percent * leverage
    
    return leveraged_pnl

def get_fish_by_pnl(pnl_percent):
    """Determine fish type based on P&L percentage"""
    if pnl_percent <= -20:
        return "🦐 Soggy Boot"
    elif pnl_percent <= 0:
        return "🐡 Pufferfish of Regret"
    elif pnl_percent <= 10:
        return "🐟 Lucky Minnow"
    elif pnl_percent <= 30:
        return "🐠 Diamond Fin Bass"
    elif pnl_percent <= 50:
        return "🦈 Profit Shark"
    else:
        return "🐋 Legendary Whale"

def format_time_fishing(entry_time):
    """Format time spent fishing"""
    try:
        from datetime import datetime
        
        # Parse entry_time if it's a string
        if isinstance(entry_time, str):
            entry_dt = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
        else:
            entry_dt = entry_time
            
        now = datetime.now()
        diff = now - entry_dt.replace(tzinfo=None)
        
        total_seconds = int(diff.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
            
    except Exception as e:
        print(f"Error formatting time: {e}")
        return "unknown time"
