// === TELEGRAM WEB APP INITIALIZATION ===
const appConfig = window.appConfig || {};
const tg = appConfig.TELEGRAM_ENABLED ? window.Telegram?.WebApp : null;

// Initialize Telegram Web App
if (tg) {
    tg.ready();
    tg.expand();
    
    // Hide main button by default
    tg.MainButton.hide();
    
    // Enable closing confirmation
    tg.enableClosingConfirmation();
}

// Log mode in development
if (appConfig.DEBUG) {
    console.log('🎣 WebApp running in', appConfig.isDevelopment ? 'DEVELOPMENT' : 'PRODUCTION', 'mode');
    console.log('API URL:', appConfig.API_BASE_URL || 'default');
}

// === GLOBAL STATE ===
let currentScreen = 'lobby';
let userData = null;
let fishCollection = [];
let userRods = [];
let fishHistory = {};
let activeRod = null;
let currentRodIndex = 0;
let userBalance = null;

// === UTILITY FUNCTIONS ===
function getUserIdFromTelegram() {
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
        return tg.initDataUnsafe.user.id;
    }
    // Fallback for testing and development
    return appConfig.DEFAULT_USER_ID || 123456789;
}

function getUsernameFromTelegram() {
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
        return tg.initDataUnsafe.user.username || tg.initDataUnsafe.user.first_name;
    }
    return appConfig.DEFAULT_USERNAME || 'Fisherman';
}

// === API FUNCTIONS ===
async function apiRequest(endpoint, options = {}) {
    try {
        const defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        // Use base URL from config
        const baseUrl = appConfig.API_BASE_URL || '';
        const url = `${baseUrl}/api${endpoint}`;
        
        if (appConfig.DEBUG) {
            console.log('API Request:', options.method || 'GET', url);
        }
        
        const response = await fetch(url, {
            ...defaultOptions,
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`API Error: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (appConfig.DEBUG) {
            console.log('API Response:', data);
        }
        
        return data;
    } catch (error) {
        console.error('API Request failed:', error);
        throw error;
    }
}

async function loadUserData() {
    try {
        const userId = getUserIdFromTelegram();
        userData = await apiRequest(`/user/${userId}/stats`);
        updatePlayerStats();
        // Load balance data
        await loadUserBalance();
    } catch (error) {
        console.error('Failed to load user data:', error);
        showError('Failed to load user data');
    }
}

async function loadUserBalance() {
    try {
        const userId = getUserIdFromTelegram();
        userBalance = await apiRequest(`/user/${userId}/balance`);
        updateBalanceDisplay();
    } catch (error) {
        console.error('Failed to load user balance:', error);
    }
}

async function loadFishCollection() {
    const grid = document.getElementById('fish-grid');
    
    // Show loading state
    if (grid) {
        grid.innerHTML = createLoadingGrid(12); // Show 12 skeleton cards
    }
    
    try {
        const userId = getUserIdFromTelegram();
        const response = await apiRequest(`/user/${userId}/fish`);
        fishCollection = response.fish || [];
        fishHistory = response.history || {};
        updateFishGrid();
        updateFishCount();
    } catch (error) {
        console.error('Failed to load fish collection:', error);
        showError('Failed to load fish collection');
    }
}

function createLoadingGrid(count) {
    let skeletons = '';
    for (let i = 0; i < count; i++) {
        skeletons += `
            <div class="fish-card">
                <div class="fish-image-container">
                    <div class="fish-image-skeleton"></div>
                </div>
                <div class="fish-card-info">
                    <div class="fish-name">Loading...</div>
                </div>
            </div>
        `;
    }
    return skeletons;
}

async function loadUserRods() {
    try {
        const userId = getUserIdFromTelegram();
        userRods = await apiRequest(`/user/${userId}/rods`);
        await loadActiveRod();
        
        // Устанавливаем текущий индекс на активную удочку
        if (activeRod) {
            const activeIndex = userRods.findIndex(rod => rod.id === activeRod.id);
            if (activeIndex !== -1) {
                currentRodIndex = activeIndex;
            }
        }
        
        updateRodSelector();
        updateRodsCount();
    } catch (error) {
        console.error('Failed to load rods:', error);
        showError('Failed to load rods');
    }
}

async function loadActiveRod() {
    try {
        const userId = getUserIdFromTelegram();
        const response = await apiRequest(`/user/${userId}/active-rod`);
        activeRod = response.active_rod;
        
        // Immediately update character visual when active rod is loaded
        updateCharacterVisual();
    } catch (error) {
        console.error('Failed to load active rod:', error);
    }
}

async function setActiveRod(rodId) {
    try {
        const userId = getUserIdFromTelegram();
        await apiRequest(`/user/${userId}/active-rod`, {
            method: 'POST',
            body: JSON.stringify({ rod_id: rodId })
        });
        
        // Update active rod state
        activeRod = userRods.find(rod => rod.id === rodId) || null;
        updateRodSelector();
        updateCharacterVisual();
        
        return true;
    } catch (error) {
        console.error('Failed to set active rod:', error);
        showError('Failed to change rod');
        return false;
    }
}

// === UI UPDATE FUNCTIONS ===
function updatePlayerStats() {
    if (!userData) return;
    
    // Безопасное обновление элементов с проверкой на существование
    const playerName = document.getElementById('player-name');
    if (playerName) playerName.textContent = getUsernameFromTelegram();
    
    const playerLevel = document.getElementById('player-level');
    if (playerLevel) playerLevel.textContent = userData.level || 1;
    
    const playerBait = document.getElementById('player-bait');
    if (playerBait) playerBait.textContent = userData.bait_tokens || 0;
    
    const bottomPlayerBait = document.getElementById('bottom-player-bait');
    if (bottomPlayerBait) bottomPlayerBait.textContent = userData.bait_tokens || 0;
    
    // Обновляем счетчики рыб и удочек из статистики
    const fishCountElement = document.getElementById('fish-count');
    if (fishCountElement) fishCountElement.textContent = userData.fish_display || '0/0';
    
    const rodsCountElement = document.getElementById('rods-count');
    if (rodsCountElement) rodsCountElement.textContent = userData.rods_count || 0;
}

function updateBalanceDisplay() {
    if (!userBalance) return;
    
    const balanceElement = document.getElementById('balance-value');
    if (balanceElement) {
        const balance = userBalance.balance || 10000;
        const formatted = new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(balance);
        
        balanceElement.textContent = formatted;
        
        // Add color class based on profit/loss
        balanceElement.classList.remove('positive', 'negative');
        if (balance > 10000) {
            balanceElement.classList.add('positive');
        } else if (balance < 10000) {
            balanceElement.classList.add('negative');
        }
    }
}

function updateFishCount() {
    // Обновляем счетчик рыб после загрузки коллекции (на случай обновления)
    if (userData && fishCollection.length > 0) {
        const uniqueFish = new Set(fishCollection.map(fish => fish.id)).size;
        const fishCountElement = document.getElementById('fish-count');
        if (fishCountElement) {
            fishCountElement.textContent = `${uniqueFish}/${userData.fish_total || 0}`;
        }
    }
}

function updateRodsCount() {
    // Обновляем счетчик удочек после загрузки (на случай обновления)
    if (userRods.length > 0) {
        const rodsCountElement = document.getElementById('rods-count');
        if (rodsCountElement) rodsCountElement.textContent = userRods.length;
    }
}

function updateFishGrid() {
    const grid = document.getElementById('fish-grid');
    
    if (!grid) return;
    
    if (fishCollection.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-animation">
                    <div class="fishing-rod">🎣</div>
                    <div class="water-ripples">
                        <div class="ripple"></div>
                        <div class="ripple"></div>
                        <div class="ripple"></div>
                    </div>
                </div>
                <h3 class="empty-state-title">Collection is Empty</h3>
                <p class="empty-state-desc">Start fishing to catch your first fish!</p>
                <button class="empty-state-btn" id="empty-state-cast-btn">
                    🎯 Cast Rod
                </button>
            </div>
        `;
        return;
    }
    
    // Add loading class to grid
    grid.classList.add('loading');
    
    // Группируем рыб по ID для подсчета количества
    const fishGroups = {};
    fishCollection.forEach(fish => {
        if (!fishGroups[fish.id]) {
            fishGroups[fish.id] = {
                ...fish,
                count: 0,
                bestPnl: -Infinity,
                trades: [],
                // Передаем CDN URLs в группу
                cdn_url: fish.cdn_url,
                thumbnail_url: fish.thumbnail_url
            };
        }
        fishGroups[fish.id].count++;
        
        // Находим лучший PnL для этой рыбы
        if (fish.pnl_percent > fishGroups[fish.id].bestPnl) {
            fishGroups[fish.id].bestPnl = fish.pnl_percent;
        }
        
        // Сохраняем CDN URLs от самой свежей рыбы
        if (fish.cdn_url && !fishGroups[fish.id].cdn_url) {
            fishGroups[fish.id].cdn_url = fish.cdn_url;
            fishGroups[fish.id].thumbnail_url = fish.thumbnail_url;
        }
        
        // Добавляем сделку в историю
        fishGroups[fish.id].trades.push({
            pnl: fish.pnl_percent,
            date: fish.caught_at,
            rod: fish.rod_name,
            pond: fish.pond_name
        });
    });
    
    grid.innerHTML = Object.values(fishGroups)
        .sort((a, b) => getRarityOrder(b.rarity) - getRarityOrder(a.rarity))
        .map(fish => createFishCard(fish))
        .join('');
    
    // Remove loading class after render
    setTimeout(() => {
        grid.classList.remove('loading');
    }, 100);
}

function createFishCard(fish) {
    const pnlClass = fish.bestPnl >= 0 ? 'profit' : 'loss';
    const pnlSign = fish.bestPnl >= 0 ? '+' : '';
    
    // Use CDN thumbnail URL if available, otherwise fallback to API
    const imageUrl = fish.thumbnail_url || fish.cdn_url || `/api/fish/${fish.id}/image?size=thumbnail`;
    
    return `
        <div class="fish-card" data-fish-id="${fish.id}">
            <div class="fish-image-container">
                <!-- Skeleton loader for image only -->
                <div class="fish-image-skeleton"></div>
                
                <!-- Actual image (hidden initially) -->
                <img src="${imageUrl}" 
                     alt="${fish.name}" 
                     class="fish-image"
                     style="opacity: 0;"
                     loading="lazy"
                     onload="handleImageLoad(this)"
                     onerror="handleImageError(this)">
                
                <!-- Emoji fallback -->
                <div class="fish-emoji-fallback" style="display: none;">${fish.emoji}</div>
                
                <!-- Плашки поверх изображения -->
                <div class="rarity-overlay rarity-${fish.rarity}">${getRarityText(fish.rarity)}</div>
                <div class="fish-best-pnl-overlay ${pnlClass}">
                    ${pnlSign}${fish.bestPnl.toFixed(1)}%
                </div>
            </div>
            
            <div class="fish-card-info">
                <div class="fish-name">${fish.name}</div>
            </div>
        </div>
    `;
}

function updateRodSelector() {
    const mainDisplay = document.getElementById('main-rod-display');
    const indicators = document.getElementById('carousel-indicators');
    const actionBtn = document.getElementById('rod-action-btn');
    const prevBtn = document.getElementById('prev-rod-btn');
    const nextBtn = document.getElementById('next-rod-btn');
    
    if (userRods.length === 0) {
        mainDisplay.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🎣</div>
                <p>No Rods</p>
                <small>Get your first rod to start fishing!</small>
            </div>
        `;
        indicators.innerHTML = '';
        actionBtn.style.display = 'none';
        prevBtn.style.display = 'none';
        nextBtn.style.display = 'none';
        return;
    }
    
    // Обновляем главный дисплей с текущей удочкой
    const currentRod = userRods[currentRodIndex];
    mainDisplay.innerHTML = createMainRodDisplay(currentRod);
    
    // Обновляем индикаторы карусели
    updateCarouselIndicators();
    
    // Обновляем кнопку действия
    updateRodActionButton(currentRod);
    
    // Показываем/скрываем стрелки навигации
    prevBtn.style.display = userRods.length > 1 ? 'flex' : 'none';
    nextBtn.style.display = userRods.length > 1 ? 'flex' : 'none';
    
    // Обновляем классы для стилей
    updateMainDisplayClasses(currentRod);
}

function createMainRodDisplay(rod) {
    const leverageDisplay = rod.leverage > 0 ? `+${rod.leverage}x` : `${rod.leverage}x`;
    const rodTypeIcon = rod.rod_type === 'long' ? '🚀' : rod.rod_type === 'short' ? '🔻' : '🎣';
    const rodTypeText = rod.rod_type === 'long' ? 'Long Position' : rod.rod_type === 'short' ? 'Short Position' : 'Position';
    
    // Пытаемся использовать SVG изображение, иначе эмодзи
    const rodType = rod.rod_type === 'long' ? 'long' : 'short';
    const baseUrl = appConfig.API_BASE_URL || '';
    const rodImageSrc = `${baseUrl}/static/images/${rodType}-rod.svg`;
    
    return `
        <div class="main-rod-icon">
            <img src="${rodImageSrc}" alt="${rod.name}" 
                 onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
            <div class="emoji-fallback" style="display: none;">${rodTypeIcon}</div>
        </div>
        <div class="main-rod-info">
            <div class="main-rod-name">${rod.name}</div>
            <div class="main-rod-type">${rodTypeText}</div>
            <div class="main-rod-leverage leverage-${rod.leverage > 0 ? 'positive' : 'negative'}">
                ${leverageDisplay} Leverage
            </div>
        </div>
    `;
}

function updateMainDisplayClasses(rod) {
    const mainDisplay = document.getElementById('main-rod-display');
    const isActive = activeRod && activeRod.id === rod.id;
    
    // Удаляем старые классы
    mainDisplay.classList.remove('rod-long', 'rod-short', 'active');
    
    // Добавляем новые классы
    if (rod.rod_type === 'long') {
        mainDisplay.classList.add('rod-long');
    } else if (rod.rod_type === 'short') {
        mainDisplay.classList.add('rod-short');
    }
    
    if (isActive) {
        mainDisplay.classList.add('active');
    }
}

function updateCarouselIndicators() {
    const indicators = document.getElementById('carousel-indicators');
    
    if (userRods.length <= 1) {
        indicators.innerHTML = '';
        return;
    }
    
    indicators.innerHTML = userRods.map((_, index) => 
        `<div class="carousel-indicator ${index === currentRodIndex ? 'active' : ''}" 
              data-rod-index="${index}"></div>`
    ).join('');
}

function updateRodActionButton(rod) {
    const actionBtn = document.getElementById('rod-action-btn');
    const isActive = activeRod && activeRod.id === rod.id;
    
    actionBtn.style.display = 'flex';
    
    if (isActive) {
        actionBtn.textContent = 'Active Rod';
        actionBtn.className = 'rod-action-btn active-rod';
    } else {
        actionBtn.textContent = 'Take This Rod';
        actionBtn.className = 'rod-action-btn select-rod';
    }
}

function selectPreviousRod() {
    if (userRods.length <= 1) return;
    
    currentRodIndex = (currentRodIndex - 1 + userRods.length) % userRods.length;
    updateRodSelector();
}

function selectNextRod() {
    if (userRods.length <= 1) return;
    
    currentRodIndex = (currentRodIndex + 1) % userRods.length;
    updateRodSelector();
}

function selectRodByIndex(index) {
    if (index < 0 || index >= userRods.length) return;
    
    currentRodIndex = index;
    updateRodSelector();
}

async function handleRodAction() {
    const currentRod = userRods[currentRodIndex];
    const isActive = activeRod && activeRod.id === currentRod.id;
    
    if (isActive) {
        // Удочка уже активна, возвращаемся на главный экран
        showMessage('This rod is already active!');
        // Возвращаемся на главный экран через короткую задержку
        setTimeout(() => {
            showScreen('lobby');
        }, 1000);
        return;
    }
    
    // Выбираем новую удочку
    const success = await setActiveRod(currentRod.id);
    if (success) {
        showMessage('Rod selected!');
        // Автоматически возвращаемся на главный экран
        setTimeout(() => {
            showScreen('lobby');
        }, 1000);
    }
}

async function selectRod(rodId) {
    // Оставляем для обратной совместимости, но используем новую логику
    const success = await setActiveRod(rodId);
    if (success) {
        // Обновляем текущий индекс если это экран с выбором удочек
        if (currentScreen === 'rods') {
            const rodIndex = userRods.findIndex(rod => rod.id === rodId);
            if (rodIndex !== -1) {
                currentRodIndex = rodIndex;
                updateRodSelector();
            }
        }
        showMessage('Rod selected!');
    }
}

function updateCharacterVisual() {
    const rodContainer = document.getElementById('character-rod');
    if (!rodContainer) return;
    
    // Clear existing rod
    rodContainer.innerHTML = '';
    
    if (activeRod && activeRod.rod_type) {
        const rodImg = document.createElement('img');
        
        // Use rod_type as fallback (long/short)
        const rodType = activeRod.rod_type === 'long' ? 'long' : 'short';
        const baseUrl = appConfig.API_BASE_URL || '';
        rodImg.src = `${baseUrl}/static/images/${rodType}-rod.svg`;
        rodImg.alt = activeRod.name;
        rodImg.className = `${rodType}-rod`;
        
        // Handle image load error with fallback
        rodImg.onerror = () => {
            console.warn(`Rod image not found: ${rodType}-rod.svg, using emoji fallback`);
            
            // Create emoji fallback
            const rodEmoji = document.createElement('div');
            rodEmoji.textContent = activeRod.rod_type === 'long' ? '🚀' : '🔻';
            rodEmoji.className = `rod-emoji-fallback ${rodType}-rod`;
            const isLong = activeRod.rod_type === 'long';
            rodEmoji.style.cssText = `
                position: absolute;
                font-size: 32px;
                top: ${isLong ? '20%' : '30%'};
                right: ${isLong ? '45%' : '47%'};
                transform: rotate(-5deg);
                filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.3));
            `;
            
            rodContainer.removeChild(rodImg);
            rodContainer.appendChild(rodEmoji);
        };
        
        rodContainer.appendChild(rodImg);
    }
}

function showMessage(text, duration = 2000) {
    // Simple toast notification
    const toast = document.createElement('div');
    toast.className = 'toast-message';
    toast.textContent = text;
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 12px 24px;
        border-radius: 20px;
        z-index: 1000;
        font-weight: 500;
    `;
    
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, duration);
}

// === SCREEN MANAGEMENT ===
function showScreen(screenName) {
    // Скрыть все экраны
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    
    // Показать нужный экран
    const targetScreen = document.getElementById(`${screenName}-screen`);
    if (targetScreen) {
        targetScreen.classList.add('active');
        currentScreen = screenName;
        
        // Загрузить данные для экрана если нужно
        loadScreenData(screenName);
        
        // Обновить заголовок Telegram WebApp
        updateTelegramTitle(screenName);
    }
}

function loadScreenData(screenName) {
    // Lazy loading: загружаем данные только при необходимости
    if (screenName === 'collection' && fishCollection.length === 0) {
        // Загружаем коллекцию рыб только при первом открытии
        loadFishCollection();
    } else if (screenName === 'rods' && userRods.length === 0) {
        // Загружаем удочки только при первом открытии
        loadUserRods();
    } else if (screenName === 'rods' && userRods.length > 0) {
        // Обновляем селектор удочек при каждом открытии экрана
        updateRodSelector();
    }
}

function updateTelegramTitle(screenName) {
    if (!tg) return;
    
    // Всегда скрываем MainButton - используем свои кнопки навигации
    tg.MainButton.hide();
}

function goToLobby() {
    showScreen('lobby');
    if (tg) {
        tg.MainButton.hide();
    }
}

// === FISH DETAILS MODAL ===
function showFishDetails(fishId) {
    const fishGroup = fishCollection
        .filter(fish => fish.id === fishId)
        .sort((a, b) => new Date(b.caught_at) - new Date(a.caught_at));
    
    if (fishGroup.length === 0) return;
    
    const fish = fishGroup[0]; // Берем самую свежую рыбу для основной информации
    
    // Use full size CDN URL for detail view
    const fullImageUrl = fish.cdn_url ? 
        fish.cdn_url.replace('width=200', 'width=800').replace('quality=80', 'quality=90') : 
        `/api/fish/${fish.id}/image?size=full`;
    
    const modalContent = document.getElementById('fish-details');
    modalContent.innerHTML = `
        <div class="fish-details-wrapper">
            <div class="fish-detail-header">
                <div class="fish-detail-image-container">
                    <img src="${fullImageUrl}" 
                         alt="${fish.name}" 
                         class="fish-detail-image"
                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <div class="fish-detail-emoji-fallback" style="display: none;">${fish.emoji}</div>
                </div>
                <div class="fish-detail-info">
                    <div class="fish-detail-name">${fish.name}</div>
                    <div class="rarity-badge rarity-${fish.rarity}">${getRarityText(fish.rarity)}</div>
                    <div class="fish-detail-description">${fish.description || ''}</div>
                </div>
            </div>
            
            <div class="fish-trades-section">
                <div class="fish-trades-title">📈 Trading History (${fishGroup.length})</div>
                <div class="fish-trades-list">
                    ${fishGroup.map(trade => createTradeItem(trade)).join('')}
                </div>
            </div>
            
            <button class="modal-close-btn" id="modal-close-btn">
                ✕ Close
            </button>
        </div>
    `;
    
    document.getElementById('fish-modal').classList.add('active');
}

function createTradeItem(trade) {
    const pnlClass = trade.pnl_percent >= 0 ? 'trade-profit' : 'trade-loss';
    const pnlSign = trade.pnl_percent >= 0 ? '+' : '';
    const date = new Date(trade.caught_at).toLocaleString('ru-RU');
    
    return `
        <div class="trade-item ${pnlClass}">
            <div class="trade-pnl">${pnlSign}${trade.pnl_percent.toFixed(1)}%</div>
            <div class="trade-date">${date}</div>
            <div class="trade-details">
                ${trade.rod_name} • ${trade.pond_name}
            </div>
        </div>
    `;
}

function closeFishModal() {
    document.getElementById('fish-modal').classList.remove('active');
}

// === TELEGRAM INTEGRATION ===
function castInTelegram() {
    if (tg) {
        // Уведомляем Telegram что пользователь хочет использовать команду
        tg.sendData(JSON.stringify({
            action: 'cast',
            userId: getUserIdFromTelegram()
        }));
        
        // Закрываем WebApp
        tg.close();
    } else {
        // Fallback для тестирования в development mode
        if (appConfig.isDevelopment) {
            showMessage('🎣 In real app, bot chat will open for fishing!', 3000);
        } else {
            alert('In real app, bot chat will open for fishing!');
        }
    }
}

// === IMAGE LOADING HELPERS ===
function handleImageLoad(img) {
    const container = img.closest('.fish-image-container');
    
    // Hide skeleton
    const skeleton = container.querySelector('.fish-image-skeleton');
    if (skeleton) {
        skeleton.style.display = 'none';
    }
    
    // Show image with fade-in
    img.style.transition = 'opacity 0.3s ease';
    img.style.opacity = '1';
    container.classList.add('image-loaded');
}

function handleImageError(img) {
    const container = img.closest('.fish-image-container');
    
    // Hide skeleton
    const skeleton = container.querySelector('.fish-image-skeleton');
    if (skeleton) {
        skeleton.style.display = 'none';
    }
    
    // Hide failed image
    img.style.display = 'none';
    
    // Show emoji fallback
    const fallback = container.querySelector('.fish-emoji-fallback');
    if (fallback) {
        fallback.style.display = 'flex';
        fallback.style.alignItems = 'center';
        fallback.style.justifyContent = 'center';
        fallback.style.width = '100%';
        fallback.style.height = '100%';
        fallback.style.fontSize = '48px';
        fallback.style.background = '#2a2a2a';
        fallback.style.position = 'absolute';
        fallback.style.top = '0';
        fallback.style.left = '0';
    }
}

// === HELPER FUNCTIONS ===
function getRarityOrder(rarity) {
    const order = { 'trash': 1, 'common': 2, 'rare': 3, 'epic': 4, 'legendary': 5 };
    return order[rarity] || 0;
}

function getRarityText(rarity) {
    const texts = {
        'trash': 'Trash',
        'common': 'Common',
        'rare': 'Rare',
        'epic': 'Epic',
        'legendary': 'Legendary'
    };
    return texts[rarity] || rarity;
}

function showError(message) {
    // В реальном приложении здесь может быть toast или другое уведомление
    console.error(message);
    
    if (tg) {
        tg.showAlert(message);
    } else if (appConfig.isDevelopment) {
        // In development, show a nicer error message
        showMessage(`❌ ${message}`, 3000);
    } else {
        alert(message);
    }
}

// === EVENT LISTENERS ===
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация приложения
    initializeApp();
    
    // Обработчики кнопок на главном экране
    document.getElementById('rods-btn').addEventListener('click', function() {
        showScreen('rods');
    });
    
    document.getElementById('collection-btn').addEventListener('click', function() {
        showScreen('collection');
    });
    
    document.getElementById('cast-btn').addEventListener('click', castInTelegram);
    
    // Кнопки "Назад"
    document.getElementById('collection-back-btn').addEventListener('click', function() {
        showScreen('lobby');
    });
    
    document.getElementById('rods-back-btn').addEventListener('click', function() {
        showScreen('lobby');
    });
    
    // Управление каруселью удочек
    document.getElementById('prev-rod-btn').addEventListener('click', selectPreviousRod);
    document.getElementById('next-rod-btn').addEventListener('click', selectNextRod);
    document.getElementById('rod-action-btn').addEventListener('click', handleRodAction);
    
    // Обработчики для динамически создаваемых элементов
    document.addEventListener('click', function(e) {
        // Карточки рыб
        if (e.target.closest('.fish-card')) {
            const fishCard = e.target.closest('.fish-card');
            const fishId = fishCard.getAttribute('data-fish-id');
            if (fishId) {
                showFishDetails(parseInt(fishId));
            }
        }
        
        // Индикаторы карусели удочек
        if (e.target.classList.contains('carousel-indicator')) {
            const rodIndex = parseInt(e.target.getAttribute('data-rod-index'));
            if (!isNaN(rodIndex)) {
                selectRodByIndex(rodIndex);
            }
        }
        
        // Кнопка закрытия модалки
        if (e.target.id === 'modal-close-btn') {
            closeFishModal();
        }
        
        // Кнопка "Забросить удочку" в пустой коллекции
        if (e.target.id === 'empty-state-cast-btn') {
            castInTelegram();
        }
    });
    
    // Закрытие модалки по клику вне её
    document.getElementById('fish-modal').addEventListener('click', function(e) {
        if (e.target === this) {
            closeFishModal();
        }
    });
    
    // Обработка кнопки назад в Telegram
    if (tg) {
        tg.onEvent('backButtonClicked', function() {
            if (currentScreen !== 'lobby') {
                goToLobby();
            } else {
                tg.close();
            }
        });
    }
});

// === APP INITIALIZATION ===
async function initializeApp() {
    try {
        // Загружаем данные пользователя и активную удочку параллельно
        // updateCharacterVisual() вызывается автоматически в loadActiveRod()
        await Promise.all([
            loadUserData(),
            loadActiveRod()
        ]);
    } catch (error) {
        console.error('Failed to initialize app:', error);
        showError('Failed to load data');
    }
}