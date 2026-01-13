import random
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class InventorySystem:
    """Система инвентаря пользователя"""
    
    def __init__(self, db):
        self.db = db
        self.nfts = self._load_nfts()
        self.categories = self._load_categories()
    
    def _load_nfts(self) -> List[Dict]:
        """Загрузить список NFT из базы/файла"""
        # В реальном проекте загружаем из БД
        # Здесь примерный список
        return [
            # Common (обычные) - 50%
            {"id": 1, "name": "Бронзовый жетон", "rarity": "common", "value": 10, "color": "#CD7F32", "emoji": "🥉", "feature": "Базовая награда"},
            {"id": 2, "name": "Серебряная монета", "rarity": "common", "value": 25, "color": "#C0C0C0", "emoji": "🪙", "feature": "+5% к удаче"},
            {"id": 3, "name": "Золотой слиток", "rarity": "common", "value": 50, "color": "#FFD700", "emoji": "🪙", "feature": "+10% к выигрышу"},
            
            # Rare (редкие) - 30%
            {"id": 4, "name": "Рубин удачи", "rarity": "rare", "value": 100, "color": "#DC143C", "emoji": "🔴", "feature": "Шанс x2 в Моно"},
            {"id": 5, "name": "Сапфир везения", "rarity": "rare", "value": 150, "color": "#1E90FF", "emoji": "🔵", "feature": "+1 спин в Рулетке"},
            {"id": 6, "name": "Изумруд богатства", "rarity": "rare", "value": 200, "color": "#00FF7F", "emoji": "💚", "feature": "Бонус 50 stars"},
            
            # Epic (эпические) - 15%
            {"id": 7, "name": "Платиновый ключ", "rarity": "epic", "value": 500, "color": "#E5E4E2", "emoji": "🔑", "feature": "Открывает сундук с призами"},
            {"id": 8, "name": "Алмазная карта", "rarity": "epic", "value": 750, "color": "#B9F2FF", "emoji": "💎", "feature": "VIP доступ на 7 дней"},
            {"id": 9, "name": "Мифический артефакт", "rarity": "epic", "value": 1000, "color": "#8A2BE2", "emoji": "🔮", "feature": "Все множители +0.5x"},
            
            # Legendary (легендарные) - 5%
            {"id": 10, "name": "Корона казино", "rarity": "legendary", "value": 5000, "color": "#FFD700", "emoji": "👑", "feature": "Пожизненный VIP статус"},
            {"id": 11, "name": "Чаша изобилия", "rarity": "legendary", "value": 10000, "color": "#FF4500", "emoji": "🏆", "feature": "Ежедневный бонус 100 stars"},
            {"id": 12, "name": "Свиток удачи", "rarity": "legendary", "value": 25000, "color": "#32CD32", "emoji": "📜", "feature": "Гарантированный джекпот"},
        ]
    
    def _load_categories(self) -> Dict:
        """Категории предметов"""
        return {
            "currency": {
                "name": "Валюта",
                "emoji": "💰",
                "items": ["stars", "spins"]
            },
            "nfts": {
                "name": "NFT подарки",
                "emoji": "🎁",
                "subcategories": ["common", "rare", "epic", "legendary"]
            },
            "boosters": {
                "name": "Бусты",
                "emoji": "⚡",
                "items": ["luck_boost", "win_boost", "spin_boost"]
            },
            "collectibles": {
                "name": "Коллекционные предметы",
                "emoji": "🏆",
                "items": ["trophies", "badges", "achievements"]
            },
            "utility": {
                "name": "Полезные предметы",
                "emoji": "🛠️",
                "items": ["keys", "chests", "passes"]
            }
        }
    
    async def get_user_inventory(self, user_id: int) -> Dict:
        """Получить весь инвентарь пользователя"""
        inventory = {
            "currency": {
                "stars": await self.db.get_stars_balance(user_id),
                "spins": await self.db.get_spins_balance(user_id)
            },
            "nfts": await self.get_user_nfts(user_id),
            "boosters": await self.get_user_boosters(user_id),
            "collectibles": await self.get_user_collectibles(user_id),
            "utility": await self.get_user_utility_items(user_id),
            "total_value": 0,
            "total_items": 0
        }
        
        # Рассчитываем общую стоимость
        total_value = inventory["currency"]["stars"]
        total_items = 0
        
        # Добавляем стоимость NFT
        for nft in inventory["nfts"]:
            total_value += nft.get("value", 0)
            total_items += 1
        
        # Добавляем другие предметы
        for category in ["boosters", "collectibles", "utility"]:
            total_items += len(inventory[category])
        
        inventory["total_value"] = total_value
        inventory["total_items"] = total_items
        
        return inventory
    
    async def get_user_nfts(self, user_id: int) -> List[Dict]:
        """Получить NFT пользователя"""
        nft_ids = await self.db.get_user_nft_ids(user_id)
        user_nfts = []
        
        for nft_id in nft_ids:
            nft = self.get_nft_by_id(nft_id)
            if nft:
                # Добавляем информацию о владении
                nft_info = nft.copy()
                nft_info["acquired_date"] = await self.db.get_nft_acquisition_date(user_id, nft_id)
                nft_info["tradeable"] = True
                user_nfts.append(nft_info)
        
        # Сортируем по редкости
        rarity_order = {"legendary": 0, "epic": 1, "rare": 2, "common": 3}
        user_nfts.sort(key=lambda x: rarity_order.get(x["rarity"], 4))
        
        return user_nfts
    
    async def get_user_boosters(self, user_id: int) -> List[Dict]:
        """Получить бусты пользователя"""
        boosters = await self.db.get_user_boosters(user_id)
        
        # Форматируем бусты
        formatted_boosters = []
        for booster in boosters:
            formatted_boosters.append({
                "id": booster["id"],
                "type": booster["type"],
                "name": self._get_booster_name(booster["type"]),
                "value": booster["value"],
                "expires": booster["expires_at"],
                "active": booster["is_active"]
            })
        
        return formatted_boosters
    
    async def get_user_collectibles(self, user_id: int) -> List[Dict]:
        """Получить коллекционные предметы"""
        collectibles = await self.db.get_user_collectibles(user_id)
        return collectibles
    
    async def get_user_utility_items(self, user_id: int) -> List[Dict]:
        """Получить полезные предметы"""
        utility_items = await self.db.get_user_utility_items(user_id)
        return utility_items
    
    def get_nft_by_id(self, nft_id: int) -> Optional[Dict]:
        """Получить NFT по ID"""
        for nft in self.nfts:
            if nft["id"] == nft_id:
                return nft
        return None
    
    async def get_random_nft(self, rarity: str = None) -> Optional[Dict]:
        """Получить случайный NFT"""
        if rarity:
            # Фильтруем по редкости
            filtered_nfts = [nft for nft in self.nfts if nft["rarity"] == rarity]
            if filtered_nfts:
                return random.choice(filtered_nfts)
        
        # Вероятности выпадения
        probabilities = {
            "common": 50,   # 50%
            "rare": 30,     # 30%
            "epic": 15,     # 15%
            "legendary": 5   # 5%
        }
        
        # Выбираем редкость
        total = sum(probabilities.values())
        rand = random.randint(1, total)
        
        current = 0
        selected_rarity = "common"
        
        for rarity_name, probability in probabilities.items():
            current += probability
            if rand <= current:
                selected_rarity = rarity_name
                break
        
        # Выбираем случайный NFT выбранной редкости
        rarity_nfts = [nft for nft in self.nfts if nft["rarity"] == selected_rarity]
        
        if rarity_nfts:
            return random.choice(rarity_nfts)
        
        # Fallback
        return random.choice(self.nfts) if self.nfts else None
    
    async def add_nft_to_user(self, user_id: int, nft_id: int) -> bool:
        """Добавить NFT пользователю"""
        nft = self.get_nft_by_id(nft_id)
        if not nft:
            return False
        
        success = await self.db.add_user_nft(user_id, nft_id)
        if success:
            # Записываем в историю
            await self.db.add_inventory_history(
                user_id=user_id,
                action="nft_received",
                item_type="nft",
                item_id=nft_id,
                item_name=nft["name"],
                quantity=1
            )
        
        return success
    
    async def remove_nft_from_user(self, user_id: int, nft_id: int) -> bool:
        """Удалить NFT у пользователя"""
        nft = self.get_nft_by_id(nft_id)
        if not nft:
            return False
        
        success = await self.db.remove_user_nft(user_id, nft_id)
        if success:
            await self.db.add_inventory_history(
                user_id=user_id,
                action="nft_removed",
                item_type="nft",
                item_id=nft_id,
                item_name=nft["name"],
                quantity=1
            )
        
        return success
    
    async def transfer_nft(self, from_user_id: int, to_user_id: int, nft_id: int) -> bool:
        """Передать NFT другому пользователю"""
        # Проверяем владение
        user_nfts = await self.db.get_user_nft_ids(from_user_id)
        if nft_id not in user_nfts:
            return False
        
        # Удаляем у отправителя
        await self.remove_nft_from_user(from_user_id, nft_id)
        
        # Добавляем получателю
        await self.add_nft_to_user(to_user_id, nft_id)
        
        # Записываем передачу
        nft = self.get_nft_by_id(nft_id)
        await self.db.add_inventory_history(
            user_id=from_user_id,
            action="nft_sent",
            item_type="nft",
            item_id=nft_id,
            item_name=nft["name"],
            quantity=1,
            target_user_id=to_user_id
        )
        
        await self.db.add_inventory_history(
            user_id=to_user_id,
            action="nft_received",
            item_type="nft",
            item_id=nft_id,
            item_name=nft["name"],
            quantity=1,
            source_user_id=from_user_id
        )
        
        return True
    
    async def use_booster(self, user_id: int, booster_id: int) -> bool:
        """Использовать буст"""
        booster = await self.db.get_user_booster(user_id, booster_id)
        if not booster or booster["is_active"]:
            return False
        
        # Активируем буст
        success = await self.db.activate_booster(user_id, booster_id)
        
        if success:
            # Применяем эффект буста
            effect = self._apply_booster_effect(user_id, booster["type"], booster["value"])
            
            await self.db.add_inventory_history(
                user_id=user_id,
                action="booster_used",
                item_type="booster",
                item_id=booster_id,
                item_name=booster["type"],
                quantity=1,
                metadata={"effect": effect}
            )
        
        return success
    
    def _apply_booster_effect(self, user_id: int, booster_type: str, value: float) -> Dict:
        """Применить эффект буста"""
        effects = {
            "luck_boost": {"description": f"Удача +{value}%", "duration": 3600},
            "win_boost": {"description": f"Выигрыш +{value}%", "duration": 1800},
            "spin_boost": {"description": f"Бесплатные спины: {int(value)}", "duration": 0}
        }
        
        return effects.get(booster_type, {"description": "Неизвестный буст", "duration": 0})
    
    def _get_booster_name(self, booster_type: str) -> str:
        """Получить название буста"""
        names = {
            "luck_boost": "Буст удачи",
            "win_boost": "Буст выигрыша",
            "spin_boost": "Бесплатные спины"
        }
        return names.get(booster_type, "Неизвестный буст")
    
    async def get_inventory_value(self, user_id: int) -> int:
        """Получить общую стоимость инвентаря"""
        inventory = await self.get_user_inventory(user_id)
        return inventory["total_value"]
    
    async def get_nft_count(self, user_id: int) -> int:
        """Получить количество NFT"""
        nfts = await self.get_user_nfts(user_id)
        return len(nfts)
    
    async def get_total_items(self, user_id: int) -> int:
        """Получить общее количество предметов"""
        inventory = await self.get_user_inventory(user_id)
        return inventory["total_items"]
    
    async def get_user_stats(self, user_id: int) -> Dict:
        """Получить статистику инвентаря пользователя"""
        nfts = await self.get_user_nfts(user_id)
        
        # Считаем по редкости
        rarity_counts = {"common": 0, "rare": 0, "epic": 0, "legendary": 0}
        total_value = 0
        
        for nft in nfts:
            rarity = nft.get("rarity", "common")
            if rarity in rarity_counts:
                rarity_counts[rarity] += 1
            
            total_value += nft.get("value", 0)
        
        # Добавляем баланс
        stars = await self.db.get_stars_balance(user_id)
        spins = await self.db.get_spins_balance(user_id)
        total_value += stars
        
        return {
            "total_items": await self.get_total_items(user_id),
            "nft_count": len(nfts),
            "rare_items": rarity_counts["rare"],
            "epic_items": rarity_counts["epic"],
            "legendary_items": rarity_counts["legendary"],
            "total_value": total_value,
            "stars_balance": stars,
            "spins_balance": spins,
            "inventory_level": self._calculate_inventory_level(len(nfts), total_value)
        }
    
    def _calculate_inventory_level(self, nft_count: int, total_value: int) -> int:
        """Рассчитать уровень инвентаря"""
        if nft_count >= 50 and total_value >= 50000:
            return 5  # Легенда
        elif nft_count >= 25 and total_value >= 25000:
            return 4  # Мастер
        elif nft_count >= 10 and total_value >= 10000:
            return 3  # Профессионал
        elif nft_count >= 5 and total_value >= 5000:
            return 2  # Любитель
        elif nft_count >= 1:
            return 1  # Новичок
        else:
            return 0  # Пустой
    
    async def search_items(self, user_id: int, query: str) -> List[Dict]:
        """Поиск предметов в инвентаре"""
        results = []
        inventory = await self.get_user_inventory(user_id)
        
        query_lower = query.lower()
        
        # Поиск по NFT
        for nft in inventory["nfts"]:
            if (query_lower in nft["name"].lower() or 
                query_lower in nft["rarity"].lower() or
                query_lower in nft["feature"].lower()):
                results.append({
                    "type": "nft",
                    "item": nft,
                    "category": "nfts"
                })
        
        # Поиск по бустам
        for booster in inventory["boosters"]:
            if query_lower in booster["name"].lower():
                results.append({
                    "type": "booster",
                    "item": booster,
                    "category": "boosters"
                })
        
        return results
    
    async def get_inventory_history(self, user_id: int, limit: int = 20) -> List[Dict]:
        """Получить историю инвентаря"""
        history = await self.db.get_inventory_history(user_id, limit)
        return history
    
    async def export_inventory(self, user_id: int) -> Dict:
        """Экспортировать инвентарь в JSON"""
        inventory = await self.get_user_inventory(user_id)
        
        export_data = {
            "user_id": user_id,
            "export_date": datetime.now().isoformat(),
            "inventory": inventory,
            "metadata": {
                "version": "1.0",
                "game": "Casino Royale",
                "total_items": inventory["total_items"],
                "total_value": inventory["total_value"]
            }
        }
        
        return export_data
