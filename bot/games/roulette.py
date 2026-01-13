import random
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class RouletteGame:
    """Классическая рулетка (как в оригинальном Rolls Game)"""
    
    def __init__(self, db):
        self.db = db
        
        # Секторы рулетки (16 секторов)
        self.sectors = [
            # Сектор, Множитель, Вероятность, Цвет, Описание
            {"id": 0, "multiplier": 0, "probability": 50.0, "color": "#2D2D3A", "label": "0x", "type": "lose"},
            {"id": 1, "multiplier": 0, "probability": 14.0, "color": "#3A3A4A", "label": "0x", "type": "lose"},
            {"id": 2, "multiplier": 1.5, "probability": 12.0, "color": "#2E6DA4", "label": "1.5x", "type": "win"},
            {"id": 3, "multiplier": 0, "probability": 8.0, "color": "#2D2D3A", "label": "0x", "type": "lose"},
            {"id": 4, "multiplier": 2.0, "probability": 6.0, "color": "#2E8B57", "label": "2x", "type": "win"},
            {"id": 5, "multiplier": 0, "probability": 4.0, "color": "#3A3A4A", "label": "0x", "type": "lose"},
            {"id": 6, "multiplier": 3.0, "probability": 3.0, "color": "#8A2BE2", "label": "3x", "type": "win"},
            {"id": 7, "multiplier": 0, "probability": 1.5, "color": "#2D2D3A", "label": "0x", "type": "lose"},
            {"id": 8, "multiplier": 5.0, "probability": 1.0, "color": "#FF8C00", "label": "5x", "type": "win"},
            {"id": 9, "multiplier": 0, "probability": 0.3, "color": "#3A3A4A", "label": "0x", "type": "lose"},
            {"id": 10, "multiplier": 10.0, "probability": 0.2, "color": "#DC143C", "label": "10x", "type": "win", "jackpot": True}
        ]
        
        # NFT награда: каждые 5 спинов
        self.nft_spin_threshold = 5
        self.nft_chance = 100  # 100% при достижении порога
    
    async def spin(self, user_id: int) -> Dict:
        """
        Выполнить спин рулетки
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Результат спина
        """
        # Проверяем баланс спинов
        current_spins = await self.db.get_spins_balance(user_id)
        if current_spins < 1:
            return {
                "success": False,
                "error": "Недостаточно спинов",
                "balance": current_spins
            }
        
        # Списываем 1 спин
        await self.db.update_spins_balance(user_id, -1)
        
        # Выбираем случайный сектор
        sector = self._select_sector()
        
        # Проверяем выигрыш
        won = sector["multiplier"] > 0
        
        # Рассчитываем выигрыш
        if won:
            win_multiplier = sector["multiplier"]
            win_amount = 1 * win_multiplier  # 1 спин * множитель
            
            # Начисляем выигрыш (уже минус использованный спин)
            net_win = win_amount - 1
            await self.db.update_spins_balance(user_id, net_win)
            
            # Проверяем начисление NFT (каждые 5 спинов)
            total_spins_used = await self.db.get_total_spins_used(user_id)
            nft_awarded = None
            
            if total_spins_used % self.nft_spin_threshold == 0:
                nft_awarded = await self._award_nft(user_id)
        else:
            win_multiplier = 0
            win_amount = 0
            nft_awarded = None
        
        # Сохраняем историю
        await self.db.add_spin_history(
            user_id=user_id,
            game_type="roulette",
            result_sector=sector["id"],
            won=won,
            win_amount=win_amount,
            win_multiplier=win_multiplier,
            nft_awarded=nft_awarded is not None
        )
        
        # Обновляем статистику
        await self.db.update_user_stats(
            user_id=user_id,
            games_played=1,
            total_wagered=1,
            total_won=win_amount
        )
        
        # Возвращаем результат
        return {
            "success": True,
            "won": won,
            "sector": sector,
            "multiplier": win_multiplier,
            "win_amount": win_amount,
            "nft_awarded": nft_awarded,
            "balance": await self.db.get_spins_balance(user_id),
            "total_spins_used": total_spins_used + 1,
            "next_nft_in": self.nft_spin_threshold - ((total_spins_used + 1) % self.nft_spin_threshold)
        }
    
    def _select_sector(self) -> Dict:
        """Выбрать случайный сектор с учетом вероятностей"""
        # Создаем взвешенный список
        weighted_sectors = []
        for sector in self.sectors:
            # Умножаем вероятность на 10 для целых чисел
            weight = int(sector["probability"] * 10)
            weighted_sectors.extend([sector] * weight)
        
        return random.choice(weighted_sectors)
    
    async def _award_nft(self, user_id: int) -> Dict:
        """Выдать NFT за каждые 5 спинов"""
        nft = await self.db.get_random_nft()
        if nft:
            await self.db.add_nft_to_user(user_id, nft["id"])
            return nft
        return None
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Статистика пользователя по рулетке"""
        stats = await self.db.get_user_game_stats(user_id, "roulette")
        
        total_spins = stats.get("total_spins", 0)
        wins = stats.get("wins", 0)
        
        return {
            "total_spins": total_spins,
            "wins": wins,
            "losses": total_spins - wins,
            "win_rate": (wins / total_spins * 100) if total_spins > 0 else 0,
            "total_wagered": stats.get("total_wagered", 0),
            "total_won": stats.get("total_won", 0),
            "net_profit": stats.get("total_won", 0) - stats.get("total_wagered", 0),
            "max_win": stats.get("max_win", 0),
            "max_multiplier": stats.get("max_multiplier", 0),
            "nfts_won": stats.get("nfts_won", 0),
            "spins_to_next_nft": self.nft_spin_threshold - (total_spins % self.nft_spin_threshold),
            "total_nft_eligible": total_spins // self.nft_spin_threshold
        }
    
    async def get_statistics(self) -> Dict:
        """Общая статистика рулетки"""
        stats = await self.db.get_game_type_stats("roulette")
        
        total_spins = stats.get("total_spins", 0)
        total_wins = stats.get("total_wins", 0)
        
        # Статистика по секторам
        sector_stats = {}
        for sector in self.sectors:
            sector_stats[sector["id"]] = {
                "hits": stats.get(f"sector_{sector['id']}_hits", 0),
                "total_paid": stats.get(f"sector_{sector['id']}_paid", 0)
            }
        
        return {
            "total_spins": total_spins,
            "wins": total_wins,
            "losses": total_spins - total_wins,
            "win_rate": (total_wins / total_spins * 100) if total_spins > 0 else 0,
            "total_wagered": stats.get("total_wagered", 0),
            "total_won": stats.get("total_won", 0),
            "total_nfts": stats.get("total_nfts", 0),
            "avg_multiplier": stats.get("avg_multiplier", 0),
            "jackpot_hits": stats.get("jackpot_hits", 0),
            "sector_stats": sector_stats
        }
    
    def get_sectors(self) -> List[Dict]:
        """Получить все секторы рулетки"""
        return self.sectors
    
    def get_sector_info(self, sector_id: int) -> Dict:
        """Получить информацию о секторе"""
        for sector in self.sectors:
            if sector["id"] == sector_id:
                return sector
        return None
    
    async def demo_spin(self) -> Dict:
        """Демо-спин (без сохранения в БД)"""
        sector = self._select_sector()
        
        won = sector["multiplier"] > 0
        
        if won:
            win_multiplier = sector["multiplier"]
            win_amount = 1 * win_multiplier
            
            # Демо NFT (симуляция)
            nft_awarded = None
            if random.random() < 0.2:  # 20% шанс в демо
                nft_awarded = {"id": 999, "name": "Демо NFT", "rarity": "demo"}
        else:
            win_multiplier = 0
            win_amount = 0
            nft_awarded = None
        
        return {
            "won": won,
            "sector": sector,
            "multiplier": win_multiplier,
            "win_amount": win_amount,
            "nft_awarded": nft_awarded
        }
    
    def calculate_rtp(self) -> float:
        """Рассчитать RTP (Return to Player) рулетки"""
        total_rtp = 0
        for sector in self.sectors:
            probability = sector["probability"] / 100
            multiplier = sector["multiplier"]
            total_rtp += probability * multiplier
        
        return total_rtp * 100  # в процентах
