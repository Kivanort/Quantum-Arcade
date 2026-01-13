import os
import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from telegram import (
    Update, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    LabeledPrice,
    MenuButtonWebApp,
    WebAppInfo,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

from config import Config
from database import Database
from payments import PaymentSystem
from games.mono import MonoGame
from games.lucky2 import Lucky2Game
from games.roulette import RouletteGame
from inventory import InventorySystem
from admin import AdminPanel

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CasinoBot:
    def __init__(self):
        self.config = Config()
        self.db = Database(self.config.DB_URL)
        self.payments = PaymentSystem(self.config.PROVIDER_TOKEN, self.db)
        
        # Инициализация игр
        self.mono_game = MonoGame(self.db)
        self.lucky2_game = Lucky2Game(self.db)
        self.roulette_game = RouletteGame(self.db)
        
        # Системы
        self.inventory = InventorySystem(self.db)
        self.admin = AdminPanel(self.db)
        
        # Инициализация приложения
        self.application = Application.builder() \
            .token(self.config.BOT_TOKEN) \
            .build()
            
        # Состояния пользователей
        self.user_states = {}
    
    def setup_handlers(self):
        """Регистрация всех обработчиков"""
        
        # Команды
        handlers = [
            CommandHandler("start", self.start_command),
            CommandHandler("help", self.help_command),
            CommandHandler("menu", self.menu_command),
            CommandHandler("games", self.games_command),
            CommandHandler("mono", self.mono_command),
            CommandHandler("lucky2", self.lucky2_command),
            CommandHandler("roulette", self.roulette_command),
            CommandHandler("buy", self.buy_command),
            CommandHandler("balance", self.balance_command),
            CommandHandler("inventory", self.inventory_command),
            CommandHandler("profile", self.profile_command),
            CommandHandler("stats", self.stats_command),
            CommandHandler("demo", self.demo_command),
            CommandHandler("admin", self.admin_command),
            
            # Админ команды
            CommandHandler("add_stars", self.add_stars_command),
            CommandHandler("add_item", self.add_item_command),
            CommandHandler("user_info", self.user_info_command),
            CommandHandler("bot_stats", self.bot_stats_command),
            
            # Платежи
            PreCheckoutQueryHandler(self.pre_checkout),
            MessageHandler(filters.SUCCESSFUL_PAYMENT, self.successful_payment),
            
            # Callback queries
            CallbackQueryHandler(self.button_handler),
            
            # Web App данные
            MessageHandler(filters.StatusUpdate.WEB_APP_DATA, self.web_app_data),
        ]
        
        for handler in handlers:
            self.application.add_handler(handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        user_id = user.id
        
        # Регистрация пользователя
        await self.db.register_user(user_id, user.username, user.first_name)
        
        # Основное меню
        await self.show_main_menu(update, context)
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать главное меню"""
        user = update.effective_user
        user_id = user.id
        
        # Получаем баланс
        balance = await self.db.get_stars_balance(user_id)
        spins_balance = await self.db.get_spins_balance(user_id)
        
        # Текст приветствия
        welcome_text = f"""
🎰 *Добро пожаловать в Casino Royale!*

👤 *{user.first_name}* | ID: `{user_id}`
💰 *Баланс:* {balance} stars
🎰 *Спины:* {spins_balance}

*Выберите игру:*
        """
        
        # Основные кнопки
        keyboard = [
            [
                InlineKeyboardButton("🎮 ИГРЫ", callback_data="games_menu"),
                InlineKeyboardButton("👛 КОШЕЛЕК", callback_data="wallet")
            ],
            [
                InlineKeyboardButton("🎒 ИНВЕНТАРЬ", callback_data="inventory"),
                InlineKeyboardButton("📊 ПРОФИЛЬ", callback_data="profile")
            ],
            [
                InlineKeyboardButton("🔄 ПОПОЛНИТЬ", callback_data="buy_stars"),
                InlineKeyboardButton("🎁 ДЕМО", callback_data="demo_mode")
            ],
            [
                InlineKeyboardButton("ℹ️ ПОМОЩЬ", callback_data="help"),
                InlineKeyboardButton("⭐ ОТЗЫВЫ", url="https://t.me/casino_reviews")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Установка меню кнопки
        await self.setup_webapp_menu(user_id)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def games_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню игр"""
        games_text = """
🎮 *ДОСТУПНЫЕ ИГРЫ*

1️⃣ *МОНО* 🎯
   Увеличивайте шанс выигрыша свайпом!
   • Шанс: от 1% до 65%
   • Множитель: от 1.54x до 100x
   • NFT шанс: 0.5% при победе

2️⃣ *LUCKY2* 🎨
   Ставьте на цвета!
   • Минимальная ставка: 25 stars
   • Синий/Фиолетовый: x2
   • Красный: x5 (редкий)

3️⃣ *РУЛЕТКА* 🎡
   Классическая игра
   • 16 секторов
   • Множители до 10x
   • NFT каждые 5 спинов

Выберите игру:
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🎯 МОНО", callback_data="play_mono"),
                InlineKeyboardButton("🎨 LUCKY2", callback_data="play_lucky2")
            ],
            [
                InlineKeyboardButton("🎡 РУЛЕТКА", callback_data="play_roulette"),
                InlineKeyboardButton("🎮 ДЕМО ИГРЫ", callback_data="demo_games")
            ],
            [
                InlineKeyboardButton("📊 СТАТИСТИКА ИГР", callback_data="games_stats"),
                InlineKeyboardButton("🏆 ЛИДЕРЫ", callback_data="leaders")
            ],
            [
                InlineKeyboardButton("« НАЗАД", callback_data="main_menu")
            ]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                games_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                games_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    async def mono_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск игры Моно"""
        user_id = update.effective_user.id
        
        # Проверяем баланс спинов
        spins = await self.db.get_spins_balance(user_id)
        
        if spins <= 0:
            await self.show_no_balance(update, context, "Mono")
            return
        
        # Открываем Web App для игры Моно
        web_app_url = f"{self.config.WEBAPP_URL}/mono?user_id={user_id}"
        
        keyboard = [[
            InlineKeyboardButton(
                "🎯 ИГРАТЬ В МОНО",
                web_app=WebAppInfo(url=web_app_url)
            )
        ], [
            InlineKeyboardButton("📖 ПРАВИЛА", callback_data="mono_rules"),
            InlineKeyboardButton("💰 КУПИТЬ СПИНЫ", callback_data="buy_spins")
        ]]
        
        await update.message.reply_text(
            f"""
🎯 *ИГРА МОНО*

*Ваш баланс спинов:* {spins}

*Правила:*
1. Выберите шанс выигрыша (1%-65%)
2. Свайпайте вправо для увеличения шанса
3. Нажмите SPIN
4. Если выпадает зеленый - победа!

*Множители:*
1% шанс = 100x
65% шанс = 1.54x

*NFT шанс:* 0.5% при победе
            """,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def lucky2_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск игры Lucky2"""
        user_id = update.effective_user.id
        
        # Проверяем баланс stars
        balance = await self.db.get_stars_balance(user_id)
        
        if balance < 25:
            await self.show_no_balance(update, context, "Lucky2", min_balance=25)
            return
        
        # Открываем Web App для игры Lucky2
        web_app_url = f"{self.config.WEBAPP_URL}/lucky2?user_id={user_id}"
        
        keyboard = [[
            InlineKeyboardButton(
                "🎨 ИГРАТЬ В LUCKY2",
                web_app=WebAppInfo(url=web_app_url)
            )
        ], [
            InlineKeyboardButton("📖 ПРАВИЛА", callback_data="lucky2_rules"),
            InlineKeyboardButton("💰 ПОПОЛНИТЬ", callback_data="buy_stars")
        ]]
        
        await update.message.reply_text(
            f"""
🎨 *ИГРА LUCKY2*

*Ваш баланс:* {balance} stars

*Правила:*
1. Выберите цвет: Синий, Красный или Фиолетовый
2. Поставьте от 25 stars
3. Крутите колесо
4. Если ваш цвет - победа!

*Выплаты:*
🔵 Синий (60%) = x2
🔴 Красный (5%) = x5
🟣 Фиолетовый (35%) = x2

*Минимальная ставка:* 25 stars
            """,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def roulette_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Запуск классической рулетки"""
        user_id = update.effective_user.id
        
        spins = await self.db.get_spins_balance(user_id)
        
        if spins <= 0:
            await self.show_no_balance(update, context, "Рулетка")
            return
        
        web_app_url = f"{self.config.WEBAPP_URL}/roulette?user_id={user_id}"
        
        keyboard = [[
            InlineKeyboardButton(
                "🎡 ИГРАТЬ В РУЛЕТКУ",
                web_app=WebAppInfo(url=web_app_url)
            )
        ]]
        
        await update.message.reply_text(
            f"""
🎡 *КЛАССИЧЕСКАЯ РУЛЕТКА*

*Баланс спинов:* {spins}

*Секторы:*
🔴 0x (50%)   🔵 1.5x (12%)
🟢 2x (10%)   🟣 3x (7%)
🟠 5x (4%)    🔴 10x (0.2%)

*NFT подарок:* Каждые 5 спинов
            """,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def inventory_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /inventory"""
        user_id = update.effective_user.id
        
        # Открываем Web App с инвентарем
        web_app_url = f"{self.config.WEBAPP_URL}/inventory?user_id={user_id}"
        
        # Получаем статистику для текста
        total_items = await self.inventory.get_total_items(user_id)
        nft_count = await self.inventory.get_nft_count(user_id)
        total_value = await self.inventory.get_inventory_value(user_id)
        
        keyboard = [[
            InlineKeyboardButton(
                "🎒 ОТКРЫТЬ ИНВЕНТАРЬ",
                web_app=WebAppInfo(url=web_app_url)
            )
        ], [
            InlineKeyboardButton("🔄 ОБМЕН", callback_data="exchange"),
            InlineKeyboardButton("🎁 ПОДАРКИ", callback_data="gifts")
        ]]
        
        await update.message.reply_text(
            f"""
🎒 *ВАШ ИНВЕНТАРЬ*

*Статистика:*
• Всего предметов: {total_items}
• NFT: {nft_count}
• Общая стоимость: {total_value} stars

*Категории:*
🎰 Выигранные спины
🎁 NFT подарки
💎 Драгоценности
🏆 Трофеи
⚡ Бусты

Нажмите кнопку ниже, чтобы открыть инвентарь
            """,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Покупка валюты"""
        await self.show_buy_menu(update, context)
    
    async def show_buy_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню покупки"""
        keyboard = [
            [
                InlineKeyboardButton("⭐ 50 STARS - 88 ₽", callback_data="buy_50_stars"),
                InlineKeyboardButton("⭐ 100 STARS - 170 ₽", callback_data="buy_100_stars")
            ],
            [
                InlineKeyboardButton("⭐ 250 STARS - 400 ₽", callback_data="buy_250_stars"),
                InlineKeyboardButton("⭐ 500 STARS - 750 ₽", callback_data="buy_500_stars")
            ],
            [
                InlineKeyboardButton("⭐ 1000 STARS - 1400 ₽", callback_data="buy_1000_stars"),
                InlineKeyboardButton("💎 2500 STARS - 3200 ₽", callback_data="buy_2500_stars")
            ],
            [
                InlineKeyboardButton("🎰 КУПИТЬ СПИНЫ", callback_data="buy_spins_menu"),
                InlineKeyboardButton("« НАЗАД", callback_data="main_menu")
            ]
        ]
        
        text = """
🛒 *МАГАЗИН*

*STARS (для Lucky2 и покупок):*
⭐ *50 stars* - 88 ₽ (1 star = 1.76 ₽)
⭐ *100 stars* - 170 ₽ (1 star = 1.7 ₽) *-3%*
⭐ *250 stars* - 400 ₽ (1 star = 1.6 ₽) *-9%*
⭐ *500 stars* - 750 ₽ (1 star = 1.5 ₽) *-15%*
⭐ *1000 stars* - 1400 ₽ (1 star = 1.4 ₽) *-20%*
💎 *2500 stars* - 3200 ₽ (1 star = 1.28 ₽) *-27%*

*СПИНЫ (для Моно и Рулетки):*
🎰 1 спин = 50 stars
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    async def show_buy_spins_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню покупки спинов"""
        keyboard = [
            [
                InlineKeyboardButton("🎰 1 СПИН - 50 STARS", callback_data="buy_1_spin"),
                InlineKeyboardButton("🎰 5 СПИНОВ - 225 STARS", callback_data="buy_5_spins")
            ],
            [
                InlineKeyboardButton("🎰 10 СПИНОВ - 400 STARS", callback_data="buy_10_spins"),
                InlineKeyboardButton("🎰 25 СПИНОВ - 900 STARS", callback_data="buy_25_spins")
            ],
            [
                InlineKeyboardButton("🎰 50 СПИНОВ - 1600 STARS", callback_data="buy_50_spins"),
                InlineKeyboardButton("💎 100 СПИНОВ - 3000 STARS", callback_data="buy_100_spins")
            ],
            [
                InlineKeyboardButton("« НАЗАД В МАГАЗИН", callback_data="buy_stars")
            ]
        ]
        
        text = """
🎰 *МАГАЗИН СПИНОВ*

*Для игр Моно и Рулетка:*
🎰 *1 спин* - 50 stars
🎰 *5 спинов* - 225 stars (-10%)
🎰 *10 спинов* - 400 stars (-20%)
🎰 *25 спинов* - 900 stars (-28%)
🎰 *50 спинов* - 1600 stars (-36%)
💎 *100 спинов* - 3000 stars (-40%)

🎁 *Бонус NFT за каждые 5 купленных спинов!*
        """
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def process_payment(self, query, product_type: str, amount: str):
        """Обработка платежа"""
        user_id = query.from_user.id
        
        # Определяем продукт
        products = {
            # Stars
            "buy_50_stars": {"type": "stars", "amount": 50, "price": 88, "currency": "RUB"},
            "buy_100_stars": {"type": "stars", "amount": 100, "price": 170, "currency": "RUB"},
            "buy_250_stars": {"type": "stars", "amount": 250, "price": 400, "currency": "RUB"},
            "buy_500_stars": {"type": "stars", "amount": 500, "price": 750, "currency": "RUB"},
            "buy_1000_stars": {"type": "stars", "amount": 1000, "price": 1400, "currency": "RUB"},
            "buy_2500_stars": {"type": "stars", "amount": 2500, "price": 3200, "currency": "RUB"},
            
            # Spins
            "buy_1_spin": {"type": "spins", "amount": 1, "price": 50, "currency": "stars", "bonus_nft": 0},
            "buy_5_spins": {"type": "spins", "amount": 5, "price": 225, "currency": "stars", "bonus_nft": 1},
            "buy_10_spins": {"type": "spins", "amount": 10, "price": 400, "currency": "stars", "bonus_nft": 2},
            "buy_25_spins": {"type": "spins", "amount": 25, "price": 900, "currency": "stars", "bonus_nft": 5},
            "buy_50_spins": {"type": "spins", "amount": 50, "price": 1600, "currency": "stars", "bonus_nft": 10},
            "buy_100_spins": {"type": "spins", "amount": 100, "price": 3000, "currency": "stars", "bonus_nft": 20},
        }
        
        product_id = f"{product_type}_{amount}"
        if product_id not in products:
            await query.edit_message_text("❌ Продукт не найден")
            return
        
        product = products[product_id]
        
        # Создаем счет
        if product["currency"] == "stars":
            # Внутренняя покупка за stars
            balance = await self.db.get_stars_balance(user_id)
            
            if balance < product["price"]:
                await query.edit_message_text(
                    f"❌ Недостаточно stars!\n"
                    f"Нужно: {product['price']} stars\n"
                    f"У вас: {balance} stars",
                    parse_mode='Markdown'
                )
                return
            
            # Списание stars
            await self.db.update_stars_balance(user_id, -product["price"])
            
            # Начисление продукта
            if product["type"] == "spins":
                await self.db.update_spins_balance(user_id, product["amount"])
                
                # Начисляем NFT бонус
                if product.get("bonus_nft", 0) > 0:
                    for _ in range(product["bonus_nft"]):
                        await self.award_random_nft(user_id)
                
                success_text = f"""
✅ *Покупка успешна!*

🎰 *Начислено:* {product['amount']} спинов
🎁 *NFT бонус:* +{product.get('bonus_nft', 0)} подарков
💰 *Потрачено:* {product['price']} stars
👛 *Баланс stars:* {await self.db.get_stars_balance(user_id)}
                """
            else:
                success_text = f"✅ Куплено {product['amount']} stars за {product['price']} stars"
            
            await query.edit_message_text(
                success_text,
                parse_mode='Markdown'
            )
            
        else:
            # Платеж через Telegram Payments
            await self.payments.create_invoice(
                chat_id=user_id,
                product_type=product["type"],
                amount=product["amount"],
                price=product["price"],
                currency=product["currency"],
                bonus_nft=product.get("bonus_nft", 0)
            )
    
    async def pre_checkout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение платежа"""
        query = update.pre_checkout_query
        
        # Всегда подтверждаем
        await query.answer(ok=True)
    
    async def successful_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Успешный платеж"""
        payment = update.message.successful_payment
        user_id = update.effective_user.id
        
        # Обработка платежа
        result = await self.payments.process_successful_payment(
            user_id=user_id,
            telegram_payment_charge_id=payment.telegram_payment_charge_id,
            provider_payment_charge_id=payment.provider_payment_charge_id,
            total_amount=payment.total_amount // 100,  # в копейках/центах
            invoice_payload=payment.invoice_payload
        )
        
        if result["success"]:
            product_type = result["product_type"]
            amount = result["amount"]
            
            if product_type == "stars":
                await self.db.update_stars_balance(user_id, amount)
                balance = await self.db.get_stars_balance(user_id)
                
                success_text = f"""
✅ *Платеж успешно завершен!*

⭐ *Начислено:* {amount} stars
👛 *Баланс:* {balance} stars

*Теперь вы можете:*
🎨 Играть в Lucky2
🎰 Покупать спины
🛒 Покупать предметы в магазине
                """
            
            elif product_type == "spins":
                await self.db.update_spins_balance(user_id, amount)
                
                # Начисляем NFT бонус
                bonus_nft = result.get("bonus_nft", 0)
                if bonus_nft > 0:
                    for _ in range(bonus_nft):
                        await self.award_random_nft(user_id)
                
                spins_balance = await self.db.get_spins_balance(user_id)
                
                success_text = f"""
✅ *Платеж успешно завершен!*

🎰 *Начислено:* {amount} спинов
🎁 *NFT бонус:* +{bonus_nft} подарков
🎯 *Баланс спинов:* {spins_balance}

*Теперь вы можете:*
🎯 Играть в Моно
🎡 Играть в Рулетку
                """
            
            keyboard = [[
                InlineKeyboardButton("🎮 ИГРАТЬ", callback_data="games_menu"),
                InlineKeyboardButton("👛 БАЛАНС", callback_data="balance")
            ]]
            
            await update.message.reply_text(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при обработке платежа. "
                "Пожалуйста, обратитесь в поддержку."
            )
    
    async def award_random_nft(self, user_id: int):
        """Наградить случайным NFT"""
        nft = await self.inventory.get_random_nft()
        if nft:
            await self.inventory.add_nft_to_user(user_id, nft["id"])
            
            try:
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=f"""
🎁 *ВЫ ПОЛУЧИЛИ NFT ПОДАРОК!*

*{nft['name']}*
Редкость: {nft['rarity']}
ID: #{nft['id']:04d}

🏆 *Особенность:* {nft['feature']}

Посмотреть в инвентаре: /inventory
                    """,
                    parse_mode='Markdown'
                )
            except:
                pass
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # Основное меню
        if data == "main_menu":
            await self.show_main_menu(update, context)
        elif data == "games_menu":
            await self.games_command(update, context)
        
        # Игры
        elif data == "play_mono":
            await self.mono_command(update, context)
        elif data == "play_lucky2":
            await self.lucky2_command(update, context)
        elif data == "play_roulette":
            await self.roulette_command(update, context)
        elif data == "demo_games":
            await self.demo_command(update, context)
        elif data == "games_stats":
            await self.show_games_stats(query)
        
        # Кошелек и покупки
        elif data == "wallet":
            await self.balance_command(update, context)
        elif data == "buy_stars":
            await self.show_buy_menu(update, context)
        elif data == "buy_spins_menu":
            await self.show_buy_spins_menu(update, context)
        elif data.startswith("buy_"):
            parts = data.split("_")
            if len(parts) == 3:
                await self.process_payment(query, parts[1], parts[2])
        
        # Инвентарь и профиль
        elif data == "inventory":
            await self.inventory_command(update, context)
        elif data == "profile":
            await self.profile_command(update, context)
        
        # Демо режим
        elif data == "demo_mode":
            await self.demo_command(update, context)
        
        # Правила игр
        elif data == "mono_rules":
            await self.show_mono_rules(query)
        elif data == "lucky2_rules":
            await self.show_lucky2_rules(query)
        
        # Помощь
        elif data == "help":
            await self.help_command(update, context)
        
        # Админ
        elif data.startswith("admin_"):
            await self.admin.handle_callback(update, context)
    
    async def show_no_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            game_name: str, min_balance: int = 1):
        """Показать сообщение о недостатке баланса"""
        user_id = update.effective_user.id
        
        if game_name == "Lucky2":
            balance = await self.db.get_stars_balance(user_id)
            currency = "stars"
        else:
            balance = await self.db.get_spins_balance(user_id)
            currency = "спинов"
        
        keyboard = [[
            InlineKeyboardButton("💰 ПОПОЛНИТЬ", callback_data="buy_stars"),
            InlineKeyboardButton("🎮 ДРУГИЕ ИГРЫ", callback_data="games_menu")
        ]]
        
        text = f"""
⚠️ *НЕДОСТАТОЧНО {currency.upper()}!*

Для игры в *{game_name}* нужно минимум *{min_balance} {currency}*
У вас: *{balance} {currency}*

Пополните баланс или выберите другую игру
        """
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    async def show_mono_rules(self, query):
        """Показать правила Моно"""
        rules = """
🎯 *ПРАВИЛА ИГРЫ МОНО*

*Механика:*
1. Выберите шанс выигрыша от 1% до 65%
2. Свайпайте вправо для увеличения шанса
3. Нажмите SPIN
4. Если выпадает зеленый сектор - вы победили!

*Шансы и множители:*
1% → 100x    15% → 6.67x
3% → 33x     20% → 5x
5% → 20x     25% → 4x
7% → 14.3x   30% → 3.33x
10% → 10x    65% → 1.54x

*NFT шанс:* 0.5% при выигрыше
*Ставка:* 1 спин = 50 stars
        """
        
        keyboard = [[
            InlineKeyboardButton("🎯 ИГРАТЬ В МОНО", callback_data="play_mono"),
            InlineKeyboardButton("« НАЗАД", callback_data="games_menu")
        ]]
        
        await query.edit_message_text(
            rules,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def show_lucky2_rules(self, query):
        """Показать правила Lucky2"""
        rules = """
🎨 *ПРАВИЛА ИГРЫ LUCKY2*

*Механика:*
1. Выберите цвет для ставки:
   • 🔵 Синий (60% шанс) → x2
   • 🔴 Красный (5% шанс) → x5
   • 🟣 Фиолетовый (35% шанс) → x2
2. Выберите сумму ставки (от 25 stars)
3. Крутите колесо
4. Если выпадает ваш цвет - вы побеждаете!

*Особенности:*
• Красный цвет редкий, но дает x5
• При проигрыше ставка сгорает
• Можно ставить на несколько цветов одновременно
• Максимальная ставка: 1000 stars

*Вероятности:*
🔵 Синий: 60%
🔴 Красный: 5% 
🟣 Фиолетовый: 35%
        """
        
        keyboard = [[
            InlineKeyboardButton("🎨 ИГРАТЬ В LUCKY2", callback_data="play_lucky2"),
            InlineKeyboardButton("« НАЗАД", callback_data="games_menu")
        ]]
        
        await query.edit_message_text(
            rules,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def show_games_stats(self, query):
        """Статистика по играм"""
        mono_stats = await self.mono_game.get_statistics()
        lucky2_stats = await self.lucky2_game.get_statistics()
        roulette_stats = await self.roulette_game.get_statistics()
        
        text = f"""
📊 *СТАТИСТИКА ИГР*

🎯 *МОНО:*
• Всего игр: {mono_stats['total_games']}
• Выигрышей: {mono_stats['wins']}
• Проигрышей: {mono_stats['losses']}
• Win Rate: {mono_stats['win_rate']}%
• Макс. выигрыш: {mono_stats['max_win']}x

🎨 *LUCKY2:*
• Всего ставок: {lucky2_stats['total_bets']}
• Общий оборот: {lucky2_stats['total_turnover']} stars
• Выплачено: {lucky2_stats['total_payout']} stars
• RTP: {lucky2_stats['rtp']}%

🎡 *РУЛЕТКА:*
• Всего спинов: {roulette_stats['total_spins']}
• NFT выдано: {roulette_stats['nfts_awarded']}
• Средний множитель: {roulette_stats['avg_multiplier']}x
        """
        
        keyboard = [[
            InlineKeyboardButton("🎮 ВЫБРАТЬ ИГРУ", callback_data="games_menu"),
            InlineKeyboardButton("🏆 ЛИДЕРЫ", callback_data="leaders")
        ]]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /balance"""
        user_id = update.effective_user.id
        
        stars = await self.db.get_stars_balance(user_id)
        spins = await self.db.get_spins_balance(user_id)
        total_deposited = await self.db.get_total_deposited(user_id)
        
        text = f"""
👛 *ВАШ БАЛАНС*

💰 *Stars:* {stars}
   Для: Lucky2, покупки спинов, магазин

🎰 *Спины:* {spins}
   Для: Моно, Рулетка

📈 *Всего пополнено:* {total_deposited} stars
📅 *Играет с:* {await self.db.get_registration_date(user_id)}

*Быстрые действия:*
        """
        
        keyboard = [
            [
                InlineKeyboardButton("💰 ПОПОЛНИТЬ STARS", callback_data="buy_stars"),
                InlineKeyboardButton("🎰 КУПИТЬ СПИНЫ", callback_data="buy_spins_menu")
            ],
            [
                InlineKeyboardButton("🔄 ОБМЕНЯТЬ STARS→СПИНЫ", callback_data="exchange_stars"),
                InlineKeyboardButton("💱 КУРС: 50 STARS = 1 СПИН", callback_data="exchange_rate")
            ],
            [
                InlineKeyboardButton("📊 ПОДРОБНАЯ СТАТИСТИКА", callback_data="detailed_stats"),
                InlineKeyboardButton("« НАЗАД", callback_data="main_menu")
            ]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /profile"""
        user = update.effective_user
        user_id = user.id
        
        profile = await self.db.get_user_profile(user_id)
        inventory_stats = await self.inventory.get_user_stats(user_id)
        
        text = f"""
👤 *ПРОФИЛЬ ИГРОКА*

*Основное:*
ID: `{user_id}`
Имя: {user.first_name}
Юзернейм: @{user.username if user.username else 'скрыт'}

*Статистика:*
🏆 Уровень: {profile['level']}
⭐ Рейтинг: {profile['rating']}
🎮 Всего игр: {profile['total_games']}
💰 Выиграно: {profile['total_won']} stars
📅 В игре: {profile['days_in_game']} дней

*Инвентарь:*
🎒 Предметов: {inventory_stats['total_items']}
🎁 NFT: {inventory_stats['nft_count']}
💎 Редких: {inventory_stats['rare_items']}
👑 Легендарных: {inventory_stats['legendary_items']}
💲 Стоимость: {inventory_stats['total_value']} stars

*Достижения:* {', '.join(profile['achievements'][:3])}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🎒 ИНВЕНТАРЬ", callback_data="inventory"),
                InlineKeyboardButton("🏆 ДОСТИЖЕНИЯ", callback_data="achievements")
            ],
            [
                InlineKeyboardButton("📊 ПОЛНАЯ СТАТИСТИКА", callback_data="full_stats"),
                InlineKeyboardButton("👥 ПОДЕЛИТЬСЯ", switch_inline_query=f"Привет! Я играю в Casino Royale! Мой рейтинг: {profile['rating']}")
            ],
            [
                InlineKeyboardButton("« НАЗАД", callback_data="main_menu")
            ]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def demo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Демо-режим"""
        user_id = update.effective_user.id
        
        # Создаем демо-сессию
        demo_token = await self.db.create_demo_session(user_id)
        
        web_app_url = f"{self.config.WEBAPP_URL}/demo?token={demo_token}"
        
        text = """
🎮 *ДЕМО-РЕЖИМ*

*Доступны все игры:*
🎯 Моно - 10 демо-спинов
🎨 Lucky2 - 1000 демо-stars
🎡 Рулетка - 10 демо-спинов

*Особенности демо:*
• Виртуальная валюта
• Все функции как в реальной игре
• NFT не начисляются
• Статистика не сохраняется

*Цель:* Познакомиться с играми перед реальной игрой!
        """
        
        keyboard = [[
            InlineKeyboardButton(
                "🎮 ИГРАТЬ В ДЕМО-РЕЖИМЕ",
                web_app=WebAppInfo(url=web_app_url)
            )
        ], [
            InlineKeyboardButton("📖 ОБУЧЕНИЕ", callback_data="tutorial"),
            InlineKeyboardButton("💰 ИГРАТЬ НА РЕАЛ", callback_data="buy_stars")
        ]]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def web_app_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка данных из Web App"""
        import json
        
        data = json.loads(update.effective_message.web_app_data.data)
        user_id = update.effective_user.id
        action = data.get('action')
        
        if action == 'mono_spin':
            # Обработка спина в Моно
            chance = data.get('chance', 1)
            bet_amount = data.get('bet_amount', 1)
            
            result = await self.mono_game.spin(user_id, chance, bet_amount)
            
            # Отправляем результат
            response = {
                'success': True,
                'result': result,
                'new_balance': await self.db.get_spins_balance(user_id)
            }
            
            # Если выигрыш и есть NFT
            if result['won'] and result.get('nft_awarded'):
                nft = result['nft_awarded']
                await update.message.reply_text(
                    f"🎉 *ПОБЕДА!* {result['multiplier']}x\n"
                    f"🎁 *Вы получили NFT:* {nft['name']}",
                    parse_mode='Markdown'
                )
        
        elif action == 'lucky2_bet':
            # Обработка ставки в Lucky2
            color = data.get('color')
            amount = data.get('amount', 25)
            
            result = await self.lucky2_game.bet(user_id, color, amount)
            
            response = {
                'success': True,
                'result': result,
                'new_balance': await self.db.get_stars_balance(user_id)
            }
            
            # Если проигрыш - деньги идут владельцу бота
            if not result['won']:
                owner_id = self.config.OWNER_ID
                await self.db.update_stars_balance(owner_id, amount)
        
        elif action == 'roulette_spin':
            # Классическая рулетка
            result = await self.roulette_game.spin(user_id)
            
            response = {
                'success': True,
                'result': result,
                'new_balance': await self.db.get_spins_balance(user_id)
            }
        
        # Отправляем ответ в Web App через reply
        await update.message.reply_text(
            f"🎮 Результат игры обработан!\n"
            f"Баланс обновлен.",
            parse_mode='Markdown'
        )
    
    async def setup_webapp_menu(self, user_id: int):
        """Установка меню кнопки Web App"""
        try:
            await self.application.bot.set_chat_menu_button(
                chat_id=user_id,
                menu_button=MenuButtonWebApp(
                    text="🎮 ИГРАТЬ",
                    web_app=WebAppInfo(url=f"{self.config.WEBAPP_URL}?user_id={user_id}")
                )
            )
        except:
            pass
    
    # АДМИН КОМАНДЫ
    
    async def add_stars_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить stars пользователю"""
        if not await self.admin.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Нет прав администратора!")
            return
        
        try:
            user_id = int(context.args[0])
            amount = int(context.args[1])
            
            await self.db.update_stars_balance(user_id, amount)
            new_balance = await self.db.get_stars_balance(user_id)
            
            # Уведомляем пользователя
            try:
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=f"🎁 *Вам начислено {amount} stars администратором!*\n\n"
                         f"Новый баланс: {new_balance} stars",
                    parse_mode='Markdown'
                )
            except:
                pass
            
            await update.message.reply_text(
                f"✅ Пользователю {user_id} добавлено {amount} stars\n"
                f"Новый баланс: {new_balance} stars"
            )
            
        except (IndexError, ValueError):
            await update.message.reply_text(
                "Использование: /add_stars [user_id] [amount]\n"
                "Пример: /add_stars 123456789 1000"
            )
    
    async def add_item_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить предмет в инвентарь"""
        if not await self.admin.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Нет прав!")
            return
        
        try:
            user_id = int(context.args[0])
            item_type = context.args[1]
            item_id = int(context.args[2]) if len(context.args) > 2 else None
            
            if item_type == "nft":
                if item_id:
                    await self.inventory.add_nft_to_user(user_id, item_id)
                else:
                    await self.award_random_nft(user_id)
                await update.message.reply_text(f"✅ NFT добавлен пользователю {user_id}")
            
            elif item_type == "spin":
                amount = item_id or 1
                await self.db.update_spins_balance(user_id, amount)
                await update.message.reply_text(f"✅ {amount} спинов добавлено пользователю {user_id}")
            
            else:
                await update.message.reply_text("Типы предметов: nft, spin")
                
        except (IndexError, ValueError):
            await update.message.reply_text(
                "Использование: /add_item [user_id] [type] [id?]\n"
                "Примеры:\n"
                "/add_item 123456789 nft 42\n"
                "/add_item 123456789 spin 10"
            )
    
    async def user_info_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Информация о пользователе"""
        if not await self.admin.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Нет прав!")
            return
        
        try:
            user_id = int(context.args[0])
            
            user_info = await self.db.get_user_info(user_id)
            stars = await self.db.get_stars_balance(user_id)
            spins = await self.db.get_spins_balance(user_id)
            nft_count = await self.inventory.get_nft_count(user_id)
            
            text = f"""
👤 *ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ*

*ID:* `{user_id}`
*Username:* @{user_info['username'] or 'нет'}
*Имя:* {user_info['first_name']}

*Балансы:*
💰 Stars: {stars}
🎰 Спины: {spins}
🎁 NFT: {nft_count}

*Статистика:*
📅 Регистрация: {user_info['created_at']}
🎮 Всего игр: {user_info['total_games']}
💰 Пополнено: {user_info['total_deposited']} stars
🏆 Макс. выигрыш: {user_info['max_win']}x

*Последняя активность:* {user_info['last_active']}
            """
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except (IndexError, ValueError):
            await update.message.reply_text("Использование: /user_info [user_id]")
    
    async def bot_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Статистика бота"""
        if not await self.admin.is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ Нет прав!")
            return
        
        stats = await self.db.get_bot_statistics()
        
        text = f"""
📊 *СТАТИСТИКА БОТА*

*Пользователи:*
👥 Всего: {stats['total_users']}
🆕 Новых за 24ч: {stats['new_users_24h']}
📈 Активных за 24ч: {stats['active_users_24h']}

*Финансы:*
💰 Общий оборот: {stats['total_turnover']} stars
💵 Доход: {stats['revenue']} RUB
🎰 Всего спинов: {stats['total_spins']}

*Игры:*
🎯 Моно игр: {stats['mono_games']}
🎨 Lucky2 ставок: {stats['lucky2_bets']}
🎡 Рулеток: {stats['roulette_spins']}

*NFT:*
🎁 Всего выдано: {stats['total_nfts']}
💎 Уникальных NFT: {stats['unique_nfts']}

*Система:*
📅 Бот запущен: {stats['bot_started']}
⚡ Время работы: {stats['uptime']}
            """
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        text = """
🆘 *ПОМОЩЬ ПО БОТУ*

*Основные команды:*
/start - Главное меню
/menu - Основное меню
/games - Выбор игры
/buy - Магазин
/balance - Баланс
/inventory - Инвентарь
/profile - Профиль
/stats - Статистика
/demo - Демо-режим

*Игры:*
/mono - Игра Моно (шанс 1-65%)
/lucky2 - Игра Lucky2 (ставки на цвета)
/roulette - Классическая рулетка

*Пополнение:*
• 50 stars = 88 ₽
• 1 спин = 50 stars
• Минимальное пополнение: 50 stars

*Поддержка:*
📧 Email: support@casinoroyale.com
👨‍💼 Менеджер: @casino_manager
📢 Новости: @casino_news

*Правила:*
• Минимальный возраст: 18 лет
• Ответственная игра
• Возврат средств в течение 24 часов
        """
        
        keyboard = [[
            InlineKeyboardButton("📖 ПОДРОБНЫЕ ПРАВИЛА", url="https://telegra.ph/Pravila-igry-Casino-Royale-01-01"),
            InlineKeyboardButton("📞 ПОДДЕРЖКА", url="https://t.me/casino_support_bot")
        ], [
            InlineKeyboardButton("🎮 ДЕМО-РЕЖИМ", callback_data="demo_mode"),
            InlineKeyboardButton("« НАЗАД", callback_data="main_menu")
        ]]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def run(self):
        """Запуск бота"""
        self.setup_handlers()
        
        # Запускаем поллинг
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("Casino Bot запущен!")
        
        # Бесконечный цикл
        await asyncio.Event().wait()
    
    async def shutdown(self):
        """Корректное завершение"""
        await self.application.stop()
        await self.db.close()

if __name__ == "__main__":
    bot = CasinoBot()
    
    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
    finally:
        asyncio.run(bot.shutdown())
