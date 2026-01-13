import os
import logging
import asyncio
import json
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
    ContextTypes,
    ConversationHandler
)

from config import Config
from database import Database
from payments import PaymentSystem
from games.mono import MonoGame
from games.lucky2 import Lucky2Game

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
SELECTING_GAME, SELECTING_BET, CONFIRMING_SPIN = range(3)

class CasinoBot:
    def __init__(self):
        self.config = Config()
        self.db = Database(self.config.DB_URL)
        self.payments = PaymentSystem(self.config.PROVIDER_TOKEN, self.db)
        self.mono_game = MonoGame(self.db)
        self.lucky2_game = Lucky2Game(self.db)
        
        # Инициализация приложения Telegram
        self.application = Application.builder() \
            .token(self.config.BOT_TOKEN) \
            .build()
        
        # Состояния пользователей
        self.user_states = {}
        
        logger.info("Casino Bot инициализирован")
    
    def setup_handlers(self):
        """Регистрация всех обработчиков"""
        
        # Обработчики команд
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("menu", self.menu_command))
        self.application.add_handler(CommandHandler("games", self.games_command))
        self.application.add_handler(CommandHandler("mono", self.mono_command))
        self.application.add_handler(CommandHandler("lucky2", self.lucky2_command))
        self.application.add_handler(CommandHandler("buy", self.buy_command))
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("demo", self.demo_command))
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        
        # Обработчики платежей
        self.application.add_handler(PreCheckoutQueryHandler(self.pre_checkout))
        self.application.add_handler(MessageHandler(
            filters.SUCCESSFUL_PAYMENT, self.successful_payment
        ))
        
        # Обработчики callback кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Обработчики Web App данных
        self.application.add_handler(MessageHandler(
            filters.StatusUpdate.WEB_APP_DATA, self.web_app_data
        ))
        
        # Админ команды
        self.application.add_handler(CommandHandler("add_stars", self.add_stars_command))
        self.application.add_handler(CommandHandler("add_spins", self.add_spins_command))
        self.application.add_handler(CommandHandler("user_info", self.user_info_command))
        self.application.add_handler(CommandHandler("bot_stats", self.bot_stats_command))
        
        logger.info("Обработчики зарегистрированы")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user
        user_id = user.id
        
        logger.info(f"Новый пользователь: {user_id} - {user.first_name}")
        
        # Регистрируем пользователя в базе данных
        await self.db.register_user(user_id, user.username, user.first_name)
        
        # Устанавливаем меню кнопку Web App
        await self.setup_webapp_menu(user_id)
        
        # Отправляем приветственное сообщение
        welcome_text = f"""
🎰 *Добро пожаловать в Casino Royale!*

👤 *{user.first_name}*, рады видеть вас в нашем казино!

*Доступные игры:*
🎯 *МОНО* - Увеличивайте шанс выигрыша свайпом (1-65%)
🎨 *LUCKY2* - Ставки на цвета с множителями до 5x
🎡 *РУЛЕТКА* - Классическая игра

*Ваш баланс:*
🎰 Спины: {await self.db.get_spins_balance(user_id)}
⭐ Stars: {await self.db.get_stars_balance(user_id)}

*Используйте команды:*
/menu - Главное меню
/games - Выбор игры
/buy - Пополнить баланс
/balance - Проверить баланс
        """
        
        # Создаем клавиатуру с кнопками
        keyboard = [
            [
                InlineKeyboardButton("🎮 ГЛАВНОЕ МЕНЮ", callback_data="main_menu"),
                InlineKeyboardButton("💰 ПОПОЛНИТЬ", callback_data="buy_stars")
            ],
            [
                InlineKeyboardButton("🎯 ИГРАТЬ В МОНО", callback_data="play_mono"),
                InlineKeyboardButton("🎨 ИГРАТЬ В LUCKY2", callback_data="play_lucky2")
            ],
            [
                InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="stats"),
                InlineKeyboardButton("ℹ️ ПОМОЩЬ", callback_data="help")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        logger.info(f"Приветственное сообщение отправлено пользователю {user_id}")
    
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /menu - главное меню"""
        user = update.effective_user
        user_id = user.id
        
        # Получаем баланс пользователя
        stars_balance = await self.db.get_stars_balance(user_id)
        spins_balance = await self.db.get_spins_balance(user_id)
        
        menu_text = f"""
🏠 *ГЛАВНОЕ МЕНЮ*

👤 *{user.first_name}* | ID: `{user_id}`
💰 Баланс: {stars_balance} stars
🎰 Спины: {spins_balance}

*Выберите действие:*
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🎮 ИГРЫ", callback_data="games_menu"),
                InlineKeyboardButton("👛 КОШЕЛЕК", callback_data="wallet")
            ],
            [
                InlineKeyboardButton("📊 ПРОФИЛЬ", callback_data="profile"),
                InlineKeyboardButton("🏆 ЛИДЕРЫ", callback_data="leaders")
            ],
            [
                InlineKeyboardButton("🔄 ПОПОЛНИТЬ", callback_data="buy_stars"),
                InlineKeyboardButton("🎁 ДЕМО", callback_data="demo_mode")
            ],
            [
                InlineKeyboardButton("📖 ПРАВИЛА", callback_data="rules"),
                InlineKeyboardButton("👨‍💼 ПОДДЕРЖКА", callback_data="support")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                menu_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                menu_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    async def games_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /games - меню игр"""
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
                InlineKeyboardButton("🏆 ТОП ИГРОКИ", callback_data="top_players")
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
        """Команда /mono - запуск игры Моно"""
        user = update.effective_user
        user_id = user.id
        
        # Проверяем баланс спинов
        spins_balance = await self.db.get_spins_balance(user_id)
        
        if spins_balance <= 0:
            # У пользователя нет спинов
            no_spins_text = """
⚠️ *У вас нет спинов!*

Для игры в Моно нужны спины:
🎰 1 спин = 50 stars

*Ваш баланс:*
⭐ Stars: {stars_balance}
🎰 Спины: {spins_balance}

Выберите действие:
            """.format(
                stars_balance=await self.db.get_stars_balance(user_id),
                spins_balance=spins_balance
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("💰 КУПИТЬ СПИНЫ", callback_data="buy_spins"),
                    InlineKeyboardButton("🔄 ОБМЕНЯТЬ STARS", callback_data="exchange_stars")
                ],
                [
                    InlineKeyboardButton("🎮 ДЕМО-РЕЖИМ", callback_data="demo_mono"),
                    InlineKeyboardButton("« НАЗАД", callback_data="games_menu")
                ]
            ]
            
            await update.message.reply_text(
                no_spins_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return
        
        # У пользователя есть спины - открываем Web App
        web_app_url = f"{self.config.WEBAPP_URL}/mono.html?user_id={user_id}"
        
        # Информация об игре Моно
        mono_info = """
🎯 *ИГРА МОНО - ПРАВИЛА*

*Как играть:*
1. Выберите шанс выигрыша от 1% до 65%
2. Установите ставку (мин. зависит от шанса)
3. Крутите колесо
4. Если выпадает зеленый сектор - победа!

*Минимальные ставки:*
1% - 4 stars     15% - 60 stars
3% - 12 stars    20% - 80 stars
5% - 20 stars    25% - 100 stars
7% - 28 stars    30% - 120 stars
10% - 40 stars   65% - 260 stars

*Множители:*
1% = 100x    20% = 5x
3% = 33x     25% = 4x
5% = 20x     30% = 3.33x
7% = 14.3x   40% = 2.5x
10% = 10x    50% = 2x
15% = 6.67x  65% = 1.54x

🎰 *Ваш баланс спинов:* {spins_balance}
        """.format(spins_balance=spins_balance)
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "🎯 НАЧАТЬ ИГРУ",
                    web_app=WebAppInfo(url=web_app_url)
                )
            ],
            [
                InlineKeyboardButton("💰 КУПИТЬ СПИНЫ", callback_data="buy_spins"),
                InlineKeyboardButton("📖 ПОДРОБНЫЕ ПРАВИЛА", callback_data="mono_rules")
            ],
            [
                InlineKeyboardButton("« НАЗАД", callback_data="games_menu")
            ]
        ]
        
        await update.message.reply_text(
            mono_info,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def lucky2_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /lucky2 - запуск игры Lucky2"""
        user = update.effective_user
        user_id = user.id
        
        # Проверяем баланс stars
        stars_balance = await self.db.get_stars_balance(user_id)
        
        if stars_balance < 25:
            # У пользователя недостаточно stars
            no_stars_text = """
⚠️ *Недостаточно stars!*

Для игры в Lucky2 нужно минимум 25 stars.

*Ваш баланс:*
⭐ Stars: {stars_balance}
🎰 Спины: {spins_balance}

Выберите действие:
            """.format(
                stars_balance=stars_balance,
                spins_balance=await self.db.get_spins_balance(user_id)
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("💰 ПОПОЛНИТЬ BALANCE", callback_data="buy_stars"),
                    InlineKeyboardButton("🎮 ДРУГИЕ ИГРЫ", callback_data="games_menu")
                ],
                [
                    InlineKeyboardButton("🎮 ДЕМО-РЕЖИМ", callback_data="demo_lucky2"),
                    InlineKeyboardButton("« НАЗАД", callback_data="games_menu")
                ]
            ]
            
            await update.message.reply_text(
                no_stars_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return
        
        # У пользователя достаточно stars - открываем Web App
        web_app_url = f"{self.config.WEBAPP_URL}/lucky2.html?user_id={user_id}"
        
        # Информация об игре Lucky2
        lucky2_info = """
🎨 *ИГРА LUCKY2 - ПРАВИЛА*

*Как играть:*
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

⭐ *Ваш баланс stars:* {stars_balance}
        """.format(stars_balance=stars_balance)
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "🎨 НАЧАТЬ ИГРУ",
                    web_app=WebAppInfo(url=web_app_url)
                )
            ],
            [
                InlineKeyboardButton("💰 ПОПОЛНИТЬ BALANCE", callback_data="buy_stars"),
                InlineKeyboardButton("📖 ПОДРОБНЫЕ ПРАВИЛА", callback_data="lucky2_rules")
            ],
            [
                InlineKeyboardButton("« НАЗАД", callback_data="games_menu")
            ]
        ]
        
        await update.message.reply_text(
            lucky2_info,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /buy - покупка валюты"""
        await self.show_buy_menu(update, context)
    
    async def show_buy_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню покупки"""
        buy_text = """
🛒 *МАГАЗИН*

*STARS (для Lucky2 и покупок):*
⭐ *50 stars* - 88 ₽ (1 star = 1.76 ₽)
⭐ *250 stars* - 400 ₽ (1 star = 1.6 ₽) *-9%*
⭐ *500 stars* - 750 ₽ (1 star = 1.5 ₽) *-15%*
⭐ *1000 stars* - 1400 ₽ (1 star = 1.4 ₽) *-20%*
💎 *2500 stars* - 3200 ₽ (1 star = 1.28 ₽) *-27%*

*СПИНЫ (для Моно и Рулетки):*
🎰 1 спин = 50 stars

*Выберите продукт:*
        """
        
        keyboard = [
            [
                InlineKeyboardButton("⭐ 50 STARS - 88 ₽", callback_data="buy_50_stars"),
                InlineKeyboardButton("⭐ 250 STARS - 400 ₽", callback_data="buy_250_stars")
            ],
            [
                InlineKeyboardButton("⭐ 500 STARS - 750 ₽", callback_data="buy_500_stars"),
                InlineKeyboardButton("⭐ 1000 STARS - 1400 ₽", callback_data="buy_1000_stars")
            ],
            [
                InlineKeyboardButton("💎 2500 STARS - 3200 ₽", callback_data="buy_2500_stars"),
                InlineKeyboardButton("🎰 КУПИТЬ СПИНЫ", callback_data="buy_spins_menu")
            ],
            [
                InlineKeyboardButton("« НАЗАД", callback_data="main_menu")
            ]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                buy_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                buy_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    async def show_buy_spins_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать меню покупки спинов"""
        spins_text = """
🎰 *МАГАЗИН СПИНОВ*

*Для игр Моно и Рулетка:*
🎰 *1 спин* - 50 stars
🎰 *5 спинов* - 225 stars (-10%)
🎰 *10 спинов* - 400 stars (-20%)
🎰 *25 спинов* - 900 stars (-28%)
🎰 *50 спинов* - 1600 stars (-36%)
💎 *100 спинов* - 3000 stars (-40%)

🎁 *Бонус NFT за каждые 5 купленных спинов!*

*Выберите пакет:*
        """
        
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
        
        await update.callback_query.edit_message_text(
            spins_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /balance - проверка баланса"""
        user = update.effective_user
        user_id = user.id
        
        # Получаем балансы
        stars_balance = await self.db.get_stars_balance(user_id)
        spins_balance = await self.db.get_spins_balance(user_id)
        total_deposited = await self.db.get_total_deposited(user_id)
        
        balance_text = f"""
👛 *ВАШ БАЛАНС*

💰 *Stars:* {stars_balance}
   Для: Lucky2, покупки спинов, магазин

🎰 *Спины:* {spins_balance}
   Для: Моно, Рулетка (1 спин = 50 stars)

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
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                balance_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                balance_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /profile - профиль пользователя"""
        user = update.effective_user
        user_id = user.id
        
        # Получаем профиль пользователя
        profile = await self.db.get_user_profile(user_id)
        
        profile_text = f"""
👤 *ПРОФИЛЬ ИГРОКА*

*Основное:*
ID: `{user_id}`
Имя: {user.first_name}
Юзернейм: @{user.username if user.username else 'скрыт'}

*Статистика:*
🏆 Уровень: {profile.get('level', 1)}
⭐ Рейтинг: {profile.get('rating', 1000)}
🎮 Всего игр: {profile.get('total_games', 0)}
💰 Выиграно: {profile.get('total_won', 0)} stars
📅 В игре: {profile.get('days_in_game', 0)} дней

*Балансы:*
🎰 Спины: {await self.db.get_spins_balance(user_id)}
⭐ Stars: {await self.db.get_stars_balance(user_id)}

*Достижения:* {', '.join(profile.get('achievements', ['Нет достижений']))[:50]}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📊 ПОЛНАЯ СТАТИСТИКА", callback_data="full_stats"),
                InlineKeyboardButton("🏆 ДОСТИЖЕНИЯ", callback_data="achievements")
            ],
            [
                InlineKeyboardButton("👥 ПОДЕЛИТЬСЯ ПРОФИЛЕМ", 
                                   switch_inline_query=f"Мой профиль в Casino Royale!"),
                InlineKeyboardButton("🎁 МОИ NFT", callback_data="my_nfts")
            ],
            [
                InlineKeyboardButton("« НАЗАД", callback_data="main_menu")
            ]
        ]
        
        await update.message.reply_text(
            profile_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /stats - статистика игры"""
        user = update.effective_user
        user_id = user.id
        
        # Получаем статистику
        stats = await self.db.get_game_stats()
        user_stats = await self.db.get_user_stats(user_id)
        
        stats_text = f"""
📊 *СТАТИСТИКА ИГРЫ*

*Общая статистика:*
👥 Всего игроков: {stats.get('total_users', 0)}
🎰 Всего спинов: {stats.get('total_spins', 0)}
💰 Общий выигрыш: {stats.get('total_won', 0)} stars
🎁 Выдано NFT: {stats.get('total_nfts', 0)}

*Топ-5 побед за сегодня:*
{self.format_top_wins(stats.get('top_wins_today', []))}

*Ваша статистика:*
🎰 Ваши спины: {user_stats.get('user_spins', 0)}
💰 Ваш выигрыш: {user_stats.get('user_won', 0)} stars
📊 Win Rate: {user_stats.get('win_rate', 0)}%
🥇 Место в рейтинге: #{user_stats.get('rank', 0)}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🏆 ТОП ИГРОКИ", callback_data="top_players"),
                InlineKeyboardButton("📈 ГРАФИКИ", callback_data="charts")
            ],
            [
                InlineKeyboardButton("🎮 МОЯ СТАТИСТИКА", callback_data="my_stats"),
                InlineKeyboardButton("📊 СТАТИСТИКА ПО ИГРАМ", callback_data="games_stats")
            ],
            [
                InlineKeyboardButton("« НАЗАД", callback_data="main_menu")
            ]
        ]
        
        await update.message.reply_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    def format_top_wins(self, top_wins):
        """Форматирование топ-побед"""
        if not top_wins:
            return "Нет данных"
        
        result = ""
        for i, win in enumerate(top_wins[:5], 1):
            result += f"{i}. @{win.get('username', 'user')} - {win.get('multiplier', 0)}x\n"
        return result
    
    async def demo_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /demo - демо-режим"""
        user = update.effective_user
        user_id = user.id
        
        # Создаем демо-сессию
        demo_token = await self.db.create_demo_session(user_id)
        
        demo_text = """
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
        
        web_app_url = f"{self.config.WEBAPP_URL}/demo.html?token={demo_token}"
        
        keyboard = [
            [
                InlineKeyboardButton(
                    "🎮 ИГРАТЬ В ДЕМО-РЕЖИМЕ",
                    web_app=WebAppInfo(url=web_app_url)
                )
            ],
            [
                InlineKeyboardButton("📖 ОБУЧЕНИЕ", callback_data="tutorial"),
                InlineKeyboardButton("💰 ИГРАТЬ НА РЕАЛ", callback_data="buy_stars")
            ],
            [
                InlineKeyboardButton("« НАЗАД", callback_data="main_menu")
            ]
        ]
        
        await update.message.reply_text(
            demo_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /admin - админ-панель"""
        user = update.effective_user
        user_id = user.id
        
        # Проверяем права админа
        if user_id not in self.config.ADMINS and user_id != self.config.OWNER_ID:
            await update.message.reply_text("⛔ У вас нет прав администратора!")
            return
        
        admin_text = """
⚙️ *АДМИН-ПАНЕЛЬ*

*Доступные функции:*
📊 *Статистика бота* - общая информация
👥 *Пользователи* - поиск и управление
💰 *Финансы* - доходы, платежи
🎁 *NFT* - статистика подарков
⚙️ *Настройки* - конфигурация игры

*Быстрые команды:*
/add_stars [user_id] [amount] - добавить stars
/add_spins [user_id] [amount] - добавить спины
/user_info [user_id] - информация о пользователе
/bot_stats - статистика бота
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📊 СТАТИСТИКА БОТА", callback_data="admin_stats"),
                InlineKeyboardButton("👥 УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton("💰 ФИНАНСОВАЯ СТАТИСТИКА", callback_data="admin_finance"),
                InlineKeyboardButton("🎁 УПРАВЛЕНИЕ NFT", callback_data="admin_nfts")
            ],
            [
                InlineKeyboardButton("⚙️ НАСТРОЙКИ", callback_data="admin_settings"),
                InlineKeyboardButton("📋 ЛОГИ", callback_data="admin_logs")
            ],
            [
                InlineKeyboardButton("« НАЗАД", callback_data="main_menu")
            ]
        ]
        
        await update.message.reply_text(
            admin_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        logger.info(f"Callback query от {query.from_user.id}: {data}")
        
        # Обработка основных действий
        if data == "main_menu":
            await self.menu_command(update, context)
        
        elif data == "games_menu":
            await self.games_command(update, context)
        
        elif data == "play_mono":
            await self.mono_command(update, context)
        
        elif data == "play_lucky2":
            await self.lucky2_command(update, context)
        
        elif data == "buy_stars":
            await self.show_buy_menu(update, context)
        
        elif data == "buy_spins_menu":
            await self.show_buy_spins_menu(update, context)
        
        elif data == "wallet":
            await self.balance_command(update, context)
        
        elif data == "profile":
            await self.profile_command(update, context)
        
        elif data == "stats":
            await self.stats_command(update, context)
        
        elif data == "demo_mode":
            await self.demo_command(update, context)
        
        elif data == "help":
            await self.help_command(update, context)
        
        elif data.startswith("buy_"):
            # Обработка покупки
            parts = data.split("_")
            if len(parts) >= 3:
                await self.process_purchase(query, parts[1], parts[2])
        
        elif data == "exchange_stars":
            await self.exchange_stars(update, context)
        
        elif data == "mono_rules":
            await self.show_mono_rules(query)
        
        elif data == "lucky2_rules":
            await self.show_lucky2_rules(query)
        
        elif data.startswith("admin_"):
            await self.handle_admin_callback(update, context, data)
    
    async def process_purchase(self, query, product_type: str, amount: str):
        """Обработка покупки продукта"""
        user_id = query.from_user.id
        
        # Определяем продукт
        products = {
            # Stars
            "50_stars": {"type": "stars", "amount": 50, "price": 88, "currency": "RUB"},
            "250_stars": {"type": "stars", "amount": 250, "price": 400, "currency": "RUB"},
            "500_stars": {"type": "stars", "amount": 500, "price": 750, "currency": "RUB"},
            "1000_stars": {"type": "stars", "amount": 1000, "price": 1400, "currency": "RUB"},
            "2500_stars": {"type": "stars", "amount": 2500, "price": 3200, "currency": "RUB"},
            
            # Spins
            "1_spin": {"type": "spins", "amount": 1, "price": 50, "currency": "stars"},
            "5_spins": {"type": "spins", "amount": 5, "price": 225, "currency": "stars"},
            "10_spins": {"type": "spins", "amount": 10, "price": 400, "currency": "stars"},
            "25_spins": {"type": "spins", "amount": 25, "price": 900, "currency": "stars"},
            "50_spins": {"type": "spins", "amount": 50, "price": 1600, "currency": "stars"},
            "100_spins": {"type": "spins", "amount": 100, "price": 3000, "currency": "stars"},
        }
        
        product_id = f"{product_type}_{amount}"
        if product_id not in products:
            await query.edit_message_text("❌ Продукт не найден")
            return
        
        product = products[product_id]
        
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
                
                # Начисляем NFT бонус (каждые 5 спинов)
                bonus_nft = product["amount"] // 5
                if bonus_nft > 0:
                    await query.edit_message_text(
                        f"✅ *Покупка успешна!*\n\n"
                        f"🎰 *Начислено:* {product['amount']} спинов\n"
                        f"🎁 *NFT бонус:* +{bonus_nft} подарков\n"
                        f"💰 *Потрачено:* {product['price']} stars\n"
                        f"👛 *Баланс stars:* {await self.db.get_stars_balance(user_id)}\n"
                        f"🎰 *Баланс спинов:* {await self.db.get_spins_balance(user_id)}",
                        parse_mode='Markdown'
                    )
                    
                    # Начисляем NFT
                    for _ in range(bonus_nft):
                        await self.award_random_nft(user_id)
                else:
                    await query.edit_message_text(
                        f"✅ *Покупка успешна!*\n\n"
                        f"🎰 *Начислено:* {product['amount']} спинов\n"
                        f"💰 *Потрачено:* {product['price']} stars\n"
                        f"👛 *Баланс stars:* {await self.db.get_stars_balance(user_id)}\n"
                        f"🎰 *Баланс спинов:* {await self.db.get_spins_balance(user_id)}",
                        parse_mode='Markdown'
                    )
            else:
                await query.edit_message_text(
                    f"✅ Куплено {product['amount']} stars за {product['price']} RUB"
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
    
    async def award_random_nft(self, user_id: int):
        """Наградить случайным NFT"""
        # В реальном проекте здесь будет логика выдачи NFT
        # Для демо просто отправляем сообщение
        try:
            await self.application.bot.send_message(
                chat_id=user_id,
                text="🎁 *Вы получили случайный NFT подарок!*\n\n"
                     "Поздравляем! 🎉\n"
                     "Посмотреть в инвентаре: /inventory",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка отправки NFT уведомления: {e}")
    
    async def exchange_stars(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обмен stars на спины"""
        query = update.callback_query
        user_id = query.from_user.id
        
        exchange_text = """
🔄 *ОБМЕН STARS НА СПИНЫ*

*Курс обмена:*
50 stars = 1 спин
1 спин = 50 stars

*Ваш баланс:*
⭐ Stars: {stars_balance}
🎰 Спины: {spins_balance}

*Выберите количество спинов для покупки:*
        """.format(
            stars_balance=await self.db.get_stars_balance(user_id),
            spins_balance=await self.db.get_spins_balance(user_id)
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🎰 1 СПИН (50⭐)", callback_data="exchange_1"),
                InlineKeyboardButton("🎰 5 СПИНОВ (225⭐)", callback_data="exchange_5")
            ],
            [
                InlineKeyboardButton("🎰 10 СПИНОВ (400⭐)", callback_data="exchange_10"),
                InlineKeyboardButton("🎰 25 СПИНОВ (900⭐)", callback_data="exchange_25")
            ],
            [
                InlineKeyboardButton("« НАЗАД", callback_data="wallet")
            ]
        ]
        
        await query.edit_message_text(
            exchange_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def show_mono_rules(self, query):
        """Показать подробные правила Моно"""
        rules_text = """
📖 *ПОДРОБНЫЕ ПРАВИЛА ИГРЫ МОНО*

*Механика игры:*
1. Выберите шанс выигрыша от 1% до 65%
2. Свайпайте вправо для увеличения шанса
3. Выберите ставку (мин. зависит от шанса)
4. Нажмите SPIN
5. Если выпадает зеленый сектор - вы победили!

*Минимальные ставки и множители:*
