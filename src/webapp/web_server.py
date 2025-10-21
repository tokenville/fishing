"""
Web server for Telegram Mini App
Provides API endpoints and serves static files for the fishing game web interface
"""

import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from aiohttp import web, web_request
from aiohttp.web import middleware
import aiofiles

from src.database.db_manager import (
    get_user, get_user_rods, get_fish_by_id,
    get_user_fish_collection, get_user_fish_history,
    get_user_active_rod, set_user_active_rod,
    get_user_virtual_balance, get_flexible_leaderboard,
    get_user_group_ponds, get_active_position, create_position_with_gear,
    use_bait, ensure_user_has_active_rod, get_pond_by_id, get_rod_by_id,
    get_suitable_fish, close_position, can_use_free_cast, mark_onboarding_action,
    update_user_balance_after_hook
)
from src.utils.crypto_price import get_crypto_price as get_crypto_price_util
from src.utils.fishing_calculations import (
    calculate_pnl_percent,
    get_fishing_duration_seconds
)

logger = logging.getLogger(__name__)

class WebAppServer:
    def __init__(self, application=None):
        self.application = application
        self.app = web.Application(middlewares=[self.cors_middleware])
        self.setup_routes()
        
    @middleware
    async def cors_middleware(self, request, handler):
        """CORS middleware for API requests"""
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    def setup_routes(self):
        """Setup all routes for the web application"""
        
        # Static files
        self.app.router.add_get('/webapp', self.serve_main_page)
        self.app.router.add_static('/static/', path='webapp/static/', name='static')
        
        # API endpoints
        self.app.router.add_get('/api/user/{user_id}', self.get_user_info)
        self.app.router.add_get('/api/user/{user_id}/stats', self.get_user_statistics)
        self.app.router.add_get('/api/user/{user_id}/fish', self.get_user_fish_collection)
        self.app.router.add_get('/api/user/{user_id}/rods', self.get_user_rods)
        self.app.router.add_get('/api/user/{user_id}/active-rod', self.get_user_active_rod)
        self.app.router.add_post('/api/user/{user_id}/active-rod', self.set_user_active_rod)
        self.app.router.add_get('/api/fish/{fish_id}/image', self.get_fish_image)

        # Leaderboard and balance endpoints
        self.app.router.add_get('/api/user/{user_id}/balance', self.get_user_balance)
        self.app.router.add_get('/api/leaderboard', self.get_leaderboard)
        
        # Payment endpoints
        self.app.router.add_get('/api/products', self.get_available_products)
        self.app.router.add_get('/api/user/{user_id}/transactions', self.get_user_transactions)
        self.app.router.add_post('/api/user/{user_id}/purchase', self.create_purchase_invoice)
        
        # Cast endpoints
        self.app.router.add_get('/api/user/{user_id}/ponds', self.get_user_ponds)
        self.app.router.add_get('/api/user/{user_id}/position', self.get_user_position)
        self.app.router.add_post('/api/user/{user_id}/cast', self.create_position)
        self.app.router.add_post('/api/user/{user_id}/hook', self.complete_position)
        self.app.router.add_get('/api/crypto-price/{symbol}', self.get_crypto_price)
        
        # Bot info
        self.app.router.add_get('/api/bot/info', self.get_bot_info)
        
        # Health check
        self.app.router.add_get('/health', self.health_check)
    
    async def serve_main_page(self, request):
        """Serve the main webapp HTML page"""
        logger.debug(f"Serving main webapp page, request from: {request.remote}")
        try:
            webapp_path = Path('webapp/templates/index.html')
            
            if not webapp_path.exists():
                logger.error(f"Main page file not found: {webapp_path.absolute()}")
                return web.Response(
                    text="<h1>WebApp not found</h1><p>webapp/templates/index.html does not exist</p>",
                    content_type='text/html',
                    status=404
                )
            
            async with aiofiles.open(webapp_path, mode='r', encoding='utf-8') as f:
                content = await f.read()
            
            logger.debug(f"Successfully served main page, content length: {len(content)}")
            return web.Response(text=content, content_type='text/html')
        except Exception as e:
            logger.error(f"Error serving webapp: {e}")
            logger.exception("Full serve_main_page error traceback:")
            return web.Response(
                text=f"<h1>Error</h1><p>Failed to load webapp: {str(e)}</p>",
                content_type='text/html',
                status=500
            )
    
    async def get_user_info(self, request):
        """Get user information"""
        try:
            user_id = int(request.match_info['user_id'])
            user = await get_user(user_id)
            
            if not user:
                return web.json_response({'error': 'User not found'}, status=404)
            
            return web.json_response({
                'id': user['telegram_id'],
                'username': user['username'],
                'level': user['level'],
                'experience': user['experience'],
                'bait_tokens': user['bait_tokens'],
                'created_at': user['created_at'].isoformat() if user['created_at'] else None
            })
        except ValueError:
            return web.json_response({'error': 'Invalid user ID'}, status=400)
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def get_user_statistics(self, request):
        """Get comprehensive user statistics including fish counts"""
        try:
            user_id = int(request.match_info['user_id'])
            
            from src.database.db_manager import (
                get_user, get_user_rods, get_total_fish_count, 
                get_user_unique_fish_count
            )
            
            # Get user info
            user = await get_user(user_id)
            if not user:
                return web.json_response({'error': 'User not found'}, status=404)
            
            # Get user rods count
            user_rods = await get_user_rods(user_id)
            rods_count = len(user_rods) if user_rods else 0
            
            # Get fish statistics
            total_fish = await get_total_fish_count()
            caught_fish = await get_user_unique_fish_count(user_id)
            
            return web.json_response({
                'id': user['telegram_id'],
                'username': user['username'],
                'level': user['level'],
                'experience': user['experience'],
                'bait_tokens': user['bait_tokens'],
                'created_at': user['created_at'].isoformat() if user['created_at'] else None,
                'rods_count': rods_count,
                'fish_caught': caught_fish,
                'fish_total': total_fish,
                'fish_display': f"{caught_fish}/{total_fish}"
            })
            
        except ValueError:
            return web.json_response({'error': 'Invalid user ID'}, status=400)
        except Exception as e:
            logger.error(f"Error getting user statistics: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def get_user_fish_collection(self, request):
        """Get user's fish collection with catch history"""
        try:
            user_id = int(request.match_info['user_id'])
            
            # Get fish collection
            fish_collection = await get_user_fish_collection(user_id)
            
            if not fish_collection:
                return web.json_response({
                    'fish': [],
                    'total_unique': 0,
                    'total_caught': 0
                })
            
            # Import function to get CDN URLs
            from src.database.db_manager import get_fish_image_cache
            from src.utils.bunny_cdn import cdn_uploader
            
            # Process collection data
            fish_data = []
            unique_fish = set()
            
            for catch in fish_collection:
                # Get CDN URL for this fish
                cache_info = await get_fish_image_cache(
                    catch['fish_id'], 
                    catch['fish_rarity']
                )
                
                # Get optimized thumbnail URL for grid display
                cdn_url = None
                thumbnail_url = None
                if cache_info and cache_info.get('cdn_url'):
                    cdn_url = cache_info['cdn_url']
                    thumbnail_url = cdn_uploader.get_thumbnail_url(cdn_url, size=200)
                
                fish_info = {
                    'id': catch['fish_id'],
                    'name': catch['fish_name'],
                    'emoji': catch['fish_emoji'],
                    'description': catch['fish_description'],
                    'rarity': catch['fish_rarity'],
                    'pnl_percent': float(catch['pnl_percent']) if catch['pnl_percent'] else 0.0,
                    'caught_at': catch['exit_time'].isoformat() if catch['exit_time'] else None,
                    'rod_name': catch['rod_name'],
                    'pond_name': catch['pond_name'],
                    'cdn_url': cdn_url,
                    'thumbnail_url': thumbnail_url
                }
                fish_data.append(fish_info)
                unique_fish.add(catch['fish_id'])
            
            return web.json_response({
                'fish': fish_data,
                'total_unique': len(unique_fish),
                'total_caught': len(fish_data)
            })
            
        except ValueError:
            return web.json_response({'error': 'Invalid user ID'}, status=400)
        except Exception as e:
            logger.error(f"Error getting fish collection: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def get_user_rods(self, request):
        """Get user's rod collection"""
        try:
            user_id = int(request.match_info['user_id'])
            user_rods = await get_user_rods(user_id)
            
            if not user_rods:
                return web.json_response([])
            
            rods_data = []
            for rod in user_rods:
                rod_info = {
                    'id': rod['id'],
                    'name': rod['name'],
                    'leverage': float(rod['leverage']),
                    'price': rod['price'],
                    'rarity': rod['rarity'],
                    'rod_type': rod.get('rod_type', 'neutral'),
                    'visual_id': rod.get('visual_id', 'default')
                }
                rods_data.append(rod_info)
            
            return web.json_response(rods_data)
            
        except ValueError:
            return web.json_response({'error': 'Invalid user ID'}, status=400)
        except Exception as e:
            logger.error(f"Error getting user rods: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def get_user_active_rod(self, request):
        """Get user's currently active rod"""
        try:
            user_id = int(request.match_info['user_id'])
            active_rod = await get_user_active_rod(user_id)
            
            if not active_rod:
                return web.json_response({'active_rod': None})
            
            rod_info = {
                'id': active_rod['id'],
                'name': active_rod['name'],
                'leverage': float(active_rod['leverage']),
                'price': active_rod['price'],
                'rarity': active_rod['rarity'],
                'rod_type': active_rod.get('rod_type', 'neutral'),
                'visual_id': active_rod.get('visual_id', 'default')
            }
            
            return web.json_response({'active_rod': rod_info})
            
        except ValueError:
            return web.json_response({'error': 'Invalid user ID'}, status=400)
        except Exception as e:
            logger.error(f"Error getting active rod: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def set_user_active_rod(self, request):
        """Set user's active rod"""
        try:
            user_id = int(request.match_info['user_id'])
            data = await request.json()
            rod_id = int(data.get('rod_id'))
            
            if not rod_id:
                return web.json_response({'error': 'Missing rod_id'}, status=400)
            
            success = await set_user_active_rod(user_id, rod_id)
            
            if not success:
                return web.json_response({'error': 'User does not own this rod'}, status=400)
            
            return web.json_response({'success': True})
            
        except (ValueError, TypeError):
            return web.json_response({'error': 'Invalid user ID or rod ID'}, status=400)
        except Exception as e:
            logger.error(f"Error setting active rod: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def get_fish_image(self, request):
        """Get fish image - redirect to CDN, generate if needed, or serve from cache"""
        try:
            fish_id = int(request.match_info['fish_id'])
            
            # Get optional size parameter for optimization
            size = request.query.get('size', 'full')
            
            # Get fish info for rarity
            from src.database.db_manager import get_fish_by_id, get_fish_image_cache, save_fish_image_cache
            from src.utils.bunny_cdn import cdn_uploader
            from src.generators.fish_card_generator import generate_fish_card_from_db
            
            fish = await get_fish_by_id(fish_id)
            
            if not fish:
                return web.Response(status=404)
            
            # Try to get cached image info from database
            cache_info = await get_fish_image_cache(fish_id, fish['rarity'])
            
            # If we have CDN URL, redirect to it with optimization
            if cache_info and cache_info.get('cdn_url'):
                cdn_url = cache_info['cdn_url']
                
                # Apply size optimization based on request
                if size == 'thumbnail':
                    optimized_url = cdn_uploader.get_thumbnail_url(cdn_url, size=200)
                elif size == 'medium':
                    optimized_url = cdn_uploader.get_optimized_url(cdn_url, width=400, quality=85)
                else:
                    optimized_url = cdn_uploader.get_full_image_url(cdn_url, max_width=800)
                
                # Redirect to CDN
                return web.Response(status=302, headers={'Location': optimized_url})
            
            # If we have local file but no CDN URL, try to upload to CDN
            if cache_info and cache_info.get('image_path') and Path(cache_info['image_path']).exists():
                try:
                    # Read existing local file
                    async with aiofiles.open(cache_info['image_path'], mode='rb') as f:
                        image_content = await f.read()
                    
                    # Try to upload to CDN
                    cdn_url = await cdn_uploader.upload_fish_image(fish_id, fish['rarity'], image_content)
                    if cdn_url:
                        # Update database with CDN URL
                        cache_key = cache_info.get('cache_key', f"fish_{fish_id}_{fish['rarity']}")
                        await save_fish_image_cache(fish_id, fish['rarity'], cache_info['image_path'], cache_key, cdn_url)
                        logger.info(f"Migrated existing fish image {fish_id} to CDN: {cdn_url}")
                        
                        # Redirect to optimized CDN URL
                        if size == 'thumbnail':
                            optimized_url = cdn_uploader.get_thumbnail_url(cdn_url, size=200)
                        elif size == 'medium':
                            optimized_url = cdn_uploader.get_optimized_url(cdn_url, width=400, quality=85)
                        else:
                            optimized_url = cdn_uploader.get_full_image_url(cdn_url, max_width=800)
                        
                        return web.Response(status=302, headers={'Location': optimized_url})
                    
                    # If CDN upload failed, serve local file
                    return web.Response(body=image_content, content_type='image/png')
                    
                except Exception as e:
                    logger.warning(f"Failed to upload existing image to CDN: {e}")
                    # Fallback to serving local file
                    async with aiofiles.open(cache_info['image_path'], mode='rb') as f:
                        content = await f.read()
                    return web.Response(body=content, content_type='image/png')
            
            # No cached image - generate new one
            try:
                logger.info(f"Generating new image for fish {fish_id} on-demand")
                image_content = await generate_fish_card_from_db(fish)
                
                # Save locally and upload to CDN
                cache_dir = Path('generated_fish_cache')
                cache_dir.mkdir(exist_ok=True)
                cache_key = f"fish_{fish_id}_{fish['rarity']}"
                image_path = cache_dir / f"{cache_key}.png"
                
                async with aiofiles.open(image_path, mode='wb') as f:
                    await f.write(image_content)
                
                # Upload to CDN
                cdn_url = await cdn_uploader.upload_fish_image(fish_id, fish['rarity'], image_content)
                
                # Save to database
                await save_fish_image_cache(fish_id, fish['rarity'], str(image_path), cache_key, cdn_url)
                
                if cdn_url:
                    logger.info(f"Generated and uploaded new fish image {fish_id} to CDN: {cdn_url}")
                    # Redirect to optimized CDN URL
                    if size == 'thumbnail':
                        optimized_url = cdn_uploader.get_thumbnail_url(cdn_url, size=200)
                    elif size == 'medium':
                        optimized_url = cdn_uploader.get_optimized_url(cdn_url, width=400, quality=85)
                    else:
                        optimized_url = cdn_uploader.get_full_image_url(cdn_url, max_width=800)
                    
                    return web.Response(status=302, headers={'Location': optimized_url})
                
                # If CDN upload failed, serve generated image
                return web.Response(body=image_content, content_type='image/png')
                
            except Exception as e:
                logger.error(f"Failed to generate image for fish {fish_id}: {e}")
                # Ultimate fallback - return 404
                return web.Response(status=404)
            
        except ValueError:
            return web.json_response({'error': 'Invalid fish ID'}, status=400)
        except Exception as e:
            logger.error(f"Error getting fish image: {e}")
            return web.Response(status=500)
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'service': 'fishing-bot-webapp'
        })
    
    async def get_user_balance(self, request):
        """Get user's virtual balance and P&L stats"""
        try:
            user_id = int(request.match_info['user_id'])
            balance_data = await get_user_virtual_balance(user_id)
            
            # Calculate P&L from starting balance
            profit_loss = balance_data['balance'] - 10000
            
            return web.json_response({
                'balance': balance_data['balance'],
                'profit_loss': profit_loss,
                'profit_loss_percent': (profit_loss / 10000) * 100,
                'total_trades': balance_data['total_trades'],
                'winning_trades': balance_data['winning_trades'],
                'win_rate': (balance_data['winning_trades'] / balance_data['total_trades'] * 100) if balance_data['total_trades'] > 0 else 0,
                'avg_pnl': balance_data['avg_pnl']
            })
        except ValueError:
            return web.json_response({'error': 'Invalid user ID'}, status=400)
        except Exception as e:
            logger.error(f"Error getting user balance: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def get_leaderboard(self, request):
        """Get leaderboard data with optional filters"""
        try:
            # Parse query parameters
            params = request.rel_url.query
            
            leaderboard_data = await get_flexible_leaderboard(
                pond_id=int(params.get('pond_id')) if params.get('pond_id') else None,
                rod_id=int(params.get('rod_id')) if params.get('rod_id') else None,
                time_period=params.get('type', 'all'),
                user_id=int(params.get('user_id')) if params.get('user_id') else None,
                limit=int(params.get('limit', 10)),
                include_bottom=params.get('include_bottom', 'true').lower() == 'true'
            )
            
            # Format response for frontend
            return web.json_response({
                'top': [
                    {
                        'user_id': player['telegram_id'],
                        'username': player['username'],
                        'level': player['level'],
                        'balance': float(player['balance']),
                        'total_trades': player['total_trades'],
                        'avg_pnl': float(player['avg_pnl']) if player['avg_pnl'] else 0,
                        'best_trade': float(player['best_trade']) if player['best_trade'] else 0,
                        'worst_trade': float(player['worst_trade']) if player['worst_trade'] else 0,
                        'rank': player.get('rank', i+1)
                    }
                    for i, player in enumerate(leaderboard_data['top'])
                ],
                'bottom': [
                    {
                        'user_id': player['telegram_id'],
                        'username': player['username'],
                        'level': player['level'],
                        'balance': float(player['balance']),
                        'total_trades': player['total_trades'],
                        'avg_pnl': float(player['avg_pnl']) if player['avg_pnl'] else 0
                    }
                    for player in leaderboard_data['bottom']
                ],
                'user_position': leaderboard_data['user_position'],
                'total_players': leaderboard_data['total_players'],
                'filters': leaderboard_data['filters_applied']
            })
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)

    async def get_available_products(self, request):
        """Get available BAIT products for purchase"""
        try:
            from src.database.db_manager import get_available_products
            
            products = await get_available_products()
            
            return web.json_response({
                'products': [
                    {
                        'id': product['id'],
                        'name': product['name'],
                        'description': product['description'],
                        'bait_amount': product['bait_amount'],
                        'stars_price': product['stars_price'],
                        'is_active': product['is_active']
                    }
                    for product in products
                ]
            })
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)

    async def get_user_transactions(self, request):
        """Get user's transaction history"""
        try:
            user_id = int(request.match_info['user_id'])
            limit = int(request.query.get('limit', 10))
            
            from src.database.db_manager import get_user_transactions
            
            transactions = await get_user_transactions(user_id, limit)
            
            return web.json_response({
                'transactions': [
                    {
                        'id': t['id'],
                        'product_name': t['product_name'],
                        'bait_amount': t['bait_amount'],
                        'stars_amount': t['stars_amount'],
                        'status': t['status'],
                        'created_at': t['created_at'].isoformat() if t['created_at'] else None,
                        'completed_at': t['completed_at'].isoformat() if t['completed_at'] else None
                    }
                    for t in transactions
                ]
            })
        except Exception as e:
            logger.error(f"Error getting user transactions: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)

    async def create_purchase_invoice(self, request):
        """Create purchase invoice for webapp"""
        try:
            user_id = int(request.match_info['user_id'])
            data = await request.json()
            
            product_id = data.get('product_id')
            quantity = data.get('quantity', 1)
            
            if not product_id:
                return web.json_response({'error': 'Product ID required'}, status=400)
            
            from src.database.db_manager import get_product_by_id, get_user
            
            # Validate product
            product = await get_product_by_id(product_id)
            if not product:
                return web.json_response({'error': 'Product not found'}, status=404)
            
            # Validate user
            user = await get_user(user_id)
            if not user:
                return web.json_response({'error': 'User not found'}, status=404)
            
            # Check if we have access to the bot application
            if not self.application:
                return web.json_response({'error': 'Bot not available'}, status=500)
            
            # Calculate totals
            total_stars = product['stars_price'] * quantity
            total_bait = product['bait_amount'] * quantity
            
            # Generate payload for Telegram invoice
            payload = f"bait_{product_id}_{quantity}"
            
            # Create invoice using bot API
            title = f"BAITs x{quantity}"
            description = f"{total_bait} BAITs for fishing"
            prices = [{"label": "BAITs", "amount": total_stars}]
            
            # Send invoice using bot
            message = await self.application.bot.send_invoice(
                chat_id=user_id,
                title=title,
                description=description,
                payload=payload,
                provider_token="",  # Empty for Stars
                currency="XTR",
                prices=prices
            )
            
            # Invoice sent successfully - return success response
            return web.json_response({
                'success': True,
                'message': 'Invoice sent to your chat',
                'purchase_info': {
                    'product_name': product['name'],
                    'bait_amount': total_bait,
                    'stars_amount': total_stars,
                    'quantity': quantity
                }
            })
        except Exception as e:
            logger.error(f"Error creating purchase invoice: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    # === CAST ENDPOINTS ===
    
    async def get_user_ponds(self, request):
        """Get user's available ponds for fishing"""
        try:
            user_id = int(request.match_info['user_id'])
            ponds = await get_user_group_ponds(user_id)
            
            # Format response for frontend
            formatted_ponds = []
            for pond in ponds:
                formatted_ponds.append({
                    'id': pond['id'],
                    'name': pond['name'],
                    'trading_pair': pond['trading_pair'],
                    'base_currency': pond['base_currency'],
                    'quote_currency': pond['quote_currency'],
                    'member_count': pond.get('member_count', 0),
                    'required_level': pond.get('required_level', 1),
                    'is_active': pond.get('is_active', True)
                })
            
            return web.json_response(formatted_ponds)
            
        except ValueError:
            return web.json_response({'error': 'Invalid user ID'}, status=400)
        except Exception as e:
            logger.error(f"Error getting user ponds: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def get_user_position(self, request):
        """Get user's current active position"""
        try:
            user_id = int(request.match_info['user_id'])
            position = await get_active_position(user_id)
            
            if not position:
                return web.json_response(None)
            
            # Format position for frontend
            formatted_position = {
                'id': position['id'],
                'pond_id': position['pond_id'],
                'rod_id': position['rod_id'],
                'entry_price': float(position['entry_price']),
                'entry_time': position['entry_time'].isoformat() if position['entry_time'] else None,
                'fish_caught_id': position.get('fish_caught_id')
            }
            
            return web.json_response(formatted_position)
            
        except ValueError:
            return web.json_response({'error': 'Invalid user ID'}, status=400)
        except Exception as e:
            logger.error(f"Error getting user position: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    
    async def create_position(self, request):
        """Create a new fishing position (cast)"""
        try:
            user_id = int(request.match_info['user_id'])
            data = await request.json()
            
            # Validate required fields
            required_fields = ['pond_id', 'rod_id', 'entry_price']
            for field in required_fields:
                if field not in data:
                    return web.json_response({'error': f'Missing field: {field}'}, status=400)
            
            pond_id = int(data['pond_id'])
            rod_id = int(data['rod_id'])
            entry_price = float(data['entry_price'])
            
            # Check if user already has active position
            existing_position = await get_active_position(user_id)
            if existing_position:
                return web.json_response({
                    'success': False,
                    'error': 'active_position_exists'
                }, status=400)
            
            # Check and consume BAIT
            user = await get_user(user_id)

            # Check if user can use free tutorial cast
            can_use_free = await can_use_free_cast(user_id)

            # Check if user has enough BAIT (skip check for free tutorial cast)
            if not can_use_free and (not user or user['bait_tokens'] <= 0):
                return web.json_response({
                    'success': False,
                    'error': 'insufficient_bait'
                }, status=400)

            # Ensure user has active rod
            await ensure_user_has_active_rod(user_id)

            # Use BAIT token (skip for free tutorial cast)
            if can_use_free:
                # Mark that user used their free cast
                await mark_onboarding_action(user_id, 'first_cast')
            else:
                await use_bait(user_id)
            
            # Create position
            await create_position_with_gear(user_id, pond_id, rod_id, entry_price)
            
            # Get the created position
            new_position = await get_active_position(user_id)
            
            return web.json_response({
                'success': True,
                'position': {
                    'id': new_position['id'],
                    'pond_id': new_position['pond_id'],
                    'rod_id': new_position['rod_id'],
                    'entry_price': float(new_position['entry_price']),
                    'entry_time': new_position['entry_time'].isoformat() if new_position['entry_time'] else None
                }
            })
            
        except ValueError as e:
            return web.json_response({'error': f'Invalid data: {str(e)}'}, status=400)
        except Exception as e:
            logger.error(f"Error creating position: {e}")
            return web.json_response({
                'success': False,
                'error': 'database_error'
            }, status=500)
    
    async def complete_position(self, request):
        """Complete fishing position (hook)"""
        try:
            user_id = int(request.match_info['user_id'])
            
            # Check if user has active position
            position = await get_active_position(user_id)
            if not position:
                return web.json_response({
                    'success': False,
                    'error': 'no_active_position'
                }, status=400)
            
            # Get pond and rod data for the position
            pond = await get_pond_by_id(position['pond_id']) if position['pond_id'] else None
            rod = await get_rod_by_id(position['rod_id']) if position['rod_id'] else None
            
            # Get base currency for price fetching
            base_currency = pond['base_currency'] if pond else 'TAC'
            leverage = rod['leverage'] if rod else 1.5
            entry_price = position['entry_price']
            entry_time = position['entry_time']

            # Calculate fishing time using centralized UTC-aware helper
            fishing_time_seconds = get_fishing_duration_seconds(entry_time)

            # Get current price
            current_price = await get_crypto_price_util(base_currency)

            # Calculate P&L using centralized helper
            pnl_percent = calculate_pnl_percent(entry_price, current_price, leverage)

            logger.info(
                f"WebApp hook: user={user_id}, position_id={position['id']}, "
                f"entry={entry_price:.2f}, exit={current_price:.2f}, "
                f"leverage={leverage}x, pnl={pnl_percent:.4f}%, time={fishing_time_seconds}s"
            )
            
            # Quick fishing check - prevent fishing in under 60 seconds with minimal P&L
            if fishing_time_seconds < 60 and abs(pnl_percent) < 0.1:
                from src.bot.ui.messages import get_quick_fishing_message
                quick_message = get_quick_fishing_message(fishing_time_seconds)
                return web.json_response({
                    'success': False,
                    'error': 'quick_fishing',
                    'message': quick_message,
                    'fishing_time_seconds': fishing_time_seconds,
                    'pnl_percent': pnl_percent
                }, status=400)
            
            # Get user level
            user = await get_user(user_id)
            user_level = user['level'] if user else 1
            
            # Get suitable fish
            fish_data = await get_suitable_fish(
                pnl_percent, 
                user_level,
                position['pond_id'] if position['pond_id'] else 1,
                position['rod_id'] if position['rod_id'] else 1
            )
            
            if not fish_data:
                # Fallback to any fish within range
                fish_data = await get_suitable_fish(pnl_percent, 1, 1, 1)
            
            if fish_data:
                # Generate catch story
                from src.bot.ui.messages import get_catch_story_from_db
                catch_story = get_catch_story_from_db(fish_data)

                # Close position with fish ID
                await close_position(position['id'], current_price, pnl_percent, fish_data['id'])

                # Update user balance based on P&L
                await update_user_balance_after_hook(user_id, pnl_percent)

                # Get fish image URL (image will be generated on-demand if needed)
                fish_image_url = f"/api/fish/{fish_data['id']}/image"

                # Return success with fish data
                return web.json_response({
                    'success': True,
                    'fish': {
                        'id': fish_data['id'],
                        'name': fish_data['name'],
                        'emoji': fish_data['emoji'],
                        'description': fish_data['description'],
                        'rarity': fish_data['rarity'],
                        'image_url': fish_image_url,
                        'catch_story': catch_story
                    },
                    'result': {
                        'pnl_percent': pnl_percent,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'fishing_time_seconds': fishing_time_seconds,
                        'pond_name': pond['name'] if pond else 'Unknown Pond',
                        'rod_name': rod['name'] if rod else 'Unknown Rod'
                    }
                })
            else:
                # Emergency fallback
                await close_position(position['id'], current_price, pnl_percent, None)

                # Update user balance based on P&L
                await update_user_balance_after_hook(user_id, pnl_percent)

                return web.json_response({
                    'success': True,
                    'fish': None,
                    'result': {
                        'pnl_percent': pnl_percent,
                        'entry_price': entry_price,
                        'current_price': current_price,
                        'fishing_time_seconds': fishing_time_seconds,
                        'pond_name': pond['name'] if pond else 'Unknown Pond',
                        'rod_name': rod['name'] if rod else 'Unknown Rod'
                    },
                    'message': f'Caught something strange! P&L: {pnl_percent:+.1f}%'
                })
                
        except ValueError as e:
            return web.json_response({'error': f'Invalid data: {str(e)}'}, status=400)
        except Exception as e:
            logger.error(f"Error completing position: {e}")
            return web.json_response({
                'success': False,
                'error': 'internal_error',
                'message': str(e)
            }, status=500)
    
    async def get_crypto_price(self, request):
        """Get current cryptocurrency price"""
        try:
            symbol = request.match_info['symbol'].upper()
            
            # Validate symbol
            valid_symbols = ['TAC']
            if symbol not in valid_symbols:
                return web.json_response({'error': f'Unsupported symbol: {symbol}'}, status=400)
            
            # Get price from crypto price utility
            current_price = await get_crypto_price_util(symbol)
            
            # Return formatted price data
            return web.json_response({
                'symbol': symbol,
                'current_price': float(current_price),
                'price_change_24h': None,  # Could be enhanced to include 24h change
                'last_updated': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error getting crypto price for {symbol}: {e}")
            return web.json_response({'error': 'Price fetch failed'}, status=500)
    
    async def get_bot_info(self, request):
        """Get bot information including username"""
        try:
            # Get bot username from environment or extract from token
            import os
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            
            if not bot_token:
                return web.json_response({'error': 'Bot token not configured'}, status=500)
            
            # Extract bot ID from token (everything before first colon)
            bot_id = bot_token.split(':')[0]
            
            # Make API call to Telegram to get bot info
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"https://api.telegram.org/bot{bot_token}/getMe"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            bot_info = data.get('result', {})
                            return web.json_response({
                                'username': bot_info.get('username'),
                                'first_name': bot_info.get('first_name'),
                                'id': bot_info.get('id')
                            })
                    
                    return web.json_response({'error': 'Failed to get bot info'}, status=500)
                    
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            return web.json_response({'error': 'Internal server error'}, status=500)
    

# Global server instance
web_server = None

def create_webapp(application=None):
    """Create and return the web application"""
    global web_server
    web_server = WebAppServer(application)
    return web_server.app

async def start_web_server(port: int = 8080, application=None):
    """Start the web server"""
    try:
        webapp = create_webapp(application)
        runner = web.AppRunner(webapp)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        return runner
        
    except Exception as e:
        logger.error(f"Failed to start web server on port {port}: {e}")
        logger.exception("Full start_web_server error traceback:")
        raise