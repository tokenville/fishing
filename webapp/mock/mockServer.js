// Mock API server for development without backend
const express = require('express');
const cors = require('cors');
const path = require('path');
const { mockData, getMockFishImage } = require('./mockData');

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
app.use(express.json());

// Serve static files from webapp directory
app.use('/static', express.static(path.join(__dirname, '..', 'static')));

// Serve mock images
app.use('/mock/images', express.static(path.join(__dirname, 'images')));

// Serve main webapp page
app.get('/webapp', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'templates', 'index.html'));
});

// Serve debug page
app.get('/debug', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'debug.html'));
});

// API Routes

// Get user statistics
app.get('/api/user/:userId/stats', (req, res) => {
  const userId = parseInt(req.params.userId) || 123456789;
  const user = mockData.users[userId] || mockData.users[123456789];
  const stats = mockData.userStats[userId] || mockData.userStats[123456789];
  
  res.json({
    ...user,
    ...stats
  });
});

// Get user info
app.get('/api/user/:userId', (req, res) => {
  const userId = parseInt(req.params.userId) || 123456789;
  const user = mockData.users[userId] || mockData.users[123456789];
  
  res.json(user);
});

// Get user fish collection
app.get('/api/user/:userId/fish', (req, res) => {
  // Simulate some processing delay
  setTimeout(() => {
    const fishData = mockData.fishCollection.map(fish => ({
      ...fish,
      // Add mock CDN URLs for images
      cdn_url: getMockFishImage(fish.rarity),
      thumbnail_url: getMockFishImage(fish.rarity)
    }));
    
    // Calculate unique fish
    const uniqueFish = new Set(fishData.map(f => f.id));
    
    res.json({
      fish: fishData,
      total_unique: uniqueFish.size,
      total_caught: fishData.length
    });
  }, 300); // 300ms delay to simulate network
});

// Get user rods
app.get('/api/user/:userId/rods', (req, res) => {
  res.json(mockData.userRods);
});

// Get active rod
app.get('/api/user/:userId/active-rod', (req, res) => {
  const userId = parseInt(req.params.userId) || 123456789;
  const activeRodId = mockData.activeRod[userId] || mockData.activeRod[123456789];
  const rod = mockData.userRods.find(r => r.id === activeRodId);
  
  res.json({
    active_rod: rod || mockData.userRods[0]
  });
});

// Set active rod
app.post('/api/user/:userId/active-rod', (req, res) => {
  const userId = parseInt(req.params.userId) || 123456789;
  const { rod_id } = req.body;
  
  // Check if user owns the rod
  const rod = mockData.userRods.find(r => r.id === rod_id);
  if (!rod) {
    return res.status(400).json({ error: 'User does not own this rod' });
  }
  
  // Update active rod in mock data
  mockData.activeRod[userId] = rod_id;
  
  res.json({ success: true });
});

// Get user balance
app.get('/api/user/:userId/balance', (req, res) => {
  const userId = parseInt(req.params.userId) || 123456789;
  const balance = mockData.userBalance[userId] || mockData.userBalance[123456789];
  
  res.json(balance);
});

// Get leaderboard
app.get('/api/leaderboard', (req, res) => {
  const { type = 'all', pond_id, rod_id, user_id, limit = 10 } = req.query;
  
  // For mock, just return the predefined leaderboard
  // In real implementation, this would filter based on parameters
  const leaderboardData = { ...mockData.leaderboard };
  
  // Slice to requested limit
  if (limit) {
    leaderboardData.top = leaderboardData.top.slice(0, parseInt(limit));
  }
  
  res.json({
    top: leaderboardData.top.map((player, i) => ({
      ...player,
      user_id: player.telegram_id,
      rank: i + 1
    })),
    bottom: leaderboardData.bottom,
    user_position: leaderboardData.user_position,
    total_players: leaderboardData.total_players,
    filters: {
      time_period: type,
      pond_id: pond_id ? parseInt(pond_id) : null,
      rod_id: rod_id ? parseInt(rod_id) : null
    }
  });
});

// Get fish image
app.get('/api/fish/:fishId/image', (req, res) => {
  const fishId = parseInt(req.params.fishId);
  const { size = 'full' } = req.query;
  
  // Check if we have a generated mock image
  const imagePath = size === 'thumbnail' 
    ? `/mock/images/fish_${fishId}_thumb.png`
    : `/mock/images/fish_${fishId}.png`;
  
  // Redirect to the mock image (or placeholder if not found)
  const baseUrl = `http://localhost:${PORT}`;
  const imageUrl = `${baseUrl}${imagePath}`;
  
  // Check if file exists, otherwise use placeholder
  const fs = require('fs');
  const fullPath = path.join(__dirname, 'images', size === 'thumbnail' ? `fish_${fishId}_thumb.png` : `fish_${fishId}.png`);
  
  if (fs.existsSync(fullPath)) {
    res.redirect(imageUrl);
  } else {
    // Use placeholder
    res.redirect(`${baseUrl}/mock/images/placeholder.png`);
  }
});

// Health check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    service: 'fishing-bot-webapp-mock'
  });
});

// Root redirect to webapp
app.get('/', (req, res) => {
  res.redirect('/webapp');
});

// Start server
app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════╗
║     🎣 Mock Server Running                 ║
╠════════════════════════════════════════════╣
║                                            ║
║  Server:    http://localhost:${PORT}         ║
║  WebApp:    http://localhost:${PORT}/webapp  ║
║  API:       http://localhost:${PORT}/api     ║
║                                            ║
║  Press Ctrl+C to stop                     ║
╚════════════════════════════════════════════╝
  `);
});

module.exports = app;