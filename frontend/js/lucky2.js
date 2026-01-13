class Lucky2Game {
    constructor(userId) {
        this.userId = userId;
        this.selectedColor = null;
        this.betAmount = 25;
        this.isSpinning = false;
        
        // Настройки цветов
        this.colors = {
            blue: {
                name: 'Синий',
                emoji: '🔵',
                chance: 60,
                multiplier: 2.0,
                color: '#1E90FF',
                degrees: 216 // 60% от 360
            },
            red: {
                name: 'Красный',
                emoji: '🔴',
                chance: 5,
                multiplier: 5.0,
                color: '#DC143C',
                degrees: 18 // 5% от 360
            },
            purple: {
                name: 'Фиолетовый',
                emoji: '🟣',
                chance: 35,
                multiplier: 2.0,
                color: '#8A2BE2',
                degrees: 126 // 35% от 360
            }
        };
        
        this.initializeElements();
        this.setupEventListeners();
        this.createWheel();
        this.updateDisplay();
    }
    
    initializeElements() {
        this.wheelElement = document.getElementById('lucky2-wheel');
        this.wheelPointer = document.getElementById('wheel-pointer');
        this.balanceElement = document.getElementById('stars-balance');
        this.betAmountElement = document.getElementById('current-bet');
        this.potentialWinElement = document.getElementById('potential-win');
        this.spinButton = document.getElementById('spin-button');
        this.resultElement = document.getElementById('spin-result');
        this.colorButtons = {
            blue: document.getElementById('color-blue'),
            red: document.getElementById('color-red'),
            purple: document.getElementById('color-purple')
        };
        
        // Создаем элементы управления ставками
        this.createBetControls();
    }
    
    createWheel() {
        if (!this.wheelElement) return;
        
        this.wheelElement.innerHTML = '';
        
        // Создаем секторы колеса
        let currentAngle = 0;
        
        // Синий сектор (60%)
        const blueSector = document.createElement('div');
        blueSector.className = 'wheel-section wheel-section-blue';
        blueSector.style.transform = `rotate(${currentAngle}deg)`;
        blueSector.style.clipPath = `polygon(50% 50%, 50% 0%, ${this.getPointOnCircle(216, 100)}%)`;
        this.wheelElement.appendChild(blueSector);
        currentAngle += 216;
        
        // Красный сектор (5%)
        const redSector = document.createElement('div');
        redSector.className = 'wheel-section wheel-section-red';
        redSector.style.transform = `rotate(${currentAngle}deg)`;
        redSector.style.clipPath = `polygon(50% 50%, 50% 0%, ${this.getPointOnCircle(18, 100)}%)`;
        this.wheelElement.appendChild(redSector);
        currentAngle += 18;
        
        // Фиолетовый сектор (35%)
        const purpleSector = document.createElement('div');
        purpleSector.className = 'wheel-section wheel-section-purple';
        purpleSector.style.transform = `rotate(${currentAngle}deg)`;
        purpleSector.style.clipPath = `polygon(50% 50%, 50% 0%, ${this.getPointOnCircle(126, 100)}%)`;
        this.wheelElement.appendChild(purpleSector);
    }
    
    getPointOnCircle(degrees, radius) {
        const radians = degrees * Math.PI / 180;
        const x = 50 + radius * Math.cos(radians);
        const y = 50 + radius * Math.sin(radians);
        return `${x}% ${y}%`;
    }
    
    createBetControls() {
        const betControls = document.getElementById('bet-controls');
        if (!betControls) return;
        
        const betAmounts = [25, 50, 100, 250, 500, 750, 1000];
        
        betAmounts.forEach(amount => {
            const button = document.createElement('button');
            button.className = 'bet-btn';
            if (amount === this.betAmount) button.classList.add('active');
            button.dataset.amount = amount;
            button.textContent = amount;
            button.addEventListener('click', () => this.setBetAmount(amount));
            betControls.appendChild(button);
        });
    }
    
    setupEventListeners() {
        // Обработчики выбора цвета
        Object.keys(this.colorButtons).forEach(color => {
            const button = this.colorButtons[color];
            if (button) {
                button.addEventListener('click', () => this.selectColor(color));
            }
        });
        
        // Кнопка спина
        if (this.spinButton) {
            this.spinButton.addEventListener('click', () => this.spin());
        }
        
        // Кнопки управления ставкой
        document.querySelectorAll('.bet-control').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.target.dataset.action;
                if (action === 'increase') {
                    this.increaseBet();
                } else if (action === 'decrease') {
                    this.decreaseBet();
                } else if (action === 'max') {
                    this.setMaxBet();
                } else if (action === 'min') {
                    this.setMinBet();
                }
            });
        });
    }
    
    selectColor(color) {
        if (!this.colors[color]) return;
        
        this.selectedColor = color;
        
        // Обновляем UI кнопок
        Object.keys(this.colorButtons).forEach(c => {
            const button = this.colorButtons[c];
            if (button) {
                button.classList.remove('selected');
                if (c === color) {
                    button.classList.add('selected');
                }
            }
        });
        
        this.updateDisplay();
    }
    
    setBetAmount(amount) {
        this.betAmount = Math.max(25, Math.min(1000, amount));
        this.updateBetControls();
        this.updateDisplay();
    }
    
    increaseBet() {
        const steps = [25, 50, 100, 250, 500, 750, 1000];
        const currentIndex = steps.indexOf(this.betAmount);
        if (currentIndex < steps.length - 1) {
            this.setBetAmount(steps[currentIndex + 1]);
        }
    }
    
    decreaseBet() {
        const steps = [25, 50, 100, 250, 500, 750, 1000];
        const currentIndex = steps.indexOf(this.betAmount);
        if (currentIndex > 0) {
            this.setBetAmount(steps[currentIndex - 1]);
        }
    }
    
    setMaxBet() {
        this.setBetAmount(1000);
    }
    
    setMinBet() {
        this.setBetAmount(25);
    }
    
    updateBetControls() {
        // Обновляем активные кнопки ставок
        document.querySelectorAll('.bet-btn').forEach(btn => {
            btn.classList.remove('active');
            if (parseInt(btn.dataset.amount) === this.betAmount) {
                btn.classList.add('active');
            }
        });
        
        // Обновляем отображение суммы ставки
        if (this.betAmountElement) {
            this.betAmountElement.textContent = this.betAmount;
        }
    }
    
    updateDisplay() {
        this.updateBetControls();
        
        // Обновляем потенциальный выигрыш
        if (this.selectedColor && this.potentialWinElement) {
            const color = this.colors[this.selectedColor];
            const potentialWin = this.betAmount * color.multiplier;
            this.potentialWinElement.textContent = potentialWin;
            this.potentialWinElement.style.color = color.color;
        }
        
        // Активируем/деактивируем кнопку спина
        if (this.spinButton) {
            this.spinButton.disabled = !this.selectedColor || this.isSpinning;
        }
    }
    
    async spin() {
        if (this.isSpinning || !this.selectedColor) return;
        
        // Проверяем баланс
        const balance = parseInt(this.balanceElement?.textContent || 0);
        if (balance < this.betAmount) {
            this.showMessage('Недостаточно stars!', 'error');
            return;
        }
        
        this.isSpinning = true;
        this.spinButton.disabled = true;
        
        // Определяем выигрышный цвет (в реальном проекте сервер определяет)
        const winningColor = this.determineWinningColor();
        const won = winningColor === this.selectedColor;
        
        // Анимация вращения колеса
        await this.animateWheel(winningColor);
        
        // Показываем результат
        this.showResult(won, winningColor);
        
        // Отправляем результат на сервер
        if (userId !== 'demo') {
            await this.sendBetResult(won, winningColor);
        }
        
        this.isSpinning = false;
        this.spinButton.disabled = false;
    }
    
    determineWinningColor() {
        // В реальном проекте сервер определяет результат
        // Здесь симуляция на основе вероятностей
        const random = Math.random() * 100;
        
        if (random <= 60) return 'blue';
        if (random <= 65) return 'red';
        return 'purple';
    }
    
    async animateWheel(winningColor) {
        if (!this.wheelElement) return;
        
        // Определяем угол для выигрышного цвета
        let targetAngle = 0;
        switch(winningColor) {
            case 'blue':
                targetAngle = Math.random() * 216; // 0-216 градусов
                break;
            case 'red':
                targetAngle = 216 + Math.random() * 18; // 216-234 градуса
                break;
            case 'purple':
                targetAngle = 234 + Math.random() * 126; // 234-360 градусов
                break;
        }
        
        // Добавляем несколько полных оборотов
        const fullRotations = 5;
        const totalRotation = (fullRotations * 360) + targetAngle;
        
        // Анимация вращения
        this.wheelElement.style.transition = 'transform 3s cubic-bezier(0.2, 0.8, 0.3, 1)';
        this.wheelElement.style.transform = `rotate(${totalRotation}deg)`;
        
        // Ждем окончания анимации
        return new Promise(resolve => {
            setTimeout(resolve, 3000);
        });
    }
    
    showResult(won, winningColor) {
        if (!this.resultElement) return;
        
        const color = this.colors[winningColor];
        const selectedColor = this.colors[this.selectedColor];
        
        if (won) {
            // Победа
            const winAmount = this.betAmount * selectedColor.multiplier;
            
            this.resultElement.innerHTML = `
                <div class="result-win">
                    <div class="result-icon">🎉</div>
                    <div class="result-title">ПОБЕДА!</div>
                    <div class="result-color" style="color: ${selectedColor.color}">
                        ${selectedColor.emoji} ${selectedColor.name}
                    </div>
                    <div class="result-multiplier">${selectedColor.multiplier}x</div>
                    <div class="result-amount">Выигрыш: ${winAmount} stars</div>
                    <div class="result-message">Выпал цвет: ${color.emoji} ${color.name}</div>
                </div>
            `;
            
            this.resultElement.className = 'result win-animation';
            
            // Обновляем баланс
            this.updateBalance(winAmount - this.betAmount);
            
        } else {
            // Проигрыш
            this.resultElement.innerHTML = `
                <div class="result-lose">
                    <div class="result-icon">😔</div>
                    <div class="result-title">ПРОИГРЫШ</div>
                    <div class="result-color" style="color: ${selectedColor.color}">
                        Вы ставили на: ${selectedColor.emoji} ${selectedColor.name}
                    </div>
                    <div class="result-message">Выпал цвет: ${color.emoji} ${color.name}</div>
                    <div class="result-lose-amount">Потеряно: ${this.betAmount} stars</div>
                </div>
            `;
            
            this.resultElement.className = 'result lose-animation';
            
            // Обновляем баланс (минус ставка)
            this.updateBalance(-this.betAmount);
        }
        
        // Показываем результат
        this.resultElement.classList.add('show');
        
        // Скрываем через 3 секунды
        setTimeout(() => {
            this.resultElement.classList.remove('show');
        }, 3000);
    }
    
    async sendBetResult(won, winningColor) {
        const payload = {
            action: 'lucky2_bet',
            user_id: this.userId,
            color: this.selectedColor,
            amount: this.betAmount,
            won: won,
            winning_color: winningColor,
            timestamp: Date.now()
        };
        
        // Используем Telegram Web App API
        if (window.Telegram && window.Telegram.WebApp) {
            window.Telegram.WebApp.sendData(JSON.stringify(payload));
        }
        
        // В реальном проекте здесь будет fetch запрос к вашему API
        try {
            const response = await fetch('/api/lucky2/bet', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });
            
            const data = await response.json();
            
            if (data.success && data.new_balance !== undefined) {
                this.balanceElement.textContent = data.new_balance;
            }
            
        } catch (error) {
            console.error('Ошибка отправки ставки:', error);
        }
    }
    
    updateBalance(change) {
        const currentBalance = parseInt(this.balanceElement.textContent || 0);
        const newBalance = Math.max(0, currentBalance + change);
        this.balanceElement.textContent = newBalance;
        return newBalance;
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

// Инициализация игры
document.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('user_id') || localStorage.getItem('casino_user_id') || 'demo';
    
    localStorage.setItem('casino_user_id', userId);
    
    window.lucky2Game = new Lucky2Game(userId);
    
    // Загружаем баланс
    loadUserBalance(userId);
});

async function loadUserBalance(userId) {
    try {
        const balanceElement = document.getElementById('stars-balance');
        if (balanceElement && userId === 'demo') {
            balanceElement.textContent = '1000'; // Демо баланс
        } else if (balanceElement) {
            // Запрос к API для получения реального баланса
            const response = await fetch(`/api/user/balance?user_id=${userId}`);
            const data = await response.json();
            if (data.success) {
                balanceElement.textContent = data.balance;
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки баланса:', error);
    }
}
