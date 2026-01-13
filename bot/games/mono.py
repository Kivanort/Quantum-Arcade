import random
import logging
from typing import Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class MonoGame:
    """Игра Моно - увеличение шанса выигрыша свайпом"""
    
    def __init__(self, db):
        self.db = db
        
        # Настройки шансов и множителей
        self.chance_settings = [
            {"chance": 1, "multiplier": 100.0, "color": "#FF0000", "label": "1% - 100x"},
            {"chance": 3, "multiplier": 33.0, "color": "#FF4500", "label": "3% - 33x"},
            {"chance": 5, "multiplier": 20.0, "color": "#FF8C00", "label": "5% - 20x"},
            {"chance": 7, "multiplier": 14.3, "color": "#FFD700", "label": "7% - 14.3x"},
            {"chance": 10, "multiplier": 10.0, "color": "#ADFF2F", "label": "10% - 10x"},
            {"chance": 15, "multiplier": 6.67, "color": "#32CD32", "label": "15% - 6.67x"},
            {"chance": 20, "multiplier": 5.0, "color": "#00FA9A", "label": "20% - 5x"},
            {"chance": 25, "multiplier": 4.0, "color": "#00CED1", "label": "25% - 4x"},
            {"chance": 30, "multiplier": 3.33, "color": "#1E90FF", "label": "30% - 3.33x"},
            {"chance": 40, "multiplier": 2.5, "color": "#4169E1", "label": "40% - 2.5x"},
            {"chance": 50, "multiplier": 2.0, "color": "#8A2BE2", "label": "50% - 2x"},
            {"chance": 65, "multiplier": 1.54, "color": "#DA70D6", "label": "65% - 1.54x"}
        ]
        
        # NFT шанс: 0.5% при выигрыше
        self.nft_chance = 0.5
    
    async def spin(self, user_id: int, chance_percentage: int, bet_amount: int = 1) -> Dict:
        """
        Выполнить спин в игре Моно
        
        Args:
            user_id: ID пользователя
            chance_percentage: Выбранный шанс (1-65%)
            bet_amount: Количество спинов для ставки
        
        Returns:
            Результат спина
        """
        # Проверяем баланс
        current_spins = await self.db.get_spins_balance(user_id)
        if current_spins < bet_amount:
            return {
                "success": False,
                "error": "Недостаточно спинов",
                "balance": current_spins
            }
        
        # Находим настройки для выбранного шанса
        setting = self._get_setting_for_chance(chance_percentage)
        
        # Проверяем выигрыш
        win_number = random.randint(1, 100)
        won = win_number <= setting["chance"]
        
        # Рассчитываем результат
        if won:
            # Выигрыш
            win_multiplier = setting["multiplier"]
            win_amount = bet_amount * win_multiplier
            
            # Начисляем выигрыш (уже минус использованный спин)
            net_win = win_amount - bet_amount
            await self.db.update_spins_balance(user_id, net_win)
            
            # Проверяем NFT
            nft_awarded = None
            if random.randint(1, 1000) <= 5:  # 0.5% шанс
                nft_awarded = await self._award_nft(user_id)
        else:
            # Проигрыш - списываем ставку
            await self.db.update_spins_balance(user_id, -bet_amount)
            win_multiplier = 0
            win_amount = 0
            nft_awarded = None
        
        # Сохраняем историю
        await self.db.add_game_history(
            user_id=user_id,
            game_type="mono",
            bet_amount=bet_amount,
            chance=chance_percentage,
            won=won,
            win_amount=win_amount,
            win_multiplier=win_multiplier,
            nft_awarded=nft_awarded is not None
        )
        
        # Обновляем статистику
        await self.db.update_user_stats(
            user_id=user_id,
            games_played=1,
            total_wagered=bet_amount,
            total_won=win_amount
        )
        
        # Возвращаем результат
        return {
            "success": True,
            "won": won,
            "chance": chance_percentage,
            "win_number": win_number,
            "multiplier": win_multiplier,
            "win_amount": win_amount,
            "nft_awarded": nft_awarded,
            "balance": await self.db.get_spins_balance(user_id),
            "setting": setting
        }
    
    def _get_setting_for_chance(self, chance: int) -> Dict:
        """Получить настройки для выбранного шанса"""
        for setting in self.chance_settings:
            if setting["chance"] == chance:
                return setting
        
        # Если шанс не найден, берем ближайший
        closest = min(self.chance_settings, key=lambda x: abs(x["chance"] - chance))
        return closest
    
    async def _award_nft(self, user_id: int) -> Dict:
        """Выдать случайный NFT"""
        # Получаем случайный NFT из базы
        nft = await self.db.get_random_nft()
        if nft:
            await self.db.add_nft_to_user(user_id, nft["id"])
            return nft
        return None
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Получить статистику пользователя по игре Моно"""
        stats = await self.db.get_user_game_stats(user_id, "mono")
        
        total_games = stats.get("total_games", 0)
        wins = stats.get("wins", 0)
        
        return {
            "total_games": total_games,
            "wins": wins,
            "losses": total_games - wins,
            "win_rate": (wins / total_games * 100) if total_games > 0 else 0,
            "total_wagered": stats.get("total_wagered", 0),
            "total_won": stats.get("total_won", 0),
            "net_profit": stats.get("total_won", 0) - stats.get("total_wagered", 0),
            "max_win": stats.get("max_win", 0),
            "nfts_won": stats.get("nfts_won", 0),
            "favorite_chance": stats.get("favorite_chance", 10)
        }
    
    async def get_statistics(self) -> Dict:
        """Общая статистика игры Моно"""
        stats = await self.db.get_game_type_stats("mono")
        
        total_games = stats.get("total_games", 0)
        total_wins = stats.get("total_wins", 0)
        
        return {
            "total_games": total_games,
            "wins": total_wins,
            "losses": total_games - total_wins,
            "win_rate": (total_wins / total_games * 100) if total_games > 0 else 0,
            "total_wagered": stats.get("total_wagered", 0),
            "total_won": stats.get("total_won", 0),
            "total_nfts": stats.get("total_nfts", 0),
            "avg_chance": stats.get("avg_chance", 10),
            "popular_chances": stats.get("popular_chances", [])
        }
    
    def get_chance_settings(self) -> List[Dict]:
        """Получить все настройки шансов"""
        return self.chance_settings
    
    def calculate_payout(self, chance: int, bet_amount: int = 1) -> float:
        """Рассчитать потенциальный выигрыш"""
        setting = self._get_setting_for_chance(chance)
        return bet_amount * setting["multiplier"]
    
    async def demo_spin(self, chance_percentage: int, bet_amount: int = 1) -> Dict:
        """Демо-спин (без сохранения в БД)"""
        setting = self._get_setting_for_chance(chance_percentage)
        
        win_number = random.randint(1, 100)
        won = win_number <= setting["chance"]
        
        if won:
            win_multiplier = setting["multiplier"]
            win_amount = bet_amount * win_multiplier
            
            # Демо NFT шанс
            nft_awarded = None
            if random.randint(1, 1000) <= 5:
                nft_awarded = {"id": 999, "name": "Демо NFT", "rarity": "demo"}
        else:
            win_multiplier = 0
            win_amount = 0
            nft_awarded = None
        
        return {
            "won": won,
            "chance": chance_percentage,
            "win_number": win_number,
            "multiplier": win_multiplier,
            "win_amount": win_amount,
            "nft_awarded": nft_awarded,
            "setting": setting
        }
