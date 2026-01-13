import asyncpg
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class Database:
    """Класс для работы с базой данных PostgreSQL"""
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool = None
    
    async def connect(self):
        """Подключиться к базе данных"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            logger.info("Подключено к базе данных")
    
    async def close(self):
        """Закрыть соединение"""
        if self.pool:
            await self.pool.close()
            logger.info("Соединение с БД закрыто")
    
    async def initialize(self):
        """Инициализировать таблицы"""
        await self.connect()
        await self._create_tables()
        logger.info("Таблицы инициализированы")
    
    async def _create_tables(self):
        """Создать все необходимые таблицы"""
        # Таблица пользователей
        await self.pool.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                stars_balance INTEGER DEFAULT 0,
                spins_balance INTEGER DEFAULT 0,
                total_deposited INTEGER DEFAULT 0,
                total_withdrawn INTEGER DEFAULT 0,
                total_won INTEGER DEFAULT 0,
                total_games INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Таблица истории игр Моно
        await self.pool.execute('''
            CREATE TABLE IF NOT EXISTS mono_history (
                history_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                chance INTEGER,
                bet_spins INTEGER,
                bet_stars INTEGER,
                win_number INTEGER,
                won BOOLEAN,
                win_spins DECIMAL(10,2),
                win_stars INTEGER,
                multiplier DECIMAL(10,2),
                nft_awarded BOOLEAN DEFAULT FALSE,
                min_bet_required INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Таблица платежей
        await self.pool.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                payment_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                amount INTEGER,
                currency VARCHAR(10),
                provider VARCHAR(50),
                provider_payment_id VARCHAR(255),
                telegram_payment_charge_id VARCHAR(255),
                status VARCHAR(50),
                product_type VARCHAR(50),
                product_amount INTEGER,
                invoice_payload TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Индексы
        await self.pool.execute('CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)')
        await self.pool.execute('CREATE INDEX IF NOT EXISTS idx_mono_history_user_id ON mono_history(user_id, created_at)')
        await self.pool.execute('CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id, created_at)')
    
    async def register_user(self, user_id: int, username: str, first_name: str) -> bool:
        """Зарегистрировать нового пользователя"""
        try:
            await self.pool.execute('''
                INSERT INTO users (user_id, username, first_name)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE
                SET username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    updated_at = NOW()
            ''', user_id, username, first_name)
            
            logger.info(f"Пользователь зарегистрирован: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка регистрации пользователя {user_id}: {e}")
            return False
    
    async def get_stars_balance(self, user_id: int) -> int:
        """Получить баланс stars"""
        row = await self.pool.fetchrow('''
            SELECT stars_balance FROM users WHERE user_id = $1
        ''', user_id)
        
        return row['stars_balance'] if row else 0
    
    async def get_spins_balance(self, user_id: int) -> int:
        """Получить баланс спинов"""
        row = await self.pool.fetchrow('''
            SELECT spins_balance FROM users WHERE user_id = $1
        ''', user_id)
        
        return row['spins_balance'] if row else 0
    
    async def update_stars_balance(self, user_id: int, amount: int) -> bool:
        """Обновить баланс stars"""
        try:
            await self.pool.execute('''
                UPDATE users 
                SET stars_balance = stars_balance + $2,
                    updated_at = NOW()
                WHERE user_id = $1
            ''', user_id, amount)
            
            if amount > 0:
                await self.pool.execute('''
                    UPDATE users 
                    SET total_deposited = total_deposited + $2,
                        updated_at = NOW()
                    WHERE user_id = $1
                ''', user_id, amount)
            
            logger.info(f"Баланс stars обновлен: {user_id} +{amount}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления баланса stars {user_id}: {e}")
            return False
    
    async def update_spins_balance(self, user_id: int, amount: int) -> bool:
        """Обновить баланс спинов"""
        try:
            await self.pool.execute('''
                UPDATE users 
                SET spins_balance = spins_balance + $2,
                    updated_at = NOW()
                WHERE user_id = $1
            ''', user_id, amount)
            
            logger.info(f"Баланс спинов обновлен: {user_id} +{amount}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обновления баланса спинов {user_id}: {e}")
            return False
    
    async def add_mono_history(self, user_id: int, chance: int, bet_spins: int, 
                              bet_stars: int, win_number: int, won: bool,
                              win_spins: float, win_stars: int, multiplier: float,
                              nft_awarded: bool, min_bet_required: int):
        """Добавить историю игры в Моно"""
        await self.pool.execute('''
            INSERT INTO mono_history 
            (user_id, chance, bet_spins, bet_stars, win_number, won, 
             win_spins, win_stars, multiplier, nft_awarded, min_bet_required)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ''', user_id, chance, bet_spins, bet_stars, win_number, won,
            win_spins, win_stars, multiplier, nft_awarded, min_bet_required)
        
        # Обновляем статистику пользователя
        await self.pool.execute('''
            UPDATE users 
            SET total_games = total_games + 1,
                total_won = total_won + $2,
                updated_at = NOW()
            WHERE user_id = $1
        ''', user_id, win_stars)
    
    async def add_payment(self, user_id: int, amount: int, currency: str, 
                         provider: str, provider_payment_id: str,
                         telegram_payment_charge_id: str, status: str,
                         product_type: str, product_amount: int, 
                         invoice_payload: str) -> int:
        """Добавить запись о платеже"""
        row = await self.pool.fetchrow('''
            INSERT INTO payments 
            (user_id, amount, currency, provider, provider_payment_id,
             telegram_payment_charge_id, status, product_type, product_amount,
             invoice_payload)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING payment_id
        ''', user_id, amount, currency, provider, provider_payment_id,
            telegram_payment_charge_id, status, product_type, product_amount,
            invoice_payload)
        
        return row['payment_id'] if row else 0
    
    async def get_payment_by_telegram_id(self, telegram_payment_charge_id: str) -> Optional[Dict]:
        """Получить платеж по telegram ID"""
        row = await self.pool.fetchrow('''
            SELECT * FROM payments 
            WHERE telegram_payment_charge_id = $1
        ''', telegram_payment_charge_id)
        
        return dict(row) if row else None
    
    async def get_user_mono_stats(self, user_id: int) -> Dict:
        """Получить статистику пользователя по Моно"""
        row = await self.pool.fetchrow('''
            SELECT 
                COUNT(*) as total_games,
                SUM(CASE WHEN won THEN 1 ELSE 0 END) as wins,
                SUM(bet_stars) as total_wagered_stars,
                SUM(win_stars) as total_won_stars,
                MAX(multiplier) as max_multiplier,
                SUM(CASE WHEN nft_awarded THEN 1 ELSE 0 END) as nfts_won,
                ROUND(AVG(chance)) as avg_chance,
                SUM(min_bet_required) as total_min_bet_required
            FROM mono_history 
            WHERE user_id = $1
        ''', user_id)
        
        return dict(row) if row else {}
    
    async def get_mono_statistics(self) -> Dict:
        """Получить общую статистику по Моно"""
        row = await self.pool.fetchrow('''
            SELECT 
                COUNT(*) as total_games,
                SUM(CASE WHEN won THEN 1 ELSE 0 END) as total_wins,
                SUM(bet_stars) as total_wagered_stars,
                SUM(win_stars) as total_won_stars,
                SUM(CASE WHEN nft_awarded THEN 1 ELSE 0 END) as total_nfts,
                ROUND(AVG(chance)) as avg_chance,
                SUM(min_bet_required) as total_min_bet_collected
            FROM mono_history
        ''')
        
        return dict(row) if row else {}
