class MonoGame {
    constructor(userId) {
        this.userId = userId;
        this.currentChance = 1;
        this.betAmount = 1;
        this.isSpinning = false;
        
        // Настройки шансов и множителей
        this.chanceSettings = [
            { chance: 1, multiplier: 100.0, color: '#FF0000', label: '1% - 100x' },
            { chance: 3, multiplier: 33.0, color: '#FF4500', label: '3% - 33x' },
            { chance: 5, multiplier: 20.0, color: '#FF8C00', label: '5% - 20x' },
            { chance: 7, multiplier: 14.3, color: '#FFD700', label: '7% - 14.3x' },
            { chance: 10, multiplier: 10.0, color: '#ADFF2F', label: '10% - 10x' },
            { chance: 15, multiplier: 6.67, color: '#32CD32', label: '15% - 6.67x' },
            { chance: 20, multiplier: 5.0, color: '#00FA9A', label: '20% - 5x' },
            { chance: 25, multiplier: 4.0, color: '#00CED1', label: '25% - 4x' },
            { chance: 30, multiplier: 3.33, color: '#1E90FF', label: '30% - 3.33x' },
            { chance: 40, multiplier: 2.5, color: '#4169E1', label: '40% - 2.5x' },
            { chance: 50, multiplier: 2.0, color: '#8A2BE2', label: '50% - 2x' },
            { chance: 65, multiplier: 1.54, color: '#DA70D6', label: '65% - 1.54x' }
        ];
        
        this.initializeElements();
        this.setupEventListeners();
        this.updateDisplay();
    }
    
    initializeElements() {
        this.slider = document.getElementById('mono-slider');
        this.currentChanceElement = document.getElementById('current-chance');
        this.currentMultiplierElement = document.getElementById('current-multiplier');
        this.betAmountElement = document.getElementById('bet-amount');
        this.balanceElement = document.getElementById('spins-balance');
        this.spinButton = document.getElementById('spin-button');
        this.resultElement = document.getElementById('spin-result');
        this.wheelElement = document.getElementById('mono-wheel');
        this.winAmountElement = document.getElementById('win-amount');
        this.winAnimation = document.getElementById('win-animation');
        this.loseAnimation = document.getElementById('lose-animation');
        
        // Создаем элементы колеса
        this.createWheel();
    }
    
    createWheel() {
        if (!this.wheelElement) return;
        
        // Очищаем колесо
        this.wheelElement.innerHTML = '';
        
        // Создаем секторы (зеленый и красный)
        const totalSectors = 100;
        const winSectors = Math.floor((this.currentChance / 100) * totalSectors);
        
        for (let i = 0; i < totalSectors; i++) {
            const sector = document.createElement('div');
            sector.className = 'wheel-sector';
            sector.style.transform = `rotate(${i * 3.6}deg)`;
            sector.style.clipPath = 'polygon(50% 50%, 50% 0%, 100% 0%)';
            sector.style.backgroundColor = i < winSectors ? '#32CD32' : '#DC143C';
            this.wheelElement.appendChild(sector);
        }
        
        // Добавляем указатель
        const pointer = document.createElement('div');
        pointer.className = 'wheel-pointer';
        this.wheelElement.appendChild(pointer);
    }
    
    setupEventListeners() {
        if (this.slider) {
            this.slider.addEventListener('input', (e) => {
                this.onSliderChange(e.target.value);
            });
            
            // Инициализируем положение слайдера
            this.slider.value = this.currentChance;
        }
        
        if (this.spinButton) {
            this.spinButton.addEventListener('click', () => {
                this.spin();
            });
        }
        
        // Кнопки ставок
        document.querySelectorAll('.bet-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const amount = parseInt(e.target.dataset.amount);
                this.setBetAmount(amount);
            });
        });
    }
    
    onSliderChange(value) {
        // Находим ближайший допустимый шанс
        const closest = this.chanceSettings.reduce((prev, curr) => {
            return Math.abs(curr.chance - value) < Math.abs(prev.chance - value) ? curr : prev;
        });
        
        this.currentChance = closest.chance;
        this.slider.value = this.currentChance;
        this.updateDisplay();
    }
    
    setBetAmount(amount) {
        this.betAmount = amount;
        
        // Обновляем активную кнопку
        document.querySelectorAll('.bet-btn').forEach(btn => {
            btn.classList.remove('active');
            if (parseInt(btn.dataset.amount) === amount) {
                btn.classList.add('active');
            }
        });
        
        this.updateBetDisplay();
    }
    
    updateDisplay() {
        if (this.currentChanceElement) {
            this.currentChanceElement.textContent = `${this.currentChance}%`;
        }
        
        const setting = this.chanceSettings.find(s => s.chance === this.currentChance);
        if (this.currentMultiplierElement && setting) {
            this.currentMultiplierElement.textContent = `${setting.multiplier.toFixed(2)}x`;
            this.currentMultiplierElement.style.color = setting.color;
        }
        
        // Обновляем колесо
        this.createWheel();
        this.updateBetDisplay();
    }
    
    updateBetDisplay() {
        if (this.betAmountElement) {
            this.betAmountElement.textContent = this.betAmount;
        }
        
        const setting = this.chanceSettings.find(s => s.chance === this.currentChance);
        if (setting && this.winAmountElement) {
            const potentialWin = this.betAmount * setting.multiplier;
            this.winAmountElement.textContent = `Потенциальный выигрыш: ${potentialWin.toFixed(2)} спинов`;
        }
    }
    
    async spin() {
        if (this.isSpinning) return;
        
        // Проверяем баланс
        const balance = parseInt(this.balanceElement?.textContent || 0);
        if (balance < this.betAmount) {
            this.showMessage('Недостаточно спинов!', 'error');
            return;
        }
        
        this.isSpinning = true;
        this.spinButton.disabled = true;
        
        // Показываем анимацию вращения
        this.wheelElement.classList.add('spinning');
        
        // Симулируем вращение
        const spinDuration = 2000 + Math.random() * 1000;
        const finalRotation = 720 + Math.random() * 360;
        
        this.wheelElement.style.transition = `transform ${spinDuration}ms cubic-bezier(0.2, 0.8, 0.3, 1)`;
        this.wheelElement.style.transform = `rotate(${finalRotation}deg)`;
        
        // Отправляем запрос на сервер
        try {
            const response = await this.sendSpinRequest();
            
            // Ждем окончания анимации
            setTimeout(() => {
                this.wheelElement.classList.remove('spinning');
                this.showResult(response);
                this.isSpinning = false;
                this.spinButton.disabled = false;
            }, spinDuration);
            
        } catch (error) {
            console.error('Ошибка спина:', error);
            this.showMessage('Ошибка при выполнении спина', 'error');
            this.isSpinning = false;
            this.spinButton.disabled = false;
            this.wheelElement.classList.remove('spinning');
        }
    }
    
    async sendSpinRequest() {
        // В реальном проекте здесь будет запрос к вашему бэкенду
        const payload = {
            action: 'mono_spin',
            user_id: this.userId,
            chance: this.currentChance,
            bet_amount: this.betAmount,
            timestamp: Date.now()
        };
        
        // Используем Telegram Web App API для отправки данных
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.sendData(JSON.stringify(payload));
            
            // В демо-режиме симулируем ответ
            return this.simulateSpinResult();
        } else {
            // Fallback для разработки
            return this.simulateSpinResult();
        }
    }
    
    simulateSpinResult() {
        // Симуляция результата (в реальном проекте сервер определяет)
        const winNumber = Math.floor(Math.random() * 100) + 1;
        const won = winNumber <= this.currentChance;
        
        const setting = this.chanceSettings.find(s => s.chance === this.currentChance);
        const winMultiplier = won ? setting.multiplier : 0;
        const winAmount = won ? this.betAmount * winMultiplier : 0;
        
        // Симуляция NFT (0.5% шанс при победе)
        let nftAwarded = null;
        if (won && Math.random() < 0.005) {
            nftAwarded = {
                id: Math.floor(Math.random() * 1000),
                name: 'Демо NFT',
                rarity: 'common'
            };
        }
        
        return {
            success: true,
            won,
            chance: this.currentChance,
            win_number: winNumber,
            multiplier: winMultiplier,
            win_amount: winAmount,
            nft_awarded: nftAwarded,
            balance: this.updateBalance(winAmount - (won ? 0 : this.betAmount))
        };
    }
    
    updateBalance(change) {
        // Обновляем баланс в UI
        const currentBalance = parseInt(this.balanceElement.textContent || 0);
        const newBalance = Math.max(0, currentBalance + change);
        this.balanceElement.textContent = newBalance;
        return newBalance;
    }
    
    showResult(result) {
        if (!this.resultElement) return;
        
        if (result.won) {
            // Победа
            this.resultElement.innerHTML = `
                <div class="result-win">
                    <div class="result-icon">🎉</div>
                    <div class="result-title">ПОБЕДА!</div>
                    <div class="result-multiplier">${result.multiplier.toFixed(2)}x</div>
                    <div class="result-amount">Выигрыш: ${result.win_amount.toFixed(2)} спинов</div>
                    ${result.nft_awarded ? 
                        `<div class="result-nft">🎁 Получен NFT: ${result.nft_awarded.name}</div>` : 
                        ''
                    }
                </div>
            `;
            
            this.resultElement.className = 'result win-animation';
            this.winAnimation?.classList.add('show');
            
            // Скрываем анимацию через 2 секунды
            setTimeout(() => {
                this.winAnimation?.classList.remove('show');
            }, 2000);
            
        } else {
            // Проигрыш
            this.resultElement.innerHTML = `
                <div class="result-lose">
                    <div class="result-icon">😔</div>
                    <div class="result-title">ПРОИГРЫШ</div>
                    <div class="result-message">Повезет в следующий раз!</div>
                    <div class="result-chance">Выпало число: ${result.win_number}</div>
                </div>
            `;
            
            this.resultElement.className = 'result lose-animation';
            this.loseAnimation?.classList.add('show');
            
            setTimeout(() => {
                this.loseAnimation?.classList.remove('show');
            }, 2000);
        }
        
        // Показываем результат на 3 секунды
        this.resultElement.classList.add('show');
        setTimeout(() => {
            this.resultElement.classList.remove('show');
        }, 3000);
    }
    
    showMessage(text, type = 'info') {
        // Создаем элемент сообщения
        const message = document.createElement('div');
        message.className = `message message-${type}`;
        message.textContent = text;
        
        // Добавляем в контейнер
        const container = document.getElementById('messages-container') || document.body;
        container.appendChild(message);
        
        // Удаляем через 3 секунды
        setTimeout(() => {
            message.remove();
        }, 3000);
    }
}

// Инициализация игры при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Получаем user_id из URL или localStorage
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('user_id') || localStorage.getItem('casino_user_id') || 'demo';
    
    // Сохраняем user_id для будущих запросов
    localStorage.setItem('casino_user_id', userId);
    
    // Инициализируем игру
    window.monoGame = new MonoGame(userId);
    
    // Загружаем баланс
    loadUserBalance(userId);
});

async function loadUserBalance(userId) {
    try {
        // В реальном проекте здесь будет запрос к API
        // Для демо используем фиктивные данные
        const balanceElement = document.getElementById('spins-balance');
        if (balanceElement && userId === 'demo') {
            balanceElement.textContent = '10'; // Демо баланс
        }
    } catch (error) {
        console.error('Ошибка загрузки баланса:', error);
    }
}
