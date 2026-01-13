import random
import logging
from typing import Dict, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class MonoGame:
    """Игра Моно - увеличение шанса выигрыша свайпом"""
    
    def __init__(self, db):
        self.db = db
        
        # ОБНОВЛЕНО: Настройки шансов, множителей и МИНИМАЛЬНЫХ СТАВОК
        self.chance_settings = [
            {"chance": 1, "multiplier": 100.0, "min_bet_stars": 4, "color": "#FF0000", "label": "1% - 100x (мин. 4 stars)"},
            {"chance": 3, "multiplier": 33.0, "min_bet_stars": 12, "color": "#FF4500", "label": "3% - 33x (мин. 12 stars)"},
            {"chance": 5, "multiplier": 20.0, "min_bet_stars": 20, "color": "#FF8C00", "label": "5% - 20x (мин. 20 stars)"},
            {"chance": 7, "multiplier": 14.3, "min_bet_stars": 28, "color": "#FFD700", "label": "7% - 14.3x (мин. 28 stars)"},
            {"chance": 10, "multiplier": 10.0, "min_bet_stars": 40, "color": "#ADFF2F", "label": "10% - 10x (мин. 40 stars)"},
            {"chance": 15, "multiplier": 6.67, "min_bet_stars": 60, "color": "#32CD32", "label": "15% - 6.67x (мин. 60 stars)"},
            {"chance": 20, "multiplier": 5.0, "min_bet_stars": 80, "color": "#00FA9A", "label": "20% - 5x (мин. 80 stars)"},
            {"chance": 25, "multiplier": 4.0, "min_bet_stars": 100, "color": "#00CED1", "label": "25% - 4x (мин. 100 stars)"},
            {"chance": 30, "multiplier": 3.33, "min_bet_stars": 120, "color": "#1E90FF", "label": "30% - 3.33x (мин. 120 stars)"},
            {"chance": 40, "multiplier": 2.5, "min_bet_stars": 160, "color": "#4169E1", "label": "40% - 2.5x (мин. 160 stars)"},
            {"chance": 50, "multiplier": 2.0, "min_bet_stars": 200, "color": "#8A2BE2", "label": "50% - 2x (мин. 200 stars)"},
            {"chance": 65, "multiplier": 1.54, "min_bet_stars": 260, "color": "#DA70D6", "label": "65% - 1.54x (мин. 260 stars)"}
        ]
        
        # Конвертация: 1 спин = 50 stars
        self.spin_to_stars = 50
        
        # NFT шанс: 0.5% при выигрыше
        self.nft_chance = 0.5
        
        # Максимальная ставка
        self.max_bet_spins = 100  # 100 спинов = 5000 stars
    
    async def spin(self, user_id: int, chance_percentage: int, bet_spins: int = 1) -> Dict:
        """
        Выполнить спин в игре Моно
        
        Args:
            user_id: ID пользователя
            chance_percentage: Выбранный шанс (1-65%)
            bet_spins: Количество спинов для ставки
        
        Returns:
            Результат спина
        """
        # Получаем настройки для выбранного шанса
        setting = self._get_setting_for_chance(chance_percentage)
        
        # ОБНОВЛЕНО: Проверяем минимальную ставку в stars
        bet_stars = bet_spins * self.spin_to_stars
        min_bet_stars = setting["min_bet_stars"]
        
        if bet_stars < min_bet_stars:
            return {
                "success": False,
                "error": f"Минимальная ставка для {chance_percentage}%: {min_bet_stars} stars ({min_bet_stars // self.spin_to_stars} спин(ов))",
                "required_min": min_bet_stars,
                "current_bet": bet_stars
            }
        
        # Проверяем максимальную ставку
        max_bet_stars = self.max_bet_spins * self.spin_to_stars
        if bet_stars > max_bet_stars:
            return {
                "success": False,
                "error": f"Максимальная ставка: {max_bet_stars} stars ({self.max_bet_spins} спинов)",
                "max_allowed": max_bet_stars,
                "current_bet": bet_stars
            }
        
        # Проверяем баланс спинов
        current_spins = await self.db.get_spins_balance(user_id)
        if current_spins < bet_spins:
            return {
                "success": False,
                "error": "Недостаточно спинов",
                "balance": current_spins,
                "required": bet_spins
            }
        
        # Проверяем выигрыш
        win_number = random.randint(1, 100)
        won = win_number <= setting["chance"]
        
        # Рассчитываем результат
        if won:
            # Выигрыш
            win_multiplier = setting["multiplier"]
            win_spins = bet_spins * win_multiplier
            
            # Начисляем выигрыш (уже минус использованные спины)
            net_win_spins = win_spins - bet_spins
            await self.db.update_spins_balance(user_id, net_win_spins)
            
            # Проверяем NFT
            nft_awarded = None
            if random.randint(1, 1000) <= 5:  # 0.5% шанс
                nft_awarded = await self._award_nft(user_id)
                
            # Конвертируем в stars для отображения
            win_stars = win_spins * self.spin_to_stars
            bet_stars_used = bet_spins * self.spin_to_stars
        else:
            # Проигрыш - списываем ставку
            await self.db.update_spins_balance(user_id, -bet_spins)
            win_multiplier = 0
            win_spins = 0
            win_stars = 0
            bet_stars_used = bet_spins * self.spin_to_stars
            nft_awarded = None
        
        # Сохраняем историю
        await self.db.add_game_history(
            user_id=user_id,
            game_type="mono",
            bet_amount=bet_spins,
            bet_stars=bet_stars_used,
            chance=chance_percentage,
            won=won,
            win_amount=win_spins,
            win_stars=win_stars,
            win_multiplier=win_multiplier,
            nft_awarded=nft_awarded is not None,
            min_bet_required=min_bet_stars
        )
        
        # Обновляем статистику
        await self.db.update_user_stats(
            user_id=user_id,
            games_played=1,
            total_wagered=bet_stars_used,
            total_won=win_stars
        )
        
        # Возвращаем результат
        return {
            "success": True,
            "won": won,
            "chance": chance_percentage,
            "win_number": win_number,
            "multiplier": win_multiplier,
            "win_spins": win_spins,
            "win_stars": win_stars,
            "bet_spins": bet_spins,
            "bet_stars": bet_stars_used,
            "min_bet_required": min_bet_stars,
            "nft_awarded": nft_awarded,
            "balance": await self.db.get_spins_balance(user_id),
            "balance_stars": await self.db.get_stars_balance(user_id),
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
            "total_wagered_stars": stats.get("total_wagered_stars", 0),
            "total_won_stars": stats.get("total_won_stars", 0),
            "net_profit_stars": stats.get("total_won_stars", 0) - stats.get("total_wagered_stars", 0),
            "max_win": stats.get("max_win", 0),
            "nfts_won": stats.get("nfts_won", 0),
            "favorite_chance": stats.get("favorite_chance", 1),
            "total_min_bet_required": stats.get("total_min_bet_required", 0)
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
            "total_wagered_stars": stats.get("total_wagered_stars", 0),
            "total_won_stars": stats.get("total_won_stars", 0),
            "total_nfts": stats.get("total_nfts", 0),
            "avg_chance": stats.get("avg_chance", 1),
            "popular_chances": stats.get("popular_chances", []),
            "total_min_bet_collected": stats.get("total_min_bet_collected", 0)
        }
    
    def get_chance_settings(self) -> List[Dict]:
        """Получить все настройки шансов"""
        return self.chance_settings
    
    def calculate_payout(self, chance: int, bet_spins: int = 1) -> Dict:
        """Рассчитать потенциальный выигрыш"""
        setting = self._get_setting_for_chance(chance)
        bet_stars = bet_spins * self.spin_to_stars
        
        # Проверяем минимальную ставку
        min_bet_stars = setting["min_bet_stars"]
        is_valid_bet = bet_stars >= min_bet_stars
        
        win_spins = bet_spins * setting["multiplier"]
        win_stars = win_spins * self.spin_to_stars
        
        return {
            "chance": chance,
            "multiplier": setting["multiplier"],
            "bet_spins": bet_spins,
            "bet_stars": bet_stars,
            "min_bet_required": min_bet_stars,
            "is_valid_bet": is_valid_bet,
            "potential_win_spins": win_spins,
            "potential_win_stars": win_stars,
            "profit_spins": win_spins - bet_spins,
            "profit_stars": win_stars - bet_stars,
            "color": setting["color"]
        }
    
    def get_min_bet_for_chance(self, chance: int) -> int:
        """Получить минимальную ставку для шанса"""
        setting = self._get_setting_for_chance(chance)
        return setting["min_bet_stars"]
    
    def get_min_spins_for_chance(self, chance: int) -> int:
        """Получить минимальное количество спинов для шанса"""
        min_stars = self.get_min_bet_for_chance(chance)
        # Округляем вверх до целого спина
        return (min_stars + self.spin_to_stars - 1) // self.spin_to_stars
    
    async def demo_spin(self, chance_percentage: int, bet_spins: int = 1) -> Dict:
        """Демо-спин (без сохранения в БД)"""
        setting = self._get_setting_for_chance(chance_percentage)
        
        # Проверяем минимальную ставку
        bet_stars = bet_spins * self.spin_to_stars
        min_bet_stars = setting["min_bet_stars"]
        
        if bet_stars < min_bet_stars:
            return {
                "success": False,
                "error": f"Минимальная ставка: {min_bet_stars} stars",
                "min_required": min_bet_stars
            }
        
        win_number = random.randint(1, 100)
        won = win_number <= setting["chance"]
        
        if won:
            win_multiplier = setting["multiplier"]
            win_spins = bet_spins * win_multiplier
            win_stars = win_spins * self.spin_to_stars
            
            # Демо NFT шанс
            nft_awarded = None
            if random.randint(1, 1000) <= 5:
                nft_awarded = {"id": 999, "name": "Демо NFT", "rarity": "demo"}
        else:
            win_multiplier = 0
            win_spins = 0
            win_stars = 0
            nft_awarded = None
        
        return {
            "success": True,
            "won": won,
            "chance": chance_percentage,
            "win_number": win_number,
            "multiplier": win_multiplier,
            "win_spins": win_spins,
            "win_stars": win_stars,
            "bet_spins": bet_spins,
            "bet_stars": bet_stars,
            "min_bet_required": min_bet_stars,
            "nft_awarded": nft_awarded,
            "setting": setting
        }
    
    def get_bet_recommendations(self, chance: int) -> List[Dict]:
        """Получить рекомендованные ставки для шанса"""
        setting = self._get_setting_for_chance(chance)
        min_spins = self.get_min_spins_for_chance(chance)
        
        recommendations = []
        
        # Базовые рекомендации
        base_bets = [
            {"spins": min_spins, "label": f"Мин. ({min_spins} спин.)"},
            {"spins": min_spins * 2, "label": f"{min_spins * 2} спинов"},
            {"spins": min_spins * 5, "label": f"{min_spins * 5} спинов"},
            {"spins": min_spins * 10, "label": f"{min_spins * 10} спинов"}
        ]
        
        for bet in base_bets:
            if bet["spins"] <= self.max_bet_spins:
                bet_stars = bet["spins"] * self.spin_to_stars
                win_spins = bet["spins"] * setting["multiplier"]
                win_stars = win_spins * self.spin_to_stars
                
                recommendations.append({
                    "spins": bet["spins"],
                    "stars": bet_stars,
                    "label": bet["label"],
                    "potential_win_spins": win_spins,
                    "potential_win_stars": win_stars,
                    "multiplier": setting["multiplier"]
                })
        
        return recommendations
