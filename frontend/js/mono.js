class MonoGame {
    constructor(userId) {
        this.userId = userId;
        this.currentChance = 1;
        this.currentBetSpins = 1;
        this.isSpinning = false;
        
        // ОБНОВЛЕНО: Настройки шансов с минимальными ставками
        this.chanceSettings = [
            { chance: 1, multiplier: 100.0, minBetStars: 4, color: '#FF0000' },
            { chance: 3, multiplier: 33.0, minBetStars: 12, color: '#FF4500' },
            { chance: 5, multiplier: 20.0, minBetStars: 20, color: '#FF8C00' },
            { chance: 7, multiplier: 14.3, minBetStars: 28, color: '#FFD700' },
            { chance: 10, multiplier: 10.0, minBetStars: 40, color: '#ADFF2F' },
            { chance: 15, multiplier: 6.67, minBetStars: 60, color: '#32CD32' },
            { chance: 20, multiplier: 5.0, minBetStars: 80, color: '#00FA9A' },
            { chance: 25, multiplier: 4.0, minBetStars: 100, color: '#00CED1' },
            { chance: 30, multiplier: 3.33, minBetStars: 120, color: '#1E90FF' },
            { chance: 40, multiplier: 2.5, minBetStars: 160, color: '#4169E1' },
            { chance: 50, multiplier: 2.0, minBetStars: 200, color: '#8A2BE2' },
            { chance: 65, multiplier: 1.54, minBetStars: 260, color: '#DA70D6' }
        ];
        
        // Конвертация: 1 спин = 50 stars
        this.spinToStars = 50;
        this.maxBetSpins = 100; // Максимум 100 спинов
        
        this.initializeElements();
        this.setupEventListeners();
        this.updateWheel();
        this.updateDisplay();
        this.showWelcomeNotification();
        
        // Загружаем статистику
        this.loadStats();
    }
    
    initializeElements() {
        // Основные элементы
        this.wheelElement = document.getElementById('mono-wheel');
        this.slider = document.getElementById('mono-slider');
        this.currentChanceElement = document.getElementById('current-chance');
        this.currentChanceDisplay = document.getElementById('current-chance-display');
        this.currentMultiplierElement = document.getElementById('current-multiplier');
        this.currentMultiplierDisplay = document.getElementById('current-multiplier-display');
        this.currentMinBetElement = document.getElementById('current-min-bet');
        this.betWarning = document.getElementById('bet-warning');
        this.minBetWarning = document.getElementById('min-bet-warning');
        this.minBetValue = document.getElementById('min-bet-value');
        this.maxBetValue = document.getElementById('max-bet-value');
        
        // Элементы ставок
        this.currentBetSpinsElement = document.getElementById('current-bet-spins');
        this.currentBetStarsElement = document.getElementById('current-bet-stars');
        this.spinCostDisplay = document.getElementById('spin-cost-display');
        this.currentBetInfo = document.getElementById('current-bet-info');
        this.currentChanceInfo = document.getElementById('current-chance-info');
        
        // Элементы потенциального выигрыша
        this.potentialWinSpins = document.getElementById('potential-win-spins');
        this.potentialWinStars = document.getElementById('potential-win-stars');
        this.potentialProfit = document.getElementById('potential-profit');
        
        // Кнопки
        this.spinButton = document.getElementById('spin-button');
        this.recommendedBetsContainer = document.getElementById('recommended-bets');
        
        // Статистика
        this.totalGamesElement = document.getElementById('total-games');
        this.winsCountElement = document.getElementById('wins-count');
        this.winRateElement = document.getElementById('win-rate');
        this.nftsWonElement = document.getElementById('nfts-won');
        
        // Модальные окна
        this.rulesModal = document.getElementById('rules-modal');
        this.rulesClose = document.getElementById('rules-close');
        this.rulesBtn = document.getElementById('rules-btn');
        
        // Навигация
        this.backBtn = document.getElementById('back-btn');
        this.shopBtn = document.getElementById('shop-btn');
        
        // Баланс
        this.spinsBalanceElement = document.getElementById('spins-balance');
        this.starsBalanceElement = document.getElementById('stars-balance');
    }
    
    setupEventListeners() {
        // Слайдер
        if (this.slider) {
            this.slider.addEventListener('input', (e) => {
                this.onSliderChange(parseInt(e.target.value));
            });
        }
        
        // Кнопки быстрого выбора шанса
        document.querySelectorAll('.chance-step').forEach(step => {
            step.addEventListener('click', () => {
                const chance = parseInt(step.dataset.chance);
                this.setChance(chance);
                this.slider.value = chance;
            });
        });
        
        // Управление ставкой
        document.querySelectorAll('[data-action="increase"]').forEach(btn => {
            btn.addEventListener('click', () => this.increaseBet());
        });
        
        document.querySelectorAll('[data-action="decrease"]').forEach(btn => {
            btn.addEventListener('click', () => this.decreaseBet());
        });
        
        // Быстрые множители ставки
        document.querySelectorAll('.bet-quick-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const multiplier = e.target.dataset.multiplier;
                if (multiplier === 'max') {
                    this.setMaxBet();
                } else {
                    this.multiplyBet(parseFloat(multiplier));
                }
            });
        });
        
        // Кнопка спина
        if (this.spinButton) {
            this.spinButton.addEventListener('click', () => this.spin());
        }
        
        // Навигация
        if (this.backBtn) {
            this.backBtn.addEventListener('click', () => window.history.back());
        }
        
        if (this.shopBtn) {
            this.shopBtn.addEventListener('click', () => {
                if (window.Telegram && window.Telegram.WebApp) {
                    window.Telegram.WebApp.openLink('https://t.me/your_bot?start=shop');
                }
            });
        }
        
        // Правила
        if (this.rulesBtn) {
            this.rulesBtn.addEventListener('click', () => {
                this.rulesModal.classList.add('show');
            });
        }
        
        if (this.rulesClose) {
            this.rulesClose.addEventListener('click', () => {
                this.rulesModal.classList.remove('show');
            });
        }
        
        // Закрытие модального окна по клику вне его
        this.rulesModal.addEventListener('click', (e) => {
            if (e.target === this.rulesModal) {
                this.rulesModal.classList.remove('show');
            }
        });
    }
    
    onSliderChange(value) {
        // Находим ближайший допустимый шанс
        const closest = this.chanceSettings.reduce((prev, curr) => {
            return Math.abs(curr.chance - value) < Math.abs(prev.chance - value) ? curr : prev;
        });
        
        this.setChance(closest.chance);
    }
    
    setChance(chance) {
        this.currentChance = chance;
        this.updateWheel();
        this.updateDisplay();
        this.updateRecommendedBets();
        
        // Проверяем текущую ставку на соответствие минимальной
        this.validateCurrentBet();
    }
    
    updateWheel() {
        if (!this.wheelElement) return;
        
        // Очищаем колесо
        this.wheelElement.innerHTML = '';
        
        const setting = this.getCurrentSetting();
        const totalDegrees = 360;
        const winDegrees = (this.currentChance / 100) * totalDegrees;
        const loseDegrees = totalDegrees - winDegrees;
        
        // Создаем выигрышный сектор
        const winSector = document.createElement('div');
        winSector.className = 'wheel-sector win-sector';
        winSector.style.transform = `rotate(0deg)`;
        winSector.style.clipPath = this.getSectorClipPath(0, winDegrees);
        winSector.style.backgroundColor = setting.color;
        this.wheelElement.appendChild(winSector);
        
        // Создаем проигрышный сектор
        const loseSector = document.createElement('div');
        loseSector.className = 'wheel-sector';
        loseSector.style.transform = `rotate(${winDegrees}deg)`;
        loseSector.style.clipPath = this.getSectorClipPath(winDegrees, loseDegrees);
        loseSector.style.backgroundColor = '#3a3a4a'; // Серый цвет
        this.wheelElement.appendChild(loseSector);
        
        // Обновляем центр колеса
        if (this.currentChanceDisplay) {
            this.currentChanceDisplay.textContent = `${this.currentChance}%`;
            this.currentChanceDisplay.style.color = setting.color;
        }
        
        if (this.currentMultiplierDisplay) {
            this.currentMultiplierDisplay.textContent = `${setting.multiplier.toFixed(2)}x`;
        }
    }
    
    getSectorClipPath(startAngle, angle) {
        // Преобразуем углы в радианы
        const startRad = (startAngle - 90) * Math.PI / 180;
        const endRad = (startAngle + angle - 90) * Math.PI / 180;
        
        // Координаты точек на окружности
        const x1 = 50 + 50 * Math.cos(startRad);
        const y1 = 50 + 50 * Math.sin(startRad);
        const x2 = 50 + 50 * Math.cos(endRad);
        const y2 = 50 + 50 * Math.sin(endRad);
        
        return `polygon(50% 50%, ${x1}% ${y1}%, ${x2}% ${y2}%)`;
    }
    
    updateDisplay() {
        const setting = this.getCurrentSetting();
        const betStars = this.currentBetSpins * this.spinToStars;
        const minBetStars = setting.minBetStars;
        const minBetSpins = Math.ceil(minBetStars / this.spinToStars);
        
        // Обновляем информацию о шансе
        if (this.currentChanceElement) {
            this.currentChanceElement.textContent = `${this.currentChance}%`;
            this.currentChanceElement.style.color = setting.color;
        }
        
        if (this.currentMultiplierElement) {
            this.currentMultiplierElement.textContent = `${setting.multiplier.toFixed(2)}x`;
        }
        
        if (this.currentMinBetElement) {
            const minBetText = minBetSpins === 1 ? '1 спин' : `${minBetSpins} спинов`;
            this.currentMinBetElement.querySelector('.min-bet-text').textContent = 
                `Мин. ставка: ${minBetStars} stars (${minBetText})`;
        }
        
        // Обновляем информацию о минимальной ставке
        if (this.minBetValue) {
            this.minBetValue.textContent = `${minBetStars} stars`;
        }
        
        if (this.maxBetValue) {
            const maxBetStars = this.maxBetSpins * this.spinToStars;
            this.maxBetValue.textContent = `${maxBetStars} stars`;
        }
        
        // Обновляем текущую ставку
        this.updateBetDisplay();
        
        // Обновляем потенциальный выигрыш
        this.updatePotentialWin();
        
        // Проверяем и показываем/скрываем предупреждение
        this.validateCurrentBet();
    }
    
    updateBetDisplay() {
        const setting = this.getCurrentSetting();
        const betStars = this.currentBetSpins * this.spinToStars;
        const minBetStars = setting.minBetStars;
        
        // Обновляем отображение ставки
        if (this.currentBetSpinsElement) {
            this.currentBetSpinsElement.textContent = 
                `${this.currentBetSpins} ${this.getSpinsWord(this.currentBetSpins)}`;
        }
        
        if (this.currentBetStarsElement) {
            this.currentBetStarsElement.textContent = `${betStars} stars`;
        }
        
        if (this.spinCostDisplay) {
            this.spinCostDisplay.textContent = `${betStars} stars`;
        }
        
        if (this.currentBetInfo) {
            this.currentBetInfo.textContent = `Ставка: ${this.currentBetSpins} спин`;
        }
        
        if (this.currentChanceInfo) {
            this.currentChanceInfo.textContent = `Шанс: ${this.currentChance}%`;
        }
        
        // Обновляем активные кнопки быстрого выбора
        this.updateQuickBetButtons();
    }
    
    updatePotentialWin() {
        const setting = this.getCurrentSetting();
        const potentialWinSpins = this.currentBetSpins * setting.multiplier;
        const potentialWinStars = potentialWinSpins * this.spinToStars;
        const betStars = this.currentBetSpins * this.spinToStars;
        const potentialProfit = potentialWinStars - betStars;
        
        if (this.potentialWinSpins) {
            this.potentialWinSpins.textContent = potentialWinSpins.toFixed(2);
        }
        
        if (this.potentialWinStars) {
            this.potentialWinStars.textContent = Math.round(potentialWinStars);
        }
        
        if (this.potentialProfit) {
            this.potentialProfit.textContent = Math.round(potentialProfit);
            this.potentialProfit.style.color = potentialProfit >= 0 ? '#32CD32' : '#DC143C';
        }
    }
    
    validateCurrentBet() {
        const setting = this.getCurrentSetting();
        const betStars = this.currentBetSpins * this.spinToStars;
        const minBetStars = setting.minBetStars;
        const maxBetStars = this.maxBetSpins * this.spinToStars;
        
        let isValid = true;
        let warningText = '';
        
        if (betStars < minBetStars) {
            isValid = false;
            const minBetSpins = Math.ceil(minBetStars / this.spinToStars);
            warningText = `Минимальная ставка для ${this.currentChance}%: ${minBetStars} stars (${minBetSpins} спин)`;
        } else if (betStars > maxBetStars) {
            isValid = false;
            warningText = `Максимальная ставка: ${maxBetStars} stars`;
        }
        
        // Показываем/скрываем предупреждение
        if (this.betWarning && this.minBetWarning) {
            if (!isValid) {
                this.betWarning.style.display = 'flex';
                this.minBetWarning.textContent = warningText;
            } else {
                this.betWarning.style.display = 'none';
            }
        }
        
        // Обновляем состояние кнопки спина
        if (this.spinButton) {
            this.spinButton.disabled = !isValid || this.isSpinning;
        }
        
        return isValid;
    }
    
    updateRecommendedBets() {
        if (!this.recommendedBetsContainer) return;
        
        this.recommendedBetsContainer.innerHTML = '';
        const setting = this.getCurrentSetting();
        const minBetSpins = Math.ceil(setting.minBetStars / this.spinToStars);
        
        // Рекомендованные ставки
        const recommendations = [
            { spins: minBetSpins, label: 'Мин.' },
            { spins: minBetSpins * 2, label: '2x' },
            { spins: minBetSpins * 5, label: '5x' },
            { spins: minBetSpins * 10, label: '10x' }
        ];
        
        recommendations.forEach(rec => {
            if (rec.spins <= this.maxBetSpins) {
                const betStars = rec.spins * this.spinToStars;
                const potentialWin = rec.spins * setting.multiplier;
                
                const betElement = document.createElement('div');
                betElement.className = 'recommended-bet';
                if (rec.spins === this.currentBetSpins) {
                    betElement.classList.add('active');
                }
                
                betElement.innerHTML = `
                    <div class="bet-label">${rec.label}</div>
                    <div class="bet-amount">${rec.spins} спин</div>
                    <div class="bet-potential">≈${potentialWin.toFixed(1)}x</div>
                `;
                
                betElement.addEventListener('click', () => {
                    this.setBetSpins(rec.spins);
                });
                
                this.recommendedBetsContainer.appendChild(betElement);
            }
        });
    }
    
    updateQuickBetButtons() {
        document.querySelectorAll('.bet-quick-btn').forEach(btn => {
            const multiplier = btn.dataset.multiplier;
            btn.classList.remove('active');
            
            if (multiplier === 'max') {
                const maxBetSpins = this.maxBetSpins;
                if (this.currentBetSpins === maxBetSpins) {
                    btn.classList.add('active');
                }
            } else {
                const multValue = parseFloat(multiplier);
                const minBetSpins = Math.ceil(this.getCurrentSetting().minBetStars / this.spinToStars);
                if (this.currentBetSpins === minBetSpins * multValue) {
                    btn.classList.add('active');
                }
            }
        });
    }
    
    setBetSpins(spins) {
        this.currentBetSpins = Math.max(1, Math.min(this.maxBetSpins, spins));
        this.updateDisplay();
    }
    
    increaseBet() {
        const setting = this.getCurrentSetting();
        const minBetSpins = Math.ceil(setting.minBetStars / this.spinToStars);
        
        // Увеличиваем с учетом минимальной ставки
        let newBet = this.currentBetSpins + minBetSpins;
        if (newBet > this.maxBetSpins) {
            newBet = this.maxBetSpins;
        }
        
        this.setBetSpins(newBet);
    }
    
    decreaseBet() {
        const setting = this.getCurrentSetting();
        const minBetSpins = Math.ceil(setting.minBetStars / this.spinToStars);
        
        // Уменьшаем с учетом минимальной ставки
        let newBet = this.currentBetSpins - minBetSpins;
        if (newBet < minBetSpins) {
            newBet = minBetSpins;
        }
        
        this.setBetSpins(newBet);
    }
    
    multiplyBet(multiplier) {
        const setting = this.getCurrentSetting();
        const minBetSpins = Math.ceil(setting.minBetStars / this.spinToStars);
        const newBet = Math.min(this.maxBetSpins, Math.ceil(minBetSpins * multiplier));
        this.setBetSpins(newBet);
    }
    
    setMaxBet() {
        this.setBetSpins(this.maxBetSpins);
    }
    
    getCurrentSetting() {
        return this.chanceSettings.find(s => s.chance === this.currentChance) || this.chanceSettings[0];
    }
    
    getSpinsWord(spins) {
        const lastDigit = spins % 10;
        const lastTwoDigits = spins % 100;
        
        if (lastTwoDigits >= 11 && lastTwoDigits <= 19) {
            return 'спинов';
        }
        
        if (lastDigit === 1) {
            return 'спин';
        } else if (lastDigit >= 2 && lastDigit <= 4) {
            return 'спина';
        } else {
            return 'спинов';
        }
    }
    
    async spin() {
        if (this.isSpinning) return;
        
        // Проверяем баланс
        const spinsBalance = parseInt(this.spinsBalanceElement?.textContent || 0);
        if (spinsBalance < this.currentBetSpins) {
            this.showNotification('Недостаточно спинов!', 'error', '🎰');
            return;
        }
        
        // Проверяем минимальную ставку
        if (!this.validateCurrentBet()) {
            return;
        }
        
        this.isSpinning = true;
        this.spinButton.disabled = true;
        
        // Анимация вращения колеса
        const spinResult = await this.performSpin();
        
        // Показываем результат
        this.showSpinResult(spinResult);
        
        // Обновляем баланс
        if (spinResult.success) {
            this.updateBalances(spinResult);
        }
        
        this.isSpinning = false;
        this.spinButton.disabled = false;
    }
    
    async performSpin() {
        // Добавляем класс вращения
        this.wheelElement.classList.add('spinning');
        
        // Определяем результат (в реальном проекте с сервера)
        const winNumber = Math.floor(Math.random() * 100) + 1;
        const won = winNumber <= this.currentChance;
        const setting = this.getCurrentSetting();
        
        // Вычисляем выигрыш
        let winSpins = 0;
        let winStars = 0;
        let nftAwarded = null;
        
        if (won) {
            winSpins = this.currentBetSpins * setting.multiplier;
            winStars = winSpins * this.spinToStars;
            
            // Шанс NFT 0.5%
            if (Math.random() < 0.005) {
                nftAwarded = {
                    id: Math.floor(Math.random() * 1000),
                    name: 'Удачный NFT',
                    rarity: 'rare'
                };
            }
        }
        
        // Анимация вращения с остановкой в нужном месте
        const spinDuration = 3000;
        const winRotation = won ? 0 : 180 + Math.random() * 180; // Для проигрыша останавливаем в серой зоне
        const totalRotation = 1440 + winRotation; // 4 полных оборота + целевой угол
        
        this.wheelElement.style.transition = `transform ${spinDuration}ms cubic-bezier(0.2, 0.8, 0.3, 1)`;
        this.wheelElement.style.transform = `rotate(${totalRotation}deg)`;
        
        // Ждем окончания анимации
        await new Promise(resolve => setTimeout(resolve, spinDuration));
        
        // Убираем класс вращения
        this.wheelElement.classList.remove('spinning');
        
        // В реальном проекте здесь отправка на сервер
        if (window.Telegram && window.Telegram.WebApp) {
            const payload = {
                action: 'mono_spin',
                user_id: this.userId,
                chance: this.currentChance,
                bet_spins: this.currentBetSpins,
                timestamp: Date.now()
            };
            window.Telegram.WebApp.sendData(JSON.stringify(payload));
        }
        
        return {
            success: true,
            won,
            chance: this.currentChance,
            win_number: winNumber,
            multiplier: won ? setting.multiplier : 0,
            win_spins: winSpins,
            win_stars: winStars,
            bet_spins: this.currentBetSpins,
            bet_stars: this.currentBetSpins * this.spinToStars,
            nft_awarded: nftAwarded
        };
    }
    
    showSpinResult(result) {
        const resultContainer = document.getElementById('result-container');
        const resultContent = document.getElementById('result-content');
        
        if (!resultContainer || !resultContent) return;
        
        if (result.won) {
            // Победа
            resultContent.innerHTML = `
                <div class="result-win">
                    <div class="result-icon">🎉</div>
                    <div class="result-title" style="color: #32CD32; font-size: 32px; font-weight: 800;">ПОБЕДА!</div>
                    <div class="result-chance">Выпало число: ${result.win_number}</div>
                    <div class="result-multiplier" style="font-size: 48px; font-weight: 800; color: #FFD700;">
                        ${result.multiplier.toFixed(2)}x
                    </div>
                    <div class="result-amount" style="font-size: 24px; margin: 20px 0;">
                        Выигрыш: ${result.win_spins.toFixed(2)} спинов
                    </div>
                    <div class="result-stars" style="font-size: 20px; color: #FFD700;">
                        ${Math.round(result.win_stars)} stars
                    </div>
                    ${result.nft_awarded ? `
                        <div class="result-nft" style="margin-top: 20px; padding: 16px; background: rgba(138, 43, 226, 0.2); border-radius: 12px;">
                            <div style="font-size: 24px;">🎁</div>
                            <div style="font-weight: 600; margin: 8px 0;">Получен NFT!</div>
                            <div>${result.nft_awarded.name}</div>
                            <div style="font-size: 12px; color: #b0b0c0;">Редкость: ${result.nft_awarded.rarity}</div>
                        </div>
                    ` : ''}
                </div>
            `;
            
            // Показываем уведомление о победе
            this.showNotification(
                `Победа! Выигрыш: ${Math.round(result.win_stars)} stars`,
                'success',
                '🎉'
            );
            
            if (result.nft_awarded) {
                // Отдельное уведомление о NFT
                setTimeout(() => {
                    this.showNotification(
                        `Получен NFT: ${result.nft_awarded.name}`,
                        'nft',
                        '🎁'
                    );
                }, 2000);
            }
        } else {
            // Проигрыш
            resultContent.innerHTML = `
                <div class="result-lose">
                    <div class="result-icon">😔</div>
                    <div class="result-title" style="color: #DC143C; font-size: 32px; font-weight: 800;">ПРОИГРЫШ</div>
                    <div class="result-chance">Выпало число: ${result.win_number}</div>
                    <div class="result-message" style="font-size: 20px; margin: 20px 0;">
                        Не повезло в этот раз!
                    </div>
                    <div class="result-lose-amount" style="font-size: 18px; color: #DC143C;">
                        Потеряно: ${result.bet_stars} stars
                    </div>
                    <div class="result-encouragement" style="margin-top: 20px; padding: 16px; background: rgba(30, 144, 255, 0.2); border-radius: 12px;">
                        <div style="font-size: 24px;">💪</div>
                        <div style="font-weight: 600; margin: 8px 0;">Не сдавайтесь!</div>
                        <div style="font-size: 14px; color: #b0b0c0;">Удача обязательно улыбнется вам в следующий раз</div>
                    </div>
                </div>
            `;
            
            // Показываем утешительное уведомление
            this.showNotification(
                'Не повезло в этот раз. Попробуйте еще!',
                'warning',
                '💪'
            );
        }
        
        // Показываем результат
        resultContainer.classList.add('show');
        
        // Скрываем через 5 секунд
        setTimeout(() => {
            resultContainer.classList.remove('show');
        }, 5000);
    }
    
    updateBalances(result) {
        // Обновляем баланс спинов
        const currentSpins = parseInt(this.spinsBalanceElement.textContent || 0);
        let newSpins = currentSpins;
        
        if (result.won) {
            // Выигрыш минус использованные спины
            newSpins = currentSpins + result.win_spins - result.bet_spins;
        } else {
            // Проигрыш - списываем ставку
            newSpins = currentSpins - result.bet_spins;
        }
        
        this.spinsBalanceElement.textContent = Math.max(0, newSpins);
        
        // Обновляем статистику
        this.updateStats(result);
    }
    
    async loadStats() {
        // В реальном проекте загрузка с сервера
        // Для демо используем фиктивные данные
        setTimeout(() => {
            if (this.totalGamesElement) this.totalGamesElement.textContent = '5';
            if (this.winsCountElement) this.winsCountElement.textContent = '2';
            if (this.winRateElement) this.winRateElement.textContent = '40%';
            if (this.nftsWonElement) this.nftsWonElement.textContent = '0';
        }, 1000);
    }
    
    updateStats(result) {
        // Обновляем локальную статистику
        let totalGames = parseInt(this.totalGamesElement.textContent || 0);
        let wins = parseInt(this.winsCountElement.textContent || 0);
        
        totalGames += 1;
        if (result.won) {
            wins += 1;
        }
        
        const winRate = totalGames > 0 ? Math.round((wins / totalGames) * 100) : 0;
        
        this.totalGamesElement.textContent = totalGames;
        this.winsCountElement.textContent = wins;
        this.winRateElement.textContent = `${winRate}%`;
        
        if (result.nft_awarded) {
            const nftsWon = parseInt(this.nftsWonElement.textContent || 0);
            this.nftsWonElement.textContent = nftsWon + 1;
        }
    }
    
    showWelcomeNotification() {
        this.showNotification(
            'Добро пожаловать в игру МОНО! Выберите шанс и ставку',
            'info',
            '🎰'
        );
    }
    
    showNotification(message, type = 'info', icon = 'ℹ️') {
        // Используем нашу систему уведомлений
        if (window.showNotification) {
            window.showNotification(message, type, icon);
        } else {
            // Fallback
            alert(message);
        }
    }
}

// Система уведомлений
class NotificationSystem {
    constructor() {
        this.notificationBanner = document.getElementById('notification-banner');
        this.notificationIcon = document.getElementById('notification-icon');
        this.notificationTitle = document.getElementById('notification-title');
        this.notificationMessage = document.getElementById('notification-message');
        this.notificationClose = document.getElementById('notification-close');
        
        this.setupNotificationListeners();
        this.autoHideTimeout = null;
    }
    
    setupNotificationListeners() {
        if (this.notificationClose) {
            this.notificationClose.addEventListener('click', () => {
                this.hideNotification();
            });
        }
    }
    
    showNotification(title, message, type = 'info', icon = 'ℹ️') {
        if (!this.notificationBanner) return;
        
        // Останавливаем предыдущий таймер
        if (this.autoHideTimeout) {
            clearTimeout(this.autoHideTimeout);
        }
        
        // Устанавливаем контент
        if (this.notificationIcon) {
            this.notificationIcon.textContent = icon;
        }
        
        if (this.notificationTitle) {
            this.notificationTitle.textContent = title;
        }
        
        if (this.notificationMessage) {
            this.notificationMessage.textContent = message;
        }
        
        // Устанавливаем тип уведомления
        this.notificationBanner.className = 'notification-banner';
        this.notificationBanner.classList.add(type);
        this.notificationBanner.classList.add('show');
        
        // Автоматическое скрытие через 10 секунд
        this.autoHideTimeout = setTimeout(() => {
            this.hideNotification();
        }, 10000);
    }
    
    hideNotification() {
        if (!this.notificationBanner) return;
        
        this.notificationBanner.classList.remove('show');
        
        // Очищаем таймер
        if (this.autoHideTimeout) {
            clearTimeout(this.autoHideTimeout);
            this.autoHideTimeout = null;
        }
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Инициализируем систему уведомлений
    window.notificationSystem = new NotificationSystem();
    
    // Функция для глобального доступа
    window.showNotification = (message, type = 'info', icon = 'ℹ️') => {
        const title = type === 'success' ? 'Поздравляем!' : 
                     type === 'error' ? 'Ошибка!' :
                     type === 'warning' ? 'Внимание!' :
                     type === 'nft' ? '🎁 NFT получен!' :
                     'Уведомление';
        
        window.notificationSystem.showNotification(title, message, type, icon);
    };
    
    // Получаем user_id из URL
    const urlParams = new URLSearchParams(window.location.search);
    const userId = urlParams.get('user_id') || 'demo';
    
    // Инициализируем игру
    window.monoGame = new MonoGame(userId);
    
    // Загружаем баланс (в реальном проекте с сервера)
    setTimeout(() => {
        const spinsBalance = document.getElementById('spins-balance');
        const starsBalance = document.getElementById('stars-balance');
        
        if (spinsBalance && userId === 'demo') {
            spinsBalance.textContent = '50';
        }
        
        if (starsBalance && userId === 'demo') {
            starsBalance.textContent = '2500';
        }
    }, 500);
});
