import random
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class Lucky2Game:
    """Игра Lucky2 - ставки на цвета"""
    
    def __init__(self, db):
        self.db = db
        
        # Настройки цветов и вероятностей
        self.colors = {
            "blue": {
                "name": "Синий",
                "emoji": "🔵",
                "chance": 60,  # 60%
                "multiplier": 2.0,
                "color": "#1E90FF",
                "description": "Частый, но x2"
            },
            "red": {
                "name": "Красный",
                "emoji": "🔴", 
                "chance": 5,   # 5% - редкий
                "multiplier": 5.0,
                "color": "#DC143C",
                "description": "Редкий, но x5!"
            },
            "purple": {
                "name": "Фиолетовый",
                "emoji": "🟣",
                "chance": 35,  # 35%
                "multiplier": 2.0,
                "color": "#8A2BE2",
                "description": "Средний, x2"
            }
        }
        
        # Настройки ставок
        self.min_bet = 25  # Минимум 25 stars
        self.max_bet = 1000  # Максимум 1000 stars
        self.bet_steps = [25, 50, 100, 250, 500, 750, 1000]
        
        # Комиссия казино (1%)
        self.house_edge = 0.01
    
    async def bet(self, user_id: int, color: str, amount: int) -> Dict:
        """
        Сделать ставку в Lucky2
        
        Args:
            user_id: ID пользователя
            color: Цвет для ставки (blue/red/purple)
            amount: Сумма ставки в stars
        
        Returns:
            Результат ставки
        """
        # Проверяем валидность цвета
        if color not in self.colors:
            return {
                "success": False,
                "error": f"Неверный цвет. Доступно: {', '.join(self.colors.keys())}"
            }
        
        # Проверяем сумму ставки
        if amount < self.min_bet:
            return {
                "success": False,
                "error": f"Минимальная ставка: {self.min_bet} stars"
            }
        
        if amount > self.max_bet:
            return {
                "success": False,
                "error": f"Максимальная ставка: {self.max_bet} stars"
            }
        
        # Проверяем баланс
        current_balance = await self.db.get_stars_balance(user_id)
        if current_balance < amount:
            return {
                "success": False,
                "error": f"Недостаточно stars. Нужно: {amount}, есть: {current_balance}"
            }
        
        # Списываем ставку
        await self.db.update_stars_balance(user_id, -amount)
        
        # Определяем выигрышный цвет
        winning_color = self._spin_wheel()
        color_settings = self.colors[color]
        
        # Проверяем победу
        won = winning_color == color
        
        # Рассчитываем результат
        if won:
            # Выигрыш с учетом множителя и комиссии
            win_multiplier = color_settings["multiplier"]
            gross_win = amount * win_multiplier
            commission = gross_win * self.house_edge
            net_win = gross_win - commission
            
            # Начисляем выигрыш
            await self.db.update_stars_balance(user_id, net_win)
            
            win_amount = net_win
        else:
            # Проигрыш - деньги остаются у казино
            win_multiplier = 0
            win_amount = 0
            
            # Деньги идут владельцу бота (уже списаны у игрока)
            # Владелец получает их автоматически через update_stars_balance
        
        # Сохраняем историю
        await self.db.add_bet_history(
            user_id=user_id,
            game_type="lucky2",
            bet_color=color,
            bet_amount=amount,
            winning_color=winning_color,
            won=won,
            win_amount=win_amount,
            win_multiplier=win_multiplier
        )
        
        # Обновляем статистику
        await self.db.update_user_stats(
            user_id=user_id,
            games_played=1,
            total_wagered=amount,
            total_won=win_amount
        )
        
        # Возвращаем результат
        return {
            "success": True,
            "won": won,
            "bet_color": color,
            "bet_amount": amount,
            "winning_color": winning_color,
            "winning_color_name": self.colors[winning_color]["name"],
            "multiplier": win_multiplier,
            "win_amount": win_amount,
            "balance": await self.db.get_stars_balance(user_id),
            "color_settings": color_settings
        }
    
    def _spin_wheel(self) -> str:
        """Вращение колеса - определение выигрышного цвета"""
        # Создаем взвешенный список на основе шансов
        weighted_colors = []
        for color, settings in self.colors.items():
            weighted_colors.extend([color] * settings["chance"])
        
        # Выбираем случайный цвет
        return random.choice(weighted_colors)
    
    async def multi_bet(self, user_id: int, bets: Dict[str, int]) -> Dict:
        """
        Множественная ставка на несколько цветов
        
        Args:
            user_id: ID пользователя
            bets: Словарь {цвет: сумма}
        
        Returns:
            Результаты ставок
        """
        total_bet = sum(bets.values())
        
        # Проверяем баланс
        current_balance = await self.db.get_stars_balance(user_id)
        if current_balance < total_bet:
            return {
                "success": False,
                "error": f"Недостаточно stars. Нужно: {total_bet}, есть: {current_balance}"
            }
        
        # Списываем общую сумму
        await self.db.update_stars_balance(user_id, -total_bet)
        
        # Определяем выигрышный цвет
        winning_color = self._spin_wheel()
        
        results = []
        total_win = 0
        
        for color, amount in bets.items():
            if color not in self.colors:
                continue
            
            color_settings = self.colors[color]
            won = winning_color == color
            
            if won:
                win_multiplier = color_settings["multiplier"]
                gross_win = amount * win_multiplier
                commission = gross_win * self.house_edge
                net_win = gross_win - commission
                
                win_amount = net_win
                total_win += net_win
            else:
                win_multiplier = 0
                win_amount = 0
            
            results.append({
                "color": color,
                "bet_amount": amount,
                "won": won,
                "win_multiplier": win_multiplier,
                "win_amount": win_amount
            })
        
        # Начисляем общий выигрыш
        if total_win > 0:
            await self.db.update_stars_balance(user_id, total_win)
        
        # Сохраняем историю
        await self.db.add_multi_bet_history(
            user_id=user_id,
            bets=bets,
            winning_color=winning_color,
            total_bet=total_bet,
            total_win=total_win
        )
        
        return {
            "success": True,
            "winning_color": winning_color,
            "winning_color_name": self.colors[winning_color]["name"],
            "total_bet": total_bet,
            "total_win": total_win,
            "results": results,
            "balance": await self.db.get_stars_balance(user_id),
            "net_profit": total_win - total_bet
        }
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Статистика пользователя по Lucky2"""
        stats = await self.db.get_user_game_stats(user_id, "lucky2")
        
        total_bets = stats.get("total_bets", 0)
        wins = stats.get("wins", 0)
        
        return {
            "total_bets": total_bets,
            "wins": wins,
            "losses": total_bets - wins,
            "win_rate": (wins / total_bets * 100) if total_bets > 0 else 0,
            "total_wagered": stats.get("total_wagered", 0),
            "total_won": stats.get("total_won", 0),
            "net_profit": stats.get("total_won", 0) - stats.get("total_wagered", 0),
            "max_win": stats.get("max_win", 0),
            "favorite_color": stats.get("favorite_color", "blue"),
            "avg_bet": stats.get("avg_bet", 0)
        }
    
    async def get_statistics(self) -> Dict:
        """Общая статистика игры Lucky2"""
        stats = await self.db.get_game_type_stats("lucky2")
        
        total_bets = stats.get("total_bets", 0)
        total_wins = stats.get("total_wins", 0)
        
        # Статистика по цветам
        color_stats = {}
        for color in self.colors:
            color_stats[color] = {
                "total_bets": stats.get(f"{color}_bets", 0),
                "wins": stats.get(f"{color}_wins", 0),
                "total_wagered": stats.get(f"{color}_wagered", 0),
                "total_paid": stats.get(f"{color}_paid", 0)
            }
        
        return {
            "total_bets": total_bets,
            "total_wins": total_wins,
            "total_losses": total_bets - total_wins,
            "win_rate": (total_wins / total_bets * 100) if total_bets > 0 else 0,
            "total_turnover": stats.get("total_turnover", 0),
            "total_payout": stats.get("total_payout", 0),
            "house_profit": stats.get("total_turnover", 0) - stats.get("total_payout", 0),
            "rtp": (stats.get("total_payout", 0) / stats.get("total_turnover", 0) * 100) 
                    if stats.get("total_turnover", 0) > 0 else 0,
            "color_stats": color_stats,
            "avg_bet": stats.get("avg_bet", 0)
        }
    
    def get_color_info(self, color: str) -> Dict:
        """Получить информацию о цвете"""
        return self.colors.get(color, {})
    
    def get_all_colors(self) -> Dict:
        """Получить информацию о всех цветах"""
        return self.colors
    
    def get_bet_steps(self) -> List[int]:
        """Получить доступные шаги ставок"""
        return self.bet_steps
    
    def calculate_expected_value(self, color: str, amount: int) -> float:
        """Рассчитать математическое ожидание ставки"""
        if color not in self.colors:
            return 0
        
        settings = self.colors[color]
        win_probability = settings["chance"] / 100
        win_amount = amount * settings["multiplier"] * (1 - self.house_edge)
        
        expected_win = win_probability * win_amount
        expected_loss = (1 - win_probability) * amount
        
        return expected_win - expected_loss
    
    async def demo_bet(self, color: str, amount: int) -> Dict:
        """Демо-ставка (без сохранения в БД)"""
        if color not in self.colors:
            return {"error": "Неверный цвет"}
        
        winning_color = self._spin_wheel()
        color_settings = self.colors[color]
        
        won = winning_color == color
        
        if won:
            win_multiplier = color_settings["multiplier"]
            gross_win = amount * win_multiplier
            commission = gross_win * self.house_edge
            net_win = gross_win - commission
            
            win_amount = net_win
        else:
            win_multiplier = 0
            win_amount = 0
        
        return {
            "won": won,
            "bet_color": color,
            "bet_amount": amount,
            "winning_color": winning_color,
            "winning_color_name": self.colors[winning_color]["name"],
            "multiplier": win_multiplier,
            "win_amount": win_amount,
            "net_profit": win_amount - amount,
            "color_settings": color_settings
        }
