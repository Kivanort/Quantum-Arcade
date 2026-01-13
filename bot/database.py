import asyncpg
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
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
        
        # Создание таблиц
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
                level INTEGER DEFAULT 1,
                rating INTEGER DEFAULT 1000,
                achievements JSONB DEFAULT '[]',
                settings JSONB DEFAULT '{}',
                last_active TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
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
                bonus_nft INTEGER DEFAULT 0,
                invoice_payload TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Таблица истории игр
        await self.pool.execute('''
            CREATE TABLE IF NOT EXISTS game_history (
                history_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                game_type VARCHAR(50),
                bet_amount INTEGER,
                chance INTEGER,
                color VARCHAR(50),
                winning_color VARCHAR(50),
                result_sector INTEGER,
                won BOOLEAN,
                win_amount INTEGER,
                win_multiplier DECIMAL(10,2),
                nft_awarded BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Таблица NFT
        await self.pool.execute('''
            CREATE TABLE IF NOT EXISTS nfts (
                nft_id SERIAL PRIMARY KEY,
                name VARCHAR(255),
                rarity VARCHAR(50),
                value INTEGER,
                color VARCHAR(20),
                emoji VARCHAR(10),
                feature TEXT,
                image_url TEXT,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Таблица владения NFT
        await self.pool.execute('''
            CREATE TABLE IF NOT EXISTS user_nfts (
                user_nft_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                nft_id INTEGER REFERENCES nfts(nft_id),
                acquired_date TIMESTAMP DEFAULT NOW(),
                is_tradeable BOOLEAN DEFAULT TRUE,
                is_staked BOOLEAN DEFAULT FALSE,
                UNIQUE(user_id, nft_id)
            )
        ''')
        
        # Таблица бустов
        await self.pool.execute('''
            CREATE TABLE IF NOT EXISTS boosters (
                booster_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                type VARCHAR(50),
                value DECIMAL(10,2),
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Таблица инвентаря
        await self.pool.execute('''
            CREATE TABLE IF NOT EXISTS inventory_history (
                history_id SERIAL PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                action VARCHAR(50),
                item_type VARCHAR(50),
                item_id INTEGER,
                item_name VARCHAR(255),
                quantity INTEGER,
                metadata JSONB DEFAULT '{}',
                source_user_id BIGINT,
                target_user_id BIGINT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Таблица демо-сессий
        await self.pool.execute('''
            CREATE TABLE IF NOT EXISTS demo_sessions (
                session_id VARCHAR(255) PRIMARY KEY,
                user_id BIGINT REFERENCES users(user_id),
                demo_stars INTEGER DEFAULT 1000,
                demo_spins INTEGER DEFAULT 10,
                expires_at TIMESTAMP DEFAULT NOW() + INTERVAL '1 hour',
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Таблица админов
        await self.pool.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                admin_id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE REFERENCES users(user_id),
                role VARCHAR(50) DEFAULT 'moderator',
                permissions JSONB DEFAULT '{}',
                created_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Индексы для производительности
        await self.pool.execute('CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active)')
        await self.pool.execute('CREATE INDEX IF NOT EXISTS idx_game_history_user_id ON game_history(user_id, created_at)')
        await self.pool.execute('CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id, created_at)')
        await self.pool.execute('CREATE INDEX IF NOT EXISTS idx_user_nfts_user_id ON user_nfts(user_id)')
    
    # Методы для пользователей
    
    async def register_user(self, user_id: int, username: str, first_name: str) -> bool:
        """Зарегистрировать нового пользователя"""
        try:
            await self.pool.execute('''
                INSERT INTO users (user_id, username, first_name)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE
                SET username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_active = NOW(),
                    updated_at = NOW()
            ''', user_id, username, first_name)
            
            # Добавляем начальные достижения
            await self._add_initial_achievements(user_id)
            
            logger.info(f"Пользователь зарегистрирован: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка регистрации пользователя {user_id}: {e}")
            return False
    
    async def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Получить информацию о пользователе"""
        row = await self.pool.fetchrow('''
            SELECT * FROM users WHERE user_id = $1
        ''', user_id)
        
        return dict(row) if row else None
    
    async def update_user_activity(self, user_id: int):
        """Обновить время последней активности"""
        await self.pool.execute('''
            UPDATE users 
            SET last_active = NOW(), updated_at = NOW()
            WHERE user_id = $1
        ''', user_id)
    
    # Методы для балансов
    
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
            
            # Обновляем общее пополнение если это депозит
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
    
    async def set_spin_balance(self, user_id: int, amount: int) -> bool:
        """Установить баланс спинов (админ)"""
        try:
            await self.pool.execute('''
                UPDATE users 
                SET spins_balance = $2,
                    updated_at = NOW()
                WHERE user_id = $1
            ''', user_id, amount)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка установки баланса спинов {user_id}: {e}")
            return False
    
    async def get_total_deposited(self, user_id: int) -> int:
        """Получить общую сумму пополнений"""
        row = await self.pool.fetchrow('''
            SELECT total_deposited FROM users WHERE user_id = $1
        ''', user_id)
        
        return row['total_deposited'] if row else 0
    
    async def get_total_spins_used(self, user_id: int) -> int:
        """Получить общее количество использованных спинов"""
        row = await self.pool.fetchrow('''
            SELECT COUNT(*) as count FROM game_history 
            WHERE user_id = $1 AND game_type IN ('mono', 'roulette')
        ''', user_id)
        
        return row['count'] if row else 0
    
    # Методы для платежей
    
    async def add_payment(self, user_id: int, amount: int, currency: str, 
                         provider: str, provider_payment_id: str,
                         telegram_payment_charge_id: str, status: str,
                         product_type: str, product_amount: int,
                         bonus_nft: int, invoice_payload: str) -> int:
        """Добавить запись о платеже"""
        row = await self.pool.fetchrow('''
            INSERT INTO payments 
            (user_id, amount, currency, provider, provider_payment_id,
             telegram_payment_charge_id, status, product_type, product_amount,
             bonus_nft, invoice_payload)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING payment_id
        ''', user_id, amount, currency, provider, provider_payment_id,
            telegram_payment_charge_id, status, product_type, product_amount,
            bonus_nft, invoice_payload)
        
        return row['payment_id'] if row else 0
    
    async def get_payment_by_telegram_id(self, telegram_payment_charge_id: str) -> Optional[Dict]:
        """Получить платеж по telegram ID"""
        row = await self.pool.fetchrow('''
            SELECT * FROM payments 
            WHERE telegram_payment_charge_id = $1
        ''', telegram_payment_charge_id)
        
        return dict(row) if row else None
    
    # Методы для истории игр
    
    async def add_game_history(self, user_id: int, game_type: str, 
                              bet_amount: int = 0, chance: int = 0,
                              color: str = None, winning_color: str = None,
                              result_sector: int = None, won: bool = False,
                              win_amount: int = 0, win_multiplier: float = 0,
                              nft_awarded: bool = False):
        """Добавить запись в историю игр"""
        await self.pool.execute('''
            INSERT INTO game_history 
            (user_id, game_type, bet_amount, chance, color, winning_color,
             result_sector, won, win_amount, win_multiplier, nft_awarded)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ''', user_id, game_type, bet_amount, chance, color, winning_color,
            result_sector, won, win_amount, win_multiplier, nft_awarded)
        
        # Обновляем статистику пользователя
        await self.update_user_stats(
            user_id=user_id,
            games_played=1,
            total_wagered=bet_amount,
            total_won=win_amount
        )
    
    async def add_bet_history(self, user_id: int, game_type: str, 
                             bet_color: str, bet_amount: int,
                             winning_color: str, won: bool,
                             win_amount: int, win_multiplier: float):
        """Добавить историю ставки"""
        await self.add_game_history(
            user_id=user_id,
            game_type=game_type,
            bet_amount=bet_amount,
            color=bet_color,
            winning_color=winning_color,
            won=won,
            win_amount=win_amount,
            win_multiplier=win_multiplier
        )
    
    async def add_spin_history(self, user_id: int, game_type: str,
                              result_sector: int, won: bool,
                              win_amount: int, win_multiplier: float,
                              nft_awarded: bool):
        """Добавить историю спина"""
        await self.add_game_history(
            user_id=user_id,
            game_type=game_type,
            bet_amount=1,  # Всегда 1 спин
            result_sector=result_sector,
            won=won,
            win_amount=win_amount,
            win_multiplier=win_multiplier,
            nft_awarded=nft_awarded
        )
    
    async def add_multi_bet_history(self, user_id: int, bets: Dict[str, int],
                                   winning_color: str, total_bet: int,
                                   total_win: int):
        """Добавить историю множественной ставки"""
        # Сохраняем как одну запись с метаданными
        metadata = {
            "bets": bets,
            "total_bet": total_bet,
            "total_win": total_win
        }
        
        await self.pool.execute('''
            INSERT INTO game_history 
            (user_id, game_type, bet_amount, color, winning_color,
             won, win_amount, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ''', user_id, "lucky2_multi", total_bet, json.dumps(bets), 
            winning_color, total_win > 0, total_win, json.dumps(metadata))
    
    # Методы для статистики
    
    async def update_user_stats(self, user_id: int, games_played: int = 0,
                               total_wagered: int = 0, total_won: int = 0):
        """Обновить статистику пользователя"""
        await self.pool.execute('''
            UPDATE users 
            SET total_games = total_games + $2,
                total_won = total_won + $4,
                updated_at = NOW()
            WHERE user_id = $1
        ''', user_id, games_played, total_wagered, total_won)
        
        # Обновляем уровень и рейтинг
        await self._update_user_level(user_id)
    
    async def get_user_game_stats(self, user_id: int, game_type: str) -> Dict:
        """Получить статистику пользователя по игре"""
        # Для Моно
        if game_type == "mono":
            row = await self.pool.fetchrow('''
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN won THEN 1 ELSE 0 END) as wins,
                    SUM(bet_amount) as total_wagered,
                    SUM(win_amount) as total_won,
                    MAX(win_multiplier) as max_win,
                    SUM(CASE WHEN nft_awarded THEN 1 ELSE 0 END) as nfts_won,
                    ROUND(AVG(chance)) as avg_chance
                FROM game_history 
                WHERE user_id = $1 AND game_type = 'mono'
            ''', user_id)
        
        # Для Lucky2
        elif game_type == "lucky2":
            row = await self.pool.fetchrow('''
                SELECT 
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN won THEN 1 ELSE 0 END) as wins,
                    SUM(bet_amount) as total_wagered,
                    SUM(win_amount) as total_won,
                    MAX(win_multiplier) as max_win,
                    MAX(bet_amount) as max_bet,
                    AVG(bet_amount) as avg_bet
                FROM game_history 
                WHERE user_id = $1 AND game_type = 'lucky2'
            ''', user_id)
        
        # Для рулетки
        elif game_type == "roulette":
            row = await self.pool.fetchrow('''
                SELECT 
                    COUNT(*) as total_spins,
                    SUM(CASE WHEN won THEN 1 ELSE 0 END) as wins,
                    SUM(bet_amount) as total_wagered,
                    SUM(win_amount) as total_won,
                    MAX(win_multiplier) as max_multiplier,
                    SUM(CASE WHEN nft_awarded THEN 1 ELSE 0 END) as nfts_won,
                    MAX(win_amount) as max_win
                FROM game_history 
                WHERE user_id = $1 AND game_type = 'roulette'
            ''', user_id)
        
        else:
            return {}
        
        return dict(row) if row else {}
    
    async def get_game_type_stats(self, game_type: str) -> Dict:
        """Получить общую статистику по типу игры"""
        if game_type == "mono":
            row = await self.pool.fetchrow('''
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN won THEN 1 ELSE 0 END) as total_wins,
                    SUM(bet_amount) as total_wagered,
                    SUM(win_amount) as total_won,
                    SUM(CASE WHEN nft_awarded THEN 1 ELSE 0 END) as total_nfts,
                    ROUND(AVG(chance)) as avg_chance
                FROM game_history 
                WHERE game_type = 'mono'
            ''')
        
        elif game_type == "lucky2":
            row = await self.pool.fetchrow('''
                SELECT 
                    COUNT(*) as total_bets,
                    SUM(CASE WHEN won THEN 1 ELSE 0 END) as total_wins,
                    SUM(bet_amount) as total_turnover,
                    SUM(win_amount) as total_payout,
                    AVG(bet_amount) as avg_bet
                FROM game_history 
                WHERE game_type = 'lucky2'
            ''')
            
            # Статистика по цветам
            color_stats = {}
            for color in ["blue", "red", "purple"]:
                color_row = await self.pool.fetchrow('''
                    SELECT 
                        COUNT(*) as total_bets,
                        SUM(CASE WHEN won THEN 1 ELSE 0 END) as wins,
                        SUM(bet_amount) as total_wagered,
                        SUM(win_amount) as total_paid
                    FROM game_history 
                    WHERE game_type = 'lucky2' AND color = $1
                ''', color)
                
                if color_row:
                    color_stats[f"{color}_bets"] = color_row["total_bets"]
                    color_stats[f"{color}_wins"] = color_row["wins"]
                    color_stats[f"{color}_wagered"] = color_row["total_wagered"]
                    color_stats[f"{color}_paid"] = color_row["total_paid"]
            
            result = dict(row) if row else {}
            result.update(color_stats)
            return result
        
        elif game_type == "roulette":
            row = await self.pool.fetchrow('''
                SELECT 
                    COUNT(*) as total_spins,
                    SUM(CASE WHEN won THEN 1 ELSE 0 END) as total_wins,
                    SUM(bet_amount) as total_wagered,
                    SUM(win_amount) as total_won,
                    SUM(CASE WHEN nft_awarded THEN 1 ELSE 0 END) as total_nfts,
                    AVG(win_multiplier) as avg_multiplier,
                    SUM(CASE WHEN result_sector = 10 THEN 1 ELSE 0 END) as jackpot_hits
                FROM game_history 
                WHERE game_type = 'roulette'
            ''')
            
            # Статистика по секторам
            sector_stats = {}
            for sector_id in range(11):  # 0-10
                sector_row = await self.pool.fetchrow('''
                    SELECT 
                        COUNT(*) as hits,
                        SUM(win_amount) as paid
                    FROM game_history 
                    WHERE game_type = 'roulette' AND result_sector = $1
                ''', sector_id)
                
                if sector_row:
                    sector_stats[f"sector_{sector_id}_hits"] = sector_row["hits"]
                    sector_stats[f"sector_{sector_id}_paid"] = sector_row["paid"]
            
            result = dict(row) if row else {}
            result.update(sector_stats)
            return result
        
        else:
            return {}
    
    async def get_bot_statistics(self) -> Dict:
        """Получить общую статистику бота"""
        # Статистика пользователей
        users_row = await self.pool.fetchrow('''
            SELECT 
                COUNT(*) as total_users,
                SUM(CASE WHEN last_active >= NOW() - INTERVAL '24 hours' THEN 1 ELSE 0 END) as active_users_24h,
                SUM(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 ELSE 0 END) as new_users_24h
            FROM users
        ''')
        
        # Финансовая статистика
        finance_row = await self.pool.fetchrow('''
            SELECT 
                COALESCE(SUM(amount), 0) as total_turnover,
                COALESCE(SUM(amount * 0.7), 0) as revenue
            FROM payments 
            WHERE status = 'completed' AND currency = 'RUB'
        ''')
        
        # Статистика игр
        mono_row = await self.pool.fetchrow("SELECT COUNT(*) as games FROM game_history WHERE game_type = 'mono'")
        lucky2_row = await self.pool.fetchrow("SELECT COUNT(*) as bets FROM game_history WHERE game_type = 'lucky2'")
        roulette_row = await self.pool.fetchrow("SELECT COUNT(*) as spins FROM game_history WHERE game_type = 'roulette'")
        
        # NFT статистика
        nft_row = await self.pool.fetchrow('''
            SELECT 
                COUNT(*) as total_nfts,
                COUNT(DISTINCT nft_id) as unique_nfts
            FROM user_nfts
        ''')
        
        return {
            "total_users": users_row["total_users"] if users_row else 0,
            "active_users_24h": users_row["active_users_24h"] if users_row else 0,
            "new_users_24h": users_row["new_users_24h"] if users_row else 0,
            "total_turnover": finance_row["total_turnover"] if finance_row else 0,
            "revenue": finance_row["revenue"] if finance_row else 0,
            "mono_games": mono_row["games"] if mono_row else 0,
            "lucky2_bets": lucky2_row["bets"] if lucky2_row else 0,
            "roulette_spins": roulette_row["spins"] if roulette_row else 0,
            "total_nfts": nft_row["total_nfts"] if nft_row else 0,
            "unique_nfts": nft_row["unique_nfts"] if nft_row else 0,
            "bot_started": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": "24/7"
        }
    
    # Методы для NFT
    
    async def get_random_nft(self) -> Optional[Dict]:
        """Получить случайный NFT"""
        row = await self.pool.fetchrow('''
            SELECT * FROM nfts 
            ORDER BY RANDOM() 
            LIMIT 1
        ''')
        
        return dict(row) if row else None
    
    async def add_nft_to_user(self, user_id: int, nft_id: int) -> bool:
        """Добавить NFT пользователю"""
        try:
            await self.pool.execute('''
                INSERT INTO user_nfts (user_id, nft_id)
                VALUES ($1, $2)
                ON CONFLICT (user_id, nft_id) DO NOTHING
            ''', user_id, nft_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления NFT {nft_id} пользователю {user_id}: {e}")
            return False
    
    async def remove_user_nft(self, user_id: int, nft_id: int) -> bool:
        """Удалить NFT у пользователя"""
        try:
            await self.pool.execute('''
                DELETE FROM user_nfts 
                WHERE user_id = $1 AND nft_id = $2
            ''', user_id, nft_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления NFT {nft_id} у пользователя {user_id}: {e}")
            return False
    
    async def get_user_nft_ids(self, user_id: int) -> List[int]:
        """Получить ID NFT пользователя"""
        rows = await self.pool.fetch('''
            SELECT nft_id FROM user_nfts 
            WHERE user_id = $1
        ''', user_id)
        
        return [row['nft_id'] for row in rows]
    
    async def get_nft_acquisition_date(self, user_id: int, nft_id: int) -> Optional[datetime]:
        """Получить дату получения NFT"""
        row = await self.pool.fetchrow('''
            SELECT acquired_date FROM user_nfts 
            WHERE user_id = $1 AND nft_id = $2
        ''', user_id, nft_id)
        
        return row['acquired_date'] if row else None
    
    async def get_nft_stats(self) -> Dict:
        """Получить статистику по NFT"""
        # Статистика по редкости
        rarity_row = await self.pool.fetchrow('''
            SELECT 
                SUM(CASE WHEN rarity = 'common' THEN 1 ELSE 0 END) as common,
                SUM(CASE WHEN rarity = 'rare' THEN 1 ELSE 0 END) as rare,
                SUM(CASE WHEN rarity = 'epic' THEN 1 ELSE 0 END) as epic,
                SUM(CASE WHEN rarity = 'legendary' THEN 1 ELSE 0 END) as legendary,
                COUNT(*) as total
            FROM nfts
        ''')
        
        # Уникальные владельцы
        owners_row = await self.pool.fetchrow('''
            SELECT COUNT(DISTINCT user_id) as unique_owners
            FROM user_nfts
        ''')
        
        # Топ коллекционеры
        top_collectors = await self.pool.fetch('''
            SELECT u.user_id, u.username, COUNT(un.nft_id) as nft_count
            FROM user_nfts un
            JOIN users u ON u.user_id = un.user_id
            GROUP BY u.user_id, u.username
            ORDER BY nft_count DESC
            LIMIT 5
        ''')
        
        top_collectors_list = []
        for row in top_collectors:
            top_collectors_list.append(f"@{row['username'] or 'user'}: {row['nft_count']} NFT")
        
        return {
            "legendary": rarity_row["legendary"] if rarity_row else 0,
            "epic": rarity_row["epic"] if rarity_row else 0,
            "rare": rarity_row["rare"] if rarity_row else 0,
            "common": rarity_row["common"] if rarity_row else 0,
            "total": rarity_row["total"] if rarity_row else 0,
            "unique_owners": owners_row["unique_owners"] if owners_row else 0,
            "top_collectors": "\n".join(top_collectors_list)
        }
    
    # Методы для инвентаря
    
    async def get_user_boosters(self, user_id: int) -> List[Dict]:
        """Получить бусты пользователя"""
        rows = await self.pool.fetch('''
            SELECT * FROM boosters 
            WHERE user_id = $1 AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC
        ''', user_id)
        
        return [dict(row) for row in rows]
    
    async def get_user_booster(self, user_id: int, booster_id: int) -> Optional[Dict]:
        """Получить конкретный буст"""
        row = await self.pool.fetchrow('''
            SELECT * FROM boosters 
            WHERE user_id = $1 AND booster_id = $2
        ''', user_id, booster_id)
        
        return dict(row) if row else None
    
    async def activate_booster(self, user_id: int, booster_id: int) -> bool:
        """Активировать буст"""
        try:
            await self.pool.execute('''
                UPDATE boosters 
                SET is_active = TRUE,
                    expires_at = CASE 
                        WHEN type IN ('luck_boost', 'win_boost') THEN NOW() + INTERVAL '1 hour'
                        ELSE expires_at
                    END
                WHERE user_id = $1 AND booster_id = $2
            ''', user_id, booster_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка активации буста {booster_id}: {e}")
            return False
    
    async def get_user_collectibles(self, user_id: int) -> List[Dict]:
        """Получить коллекционные предметы пользователя"""
        # В реальном проекте здесь будет отдельная таблица
        return []
    
    async def get_user_utility_items(self, user_id: int) -> List[Dict]:
        """Получить полезные предметы пользователя"""
        # В реальном проекте здесь будет отдельная таблица
        return []
    
    async def add_inventory_history(self, user_id: int, action: str, 
                                   item_type: str, item_id: int,
                                   item_name: str, quantity: int,
                                   metadata: Dict = None,
                                   source_user_id: int = None,
                                   target_user_id: int = None):
        """Добавить запись в историю инвентаря"""
        await self.pool.execute('''
            INSERT INTO inventory_history 
            (user_id, action, item_type, item_id, item_name, quantity, 
             metadata, source_user_id, target_user_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ''', user_id, action, item_type, item_id, item_name, quantity,
            json.dumps(metadata or {}), source_user_id, target_user_id)
    
    async def get_inventory_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Получить историю инвентаря"""
        rows = await self.pool.fetch('''
            SELECT * FROM inventory_history 
            WHERE user_id = $1 
            ORDER BY created_at DESC 
            LIMIT $2
        ''', user_id, limit)
        
        return [dict(row) for row in rows]
    
    # Методы для демо-режима
    
    async def create_demo_session(self, user_id: int) -> str:
        """Создать демо-сессию"""
        import uuid
        session_id = str(uuid.uuid4())
        
        await self.pool.execute('''
            INSERT INTO demo_sessions (session_id, user_id)
            VALUES ($1, $2)
            ON CONFLICT (session_id) DO UPDATE
            SET expires_at = NOW() + INTERVAL '1 hour'
        ''', session_id, user_id)
        
        return session_id
    
    async def get_demo_session(self, session_id: str) -> Optional[Dict]:
        """Получить демо-сессию"""
        row = await self.pool.fetchrow('''
            SELECT * FROM demo_sessions 
            WHERE session_id = $1 AND expires_at > NOW()
        ''', session_id)
        
        return dict(row) if row else None
    
    async def update_demo_balance(self, session_id: str, demo_stars: int = None, 
                                 demo_spins: int = None):
        """Обновить демо-баланс"""
        updates = []
        params = [session_id]
        
        if demo_stars is not None:
            updates.append(f"demo_stars = ${len(params) + 1}")
            params.append(demo_stars)
        
        if demo_spins is not None:
            updates.append(f"demo_spins = ${len(params) + 1}")
            params.append(demo_spins)
        
        if updates:
            query = f'''
                UPDATE demo_sessions 
                SET {', '.join(updates)}
                WHERE session_id = $1
            '''
            await self.pool.execute(query, *params)
    
    # Методы для админов
    
    async def is_admin(self, user_id: int) -> bool:
        """Проверить, является ли пользователь админом"""
        row = await self.pool.fetchrow('''
            SELECT 1 FROM admins WHERE user_id = $1
        ''', user_id)
        
        return bool(row)
    
    async def add_admin(self, user_id: int, role: str = "moderator") -> bool:
        """Добавить админа"""
        try:
            await self.pool.execute('''
                INSERT INTO admins (user_id, role)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET role = EXCLUDED.role
            ''', user_id, role)
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка добавления админа {user_id}: {e}")
            return False
    
    async def get_admin_info(self, user_id: int) -> Optional[Dict]:
        """Получить информацию об админе"""
        row = await self.pool.fetchrow('''
            SELECT * FROM admins WHERE user_id = $1
        ''', user_id)
        
        return dict(row) if row else None
    
    # Вспомогательные методы
    
    async def _add_initial_achievements(self, user_id: int):
        """Добавить начальные достижения"""
        achievements = ["🎮 Первая игра", "💰 Первый депозит", "🏆 Первая победа"]
        
        await self.pool.execute('''
            UPDATE users 
            SET achievements = $2::jsonb
            WHERE user_id = $1
        ''', user_id, json.dumps(achievements))
    
    async def _update_user_level(self, user_id: int):
        """Обновить уровень пользователя"""
        # Простая логика уровня: каждые 10 игр = +1 уровень
        user_info = await self.get_user_info(user_id)
        if user_info:
            total_games = user_info['total_games']
            new_level = min(100, (total_games // 10) + 1)
            
            if new_level > user_info['level']:
                await self.pool.execute('''
                    UPDATE users 
                    SET level = $2, updated_at = NOW()
                    WHERE user_id = $1
                ''', user_id, new_level)
    
    async def get_user_profile(self, user_id: int) -> Dict:
        """Получить профиль пользователя"""
        user_info = await self.get_user_info(user_id)
        if not user_info:
            return {}
        
        # Рассчитываем дополнительные метрики
        days_in_game = (datetime.now() - user_info['created_at']).days
        achievements = user_info.get('achievements', [])
        
        return {
            "user_id": user_info['user_id'],
            "username": user_info['username'],
            "first_name": user_info['first_name'],
            "level": user_info['level'],
            "rating": user_info['rating'],
            "total_games": user_info['total_games'],
            "total_won": user_info['total_won'],
            "max_win": user_info.get('max_win', 0),
            "created_at": user_info['created_at'],
            "last_active": user_info['last_active'],
            "days_in_game": days_in_game,
            "achievements": achievements if isinstance(achievements, list) else []
        }
    
    async def get_registration_date(self, user_id: int) -> str:
        """Получить дату регистрации"""
        row = await self.pool.fetchrow('''
            SELECT created_at FROM users WHERE user_id = $1
        ''', user_id)
        
        if row:
            return row['created_at'].strftime("%d.%m.%Y")
        return "Неизвестно"
