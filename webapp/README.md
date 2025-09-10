# 🎣 Fishing Bot WebApp - Frontend Development

This directory contains the standalone Telegram Mini App for the Fishing Bot game. It's configured to run independently from the main bot server for frontend development.

## 🚀 Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Start development server
npm run dev

# 3. Open browser automatically at http://localhost:3001/webapp
```

## 📁 Project Structure

```
webapp/
├── mock/                  # Development mock server and data
│   ├── mockServer.js      # Express server with API endpoints
│   ├── mockData.js        # Sample data for development
│   └── images/            # Generated mock fish images
├── static/                # Static assets
│   ├── css/              # Stylesheets
│   │   ├── game.css      # Main game styles
│   │   └── skeleton.css  # Loading animations
│   ├── js/               # JavaScript files
│   │   ├── app.js        # Main application logic
│   │   └── config.js     # Environment configuration
│   └── images/           # Static images (rods, characters)
├── templates/            # HTML templates
│   └── index.html        # Main application page
├── package.json          # Node.js dependencies
└── README.md            # This file
```

## 🛠 Development Mode Features

### Mock Data
The development server provides realistic mock data including:
- User profile (level, experience, bait tokens)
- Fish collection with 9 different fish types
- 4 fishing rods with different leverages
- Leaderboard with 10 players
- Balance and P&L statistics

### Configuration
The app automatically detects development mode when running on `localhost` and:
- Uses mock API server at `http://localhost:3001`
- Disables Telegram WebApp integration
- Enables debug logging in console
- Shows development-friendly error messages

### Mock Images
Run the image generator to create placeholder fish images:
```bash
cd mock
python3 generate_mock_images.py
```

## 📝 Modifying Mock Data

Edit `mock/mockData.js` to customize:

### User Data
```javascript
users: {
  123456789: {
    username: 'YourName',
    level: 10,
    bait_tokens: 50
  }
}
```

### Fish Collection
```javascript
fishCollection: [
  {
    id: 1,
    name: 'Custom Fish',
    emoji: '🐠',
    rarity: 'legendary',
    pnl_percent: 200.0
  }
]
```

### Rods
```javascript
userRods: [
  {
    id: 1,
    name: 'Super Rod',
    leverage: 10.0,
    rod_type: 'long'
  }
]
```

## 🎮 Available Screens

1. **Lobby Screen** - Main character with stats and navigation
2. **Fish Collection** - Grid view of caught fish with details
3. **Rod Selection** - Carousel for choosing active fishing rod
4. **Fish Details Modal** - Detailed view with trading history

## 🔧 API Endpoints (Mock Server)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/user/:userId/stats` | GET | User statistics |
| `/api/user/:userId/fish` | GET | Fish collection |
| `/api/user/:userId/rods` | GET | User's rods |
| `/api/user/:userId/active-rod` | GET | Current active rod |
| `/api/user/:userId/active-rod` | POST | Set active rod |
| `/api/user/:userId/balance` | GET | Balance & P&L |
| `/api/leaderboard` | GET | Leaderboard data |
| `/api/fish/:fishId/image` | GET | Fish images |

## 🚦 Development Commands

```bash
# Start mock server only
npm run serve

# Start server and open browser
npm run dev

# Generate new mock images
cd mock && python3 generate_mock_images.py
```

## 🔄 Production Integration

When deploying to production:

1. The `config.js` automatically switches to production mode
2. API calls will use relative URLs (same origin)
3. Telegram WebApp integration will be enabled
4. Mock data will be disabled

No code changes needed - just deploy the files to your production server.

## 🎨 Customization Tips

### Adding New Fish
1. Add fish data to `mock/mockData.js`
2. Generate a mock image (optional)
3. Test in the collection screen

### Styling Changes
- Main styles: `static/css/game.css`
- Loading animations: `static/css/skeleton.css`
- Colors and themes use CSS variables for easy customization

### Testing Different States
- Empty collection: Clear `fishCollection` array
- No rods: Empty `userRods` array
- Different user levels: Modify `users.level`
- Various P&L scenarios: Adjust `pnl_percent` values

## 🐛 Troubleshooting

### Port Already in Use
Change the port in `mock/mockServer.js`:
```javascript
const PORT = process.env.PORT || 3002; // Change to different port
```

### Images Not Loading
1. Check if mock images are generated: `ls mock/images/`
2. Regenerate if needed: `cd mock && python3 generate_mock_images.py`
3. Verify server is serving static files correctly

### CORS Issues
The mock server has CORS enabled by default. If you still have issues, check browser console for specific CORS errors.

## 📦 Standalone Deployment

To share this webapp with another developer:

1. Copy the entire `webapp` directory
2. Share the installation instructions:
   ```bash
   cd webapp
   npm install
   npm run dev
   ```
3. The developer can work entirely offline with mock data

## 🤝 Contributing

When making changes:
1. Test in development mode first
2. Verify production mode still works
3. Update mock data if adding new features
4. Document any new API endpoints

## 📞 Support

For questions about:
- Frontend development: Check this README
- Backend integration: See main project README
- Mock data structure: Refer to `mock/mockData.js`

---

Happy coding! 🎣