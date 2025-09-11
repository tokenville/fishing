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
    get_user_virtual_balance, get_flexible_leaderboard
)

logger = logging.getLogger(__name__)

class WebAppServer:
    def __init__(self):
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
        
        # Health check
        self.app.router.add_get('/health', self.health_check)
    
    async def serve_main_page(self, request):
        """Serve the main webapp HTML page"""
        logger.debug(f"Serving main webapp page, request from: {request.remote}")
        try:
            webapp_path = Path('webapp/templates/index.html')
            logger.debug(f"Trying to serve file: {webapp_path.absolute()}")
            
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

# Global server instance
web_server = WebAppServer()

def create_webapp():
    """Create and return the web application"""
    return web_server.app

async def start_web_server(port: int = 8080):
    """Start the web server"""
    try:
        logger.debug(f"Initializing web server on port {port}")
        runner = web.AppRunner(web_server.app)
        await runner.setup()
        logger.debug("AppRunner setup completed")
        
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.debug(f"TCPSite started on 0.0.0.0:{port}")
        
        logger.info(f"Web server successfully started on port {port}")
        return runner
        
    except Exception as e:
        logger.error(f"Failed to start web server on port {port}: {e}")
        logger.exception("Full start_web_server error traceback:")
        raise