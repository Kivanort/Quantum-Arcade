class InventorySystem {
    constructor(userId) {
        this.userId = userId;
        this.inventory = {
            nfts: [],
            boosters: [],
            collectibles: [],
            currency: { stars: 0, spins: 0 },
            totalValue: 0
        };
        
        this.currentCategory = 'all';
        this.sortBy = 'rarity';
        
        this.initializeElements();
        this.loadInventory();
        this.setupEventListeners();
    }
    
    initializeElements() {
        this.inventoryGrid = document.getElementById('inventory-grid');
        this.categoryTabs = document.getElementById('category-tabs');
        this.sortSelect = document.getElementById('sort-select');
        this.totalValueElement = document.getElementById('total-value');
        this.totalItemsElement = document.getElementById('total-items');
        this.nftCountElement = document.getElementById('nft-count');
        this.rarityStats = document.getElementById('rarity-stats');
        
        // Создаем категории
        this.createCategories();
    }
    
    createCategories() {
        const categories = [
            { id: 'all', name: 'Все', emoji: '📦' },
            { id: 'nfts', name: 'NFT', emoji: '🎁' },
            { id: 'boosters', name: 'Бусты', emoji: '⚡' },
            { id: 'currency', name: 'Валюта', emoji: '💰' },
            { id: 'collectibles', name: 'Коллекции', emoji: '🏆' }
        ];
        
        categories.forEach(category => {
            const tab = document.createElement('button');
            tab.className = 'category-tab';
            tab.dataset.category = category.id;
            tab.innerHTML = `
                <span class="tab-emoji">${category.emoji}</span>
                <span class="tab-name">${category.name}</span>
            `;
            
            tab.addEventListener('click', () => this.selectCategory(category.id));
            this.categoryTabs.appendChild(tab);
        });
    }
    
    setupEventListeners() {
        if (this.sortSelect) {
            this.sortSelect.addEventListener('change', (e) => {
                this.sortBy = e.target.value;
                this.renderInventory();
            });
        }
        
        // Поиск
        const searchInput = document.getElementById('inventory-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchItems(e.target.value);
            });
        }
    }
    
    selectCategory(category) {
        this.currentCategory = category;
        
        // Обновляем активную вкладку
        document.querySelectorAll('.category-tab').forEach(tab => {
            tab.classList.remove('active');
            if (tab.dataset.category === category) {
                tab.classList.add('active');
            }
        });
        
        this.renderInventory();
    }
    
    async loadInventory() {
        try {
            // В реальном проекте - запрос к API
            if (this.userId === 'demo') {
                this.loadDemoInventory();
            } else {
                await this.loadUserInventory();
            }
            
            this.renderInventory();
            this.updateStats();
            
        } catch (error) {
            console.error('Ошибка загрузки инвентаря:', error);
            this.showMessage('Ошибка загрузки инвентаря', 'error');
        }
    }
    
    loadDemoInventory() {
        // Демо данные
        this.inventory = {
            nfts: [
                { id: 1, name: 'Бронзовый жетон', rarity: 'common', value: 10, emoji: '🥉', color: '#CD7F32', feature: 'Базовая награда' },
                { id: 2, name: 'Серебряная монета', rarity: 'common', value: 25, emoji: '🪙', color: '#C0C0C0', feature: '+5% к удаче' },
                { id: 3, name: 'Золотой слиток', rarity: 'common', value: 50, emoji: '🪙', color: '#FFD700', feature: '+10% к выигрышу' },
                { id: 4, name: 'Рубин удачи', rarity: 'rare', value: 100, emoji: '🔴', color: '#DC143C', feature: 'Шанс x2 в Моно' },
                { id: 5, name: 'Сапфир везения', rarity: 'rare', value: 150, emoji: '🔵', color: '#1E90FF', feature: '+1 спин в Рулетке' },
                { id: 10, name: 'Корона казино', rarity: 'legendary', value: 5000, emoji: '👑', color: '#FFD700', feature: 'Пожизненный VIP' }
            ],
            boosters: [
                { id: 1, type: 'luck_boost', name: 'Буст удачи', value: 10, emoji: '🍀', expires: '2024-12-31' },
                { id: 2, type: 'win_boost', name: 'Буст выигрыша', value: 15, emoji: '💰', expires: '2024-12-31' }
            ],
            collectibles: [
                { id: 1, name: 'Трофей новичка', type: 'trophy', emoji: '🏆', rarity: 'common' }
            ],
            currency: { stars: 1250, spins: 15 },
            totalValue: 6585
        };
    }
    
    async loadUserInventory() {
        // Запрос к вашему API
        try {
            const response = await fetch(`/api/inventory?user_id=${this.userId}`);
            const data = await response.json();
            
            if (data.success) {
                this.inventory = data.inventory;
            }
        } catch (error) {
            throw error;
        }
    }
    
    renderInventory() {
        if (!this.inventoryGrid) return;
        
        this.inventoryGrid.innerHTML = '';
        
        let items = [];
        
        // Фильтруем по категории
        switch (this.currentCategory) {
            case 'nfts':
                items = this.inventory.nfts;
                break;
            case 'boosters':
                items = this.inventory.boosters;
                break;
            case 'collectibles':
                items = this.inventory.collectibles;
                break;
            case 'currency':
                this.renderCurrency();
                return;
            case 'all':
                items = [
                    ...this.inventory.nfts,
                    ...this.inventory.boosters,
                    ...this.inventory.collectibles
                ];
                break;
        }
        
        // Сортируем
        items = this.sortItems(items);
        
        // Отображаем
        if (items.length === 0) {
            this.inventoryGrid.innerHTML = `
                <div class="empty-inventory">
                    <div class="empty-icon">📭</div>
                    <div class="empty-title">Инвентарь пуст</div>
                    <div class="empty-message">Здесь будут отображаться ваши предметы</div>
                </div>
            `;
            return;
        }
        
        items.forEach(item => {
            const itemElement = this.createItemElement(item);
            this.inventoryGrid.appendChild(itemElement);
        });
    }
    
    renderCurrency() {
        this.inventoryGrid.innerHTML = '';
        
        const currencyItems = [
            {
                emoji: '⭐',
                name: 'Stars',
                amount: this.inventory.currency.stars,
                value: `${this.inventory.currency.stars} stars`,
                color: '#FFD700',
                action: 'buy'
            },
            {
                emoji: '🎰',
                name: 'Спины',
                amount: this.inventory.currency.spins,
                value: `${this.inventory.currency.spins} шт.`,
                color: '#8A2BE2',
                action: 'buy'
            }
        ];
        
        currencyItems.forEach(currency => {
            const item = document.createElement('div');
            item.className = 'inventory-item currency-item';
            item.style.borderColor = currency.color;
            
            item.innerHTML = `
                <div class="currency-emoji">${currency.emoji}</div>
                <div class="currency-name">${currency.name}</div>
                <div class="currency-amount">${currency.amount}</div>
                <div class="currency-value">${currency.value}</div>
                ${currency.action === 'buy' ? 
                    `<button class="btn btn-small btn-outline mt-2" data-action="buy-${currency.name.toLowerCase()}">
                        Купить
                    </button>` : 
                    ''
                }
            `;
            
            this.inventoryGrid.appendChild(item);
        });
    }
    
    createItemElement(item) {
        const element = document.createElement('div');
        element.className = `inventory-item ${item.rarity || item.type}`;
        
        // Определяем иконку редкости
        const rarityIcon = this.getRarityIcon(item.rarity);
        const rarityClass = item.rarity || 'common';
        
        element.innerHTML = `
            <div class="inventory-item-header">
                <span class="item-emoji">${item.emoji || '📦'}</span>
                ${rarityIcon ? `<span class="rarity-icon">${rarityIcon}</span>` : ''}
            </div>
            <div class="inventory-item-name">${item.name}</div>
            ${item.rarity ? `<div class="inventory-item-rarity ${rarityClass}">${this.getRarityName(item.rarity)}</div>` : ''}
            ${item.value ? `<div class="inventory-item-value">${item.value} stars</div>` : ''}
            ${item.feature ? `<div class="inventory-item-feature">${item.feature}</div>` : ''}
            <div class="inventory-item-actions">
                <button class="btn btn-small btn-outline" data-action="view" data-id="${item.id}">
                    Посмотреть
                </button>
            </div>
        `;
        
        // Обработчик просмотра
        element.querySelector('[data-action="view"]').addEventListener('click', () => {
            this.viewItem(item);
        });
        
        return element;
    }
    
    sortItems(items) {
        return [...items].sort((a, b) => {
            switch (this.sortBy) {
                case 'rarity':
                    const rarityOrder = { legendary: 0, epic: 1, rare: 2, common: 3 };
                    const aRarity = rarityOrder[a.rarity] || 4;
                    const bRarity = rarityOrder[b.rarity] || 4;
                    return aRarity - bRarity;
                    
                case 'value':
                    return (b.value || 0) - (a.value || 0);
                    
                case 'name':
                    return a.name.localeCompare(b.name);
                    
                case 'newest':
                    return b.id - a.id;
                    
                default:
                    return 0;
            }
        });
    }
    
    searchItems(query) {
        if (!query.trim()) {
            this.renderInventory();
            return;
        }
        
        const searchTerm = query.toLowerCase();
        let filteredItems = [];
        
        // Ищем во всех категориях
        if (this.currentCategory === 'all' || this.currentCategory === 'nfts') {
            filteredItems = filteredItems.concat(
                this.inventory.nfts.filter(item => 
                    item.name.toLowerCase().includes(searchTerm) ||
                    (item.feature && item.feature.toLowerCase().includes(searchTerm)) ||
                    (item.rarity && item.rarity.toLowerCase().includes(searchTerm))
                )
            );
        }
        
        if (this.currentCategory === 'all' || this.currentCategory === 'boosters') {
            filteredItems = filteredItems.concat(
                this.inventory.boosters.filter(item => 
                    item.name.toLowerCase().includes(searchTerm) ||
                    item.type.toLowerCase().includes(searchTerm)
                )
            );
        }
        
        // Отображаем результаты
        this.renderSearchResults(filteredItems);
    }
    
    renderSearchResults(items) {
        if (!this.inventoryGrid) return;
        
        this.inventoryGrid.innerHTML = '';
        
        if (items.length === 0) {
            this.inventoryGrid.innerHTML = `
                <div class="empty-inventory">
                    <div class="empty-icon">🔍</div>
                    <div class="empty-title">Ничего не найдено</div>
                    <div class="empty-message">Попробуйте другой запрос</div>
                </div>
            `;
            return;
        }
        
        items.forEach(item => {
            const itemElement = this.createItemElement(item);
            this.inventoryGrid.appendChild(itemElement);
        });
    }
    
    viewItem(item) {
        // Создаем модальное окно с информацией о предмете
        const modal = this.createItemModal(item);
        document.body.appendChild(modal);
    }
    
    createItemModal(item) {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        
        const rarityName = this.getRarityName(item.rarity);
        const rarityColor = this.getRarityColor(item.rarity);
        
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2 class="modal-title">${item.name}</h2>
                    <button class="modal-close">&times;</button>
                </div>
                
                <div class="item-modal-content">
                    <div class="item-modal-image" style="background: ${rarityColor}">
                        <span class="item-modal-emoji">${item.emoji || '📦'}</span>
                    </div>
                    
                    <div class="item-modal-info">
                        ${item.rarity ? `
                            <div class="item-modal-rarity" style="color: ${rarityColor}">
                                ${this.getRarityIcon(item.rarity)} ${rarityName}
                            </div>
                        ` : ''}
                        
                        ${item.value ? `
                            <div class="item-modal-value">
                                <span>Стоимость:</span>
                                <strong>${item.value} stars</strong>
                            </div>
                        ` : ''}
                        
                        ${item.feature ? `
                            <div class="item-modal-feature">
                                <h4>Особенность:</h4>
                                <p>${item.feature}</p>
                            </div>
                        ` : ''}
                        
                        <div class="item-modal-id">
                            <span>ID:</span>
                            <code>#${item.id.toString().padStart(4, '0')}</code>
                        </div>
                    </div>
                    
                    <div class="item-modal-actions">
                        ${this.canUseItem(item) ? `
                            <button class="btn btn-primary" data-action="use">
                                Использовать
                            </button>
                        ` : ''}
                        
                        ${this.canSellItem(item) ? `
                            <button class="btn btn-outline" data-action="sell">
                                Продать за ${Math.floor(item.value * 0.7)} stars
                            </button>
                        ` : ''}
                        
                        ${this.canTradeItem(item) ? `
                            <button class="btn btn-outline" data-action="trade">
                                Обменять
                            </button>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
        
        // Обработчики событий
        modal.querySelector('.modal-close').addEventListener('click', () => {
            modal.remove();
        });
        
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
        
        // Обработчики действий
        const useBtn = modal.querySelector('[data-action="use"]');
        if (useBtn) {
            useBtn.addEventListener('click', () => this.useItem(item));
        }
        
        const sellBtn = modal.querySelector('[data-action="sell"]');
        if (sellBtn) {
            sellBtn.addEventListener('click', () => this.sellItem(item));
        }
        
        return modal;
    }
    
    canUseItem(item) {
        return item.type === 'booster' || item.type === 'consumable';
    }
    
    canSellItem(item) {
        return item.value && item.value > 0 && item.rarity !== 'legendary';
    }
    
    canTradeItem(item) {
        return item.rarity && item.rarity !== 'common';
    }
    
    async useItem(item) {
        if (item.type === 'booster') {
            await this.useBooster(item);
        }
        
        // Обновляем инвентарь
        await this.loadInventory();
        this.showMessage(`${item.name} использован`, 'success');
    }
    
    async useBooster(booster) {
        // Отправляем запрос на использование буста
        try {
            const response = await fetch('/api/booster/use', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    booster_id: booster.id
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.showMessage(`Буст "${booster.name}" активирован!`, 'success');
            }
        } catch (error) {
            console.error('Ошибка использования буста:', error);
            this.showMessage('Ошибка использования буста', 'error');
        }
    }
    
    async sellItem(item) {
        const sellPrice = Math.floor(item.value * 0.7);
        const confirmed = confirm(`Продать "${item.name}" за ${sellPrice} stars?`);
        
        if (!confirmed) return;
        
        try {
            const response = await fetch('/api/inventory/sell', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: this.userId,
                    item_id: item.id,
                    item_type: 'nft'
                })
            });
            
            const data = await response.json();
            if (data.success) {
                this.showMessage(`Предмет продан за ${sellPrice} stars`, 'success');
                await this.loadInventory();
            }
        } catch (error) {
            console.error('Ошибка продажи предмета:', error);
            this.showMessage('Ошибка продажи предмета', 'error');
        }
    }
    
    updateStats() {
        // Общая стоимость
        if (this.totalValueElement) {
            this.totalValueElement.textContent = this.inventory.totalValue;
        }
        
        // Количество предметов
        const totalItems = 
            this.inventory.nfts.length + 
            this.inventory.boosters.length + 
            this.inventory.collectibles.length;
        
        if (this.totalItemsElement) {
            this.totalItemsElement.textContent = totalItems;
        }
        
        // Количество NFT
        if (this.nftCountElement) {
            this.nftCountElement.textContent = this.inventory.nfts.length;
        }
        
        // Статистика по редкости
        if (this.rarityStats) {
            const rarityCounts = {
                legendary: 0,
                epic: 0,
                rare: 0,
                common: 0
            };
            
            this.inventory.nfts.forEach(nft => {
                if (rarityCounts.hasOwnProperty(nft.rarity)) {
                    rarityCounts[nft.rarity]++;
                }
            });
            
            this.rarityStats.innerHTML = `
                <div class="rarity-stat">
                    <span class="rarity-icon legendary">👑</span>
                    <span class="rarity-count">${rarityCounts.legendary}</span>
                </div>
                <div class="rarity-stat">
                    <span class="rarity-icon epic">💎</span>
                    <span class="rarity-count">${rarityCounts.epic}</span>
                </div>
                <div class="rarity-stat">
                    <span class="rarity-icon rare">🥇</span>
                    <span class="rarity-count">${rarityCounts.rare}</span>
                </div>
                <div class="rarity-stat">
                    <span class="rarity-icon common">🔹</span>
                    <span class="rarity-count">${rarityCounts.common}</span>
                </div>
            `;
        }
    }
    
    getRarityIcon(rarity) {
        const icons = {
            legendary: '👑',
            epic: '💎',
            rare: '🥇',
            common: '🔹'
        };
        return icons[rarity] || '📦';
    }
    
    getRarityName(rarity) {
        const names = {
            legendary: 'Легендарный',
            epic: 'Эпический',
            rare: 'Редкий',
            common: 'Обычный'
        };
        return names[rarity] || 'Обычный';
    }
    
    getRarityColor(rarity) {
        const colors = {
            legendary: '#FFD700',
            epic: '#8A2BE2',
            rare: '#DC143C',
            common: '#1E90FF'
        };
        return colors[rarity] || '#808099';
    }
    
    showMessage(text, type = 'info') {
        const message = document.createElement('div');
        message.className = `message message-${type}`;
        message.textContent = text;
        
        document.body.appendChild(message);
        
        setTimeout(() => {
            message.remove();
        }, 3000);
    }
}

// Инициализация инвентаря
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('user_id') || localStorage.getItem('casino_user_id') || 'demo';
    
    localStorage.setItem('casino_user_id', userId);
    
    window.inventorySystem = new InventorySystem(userId);
});
