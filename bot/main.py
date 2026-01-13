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
    WebAppInfo
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
        self.mono_game = MonoGame(self.db)
        
        # Инициализация приложения
        self.application = Application.builder() \
            .token(self.config.BOT_TOKEN) \
            .build()
    
    def setup_handlers(self):
        """Регистрация обработчиков"""
        # Основные команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("mono", self.mono_command))
        self.application.add_handler(CommandHandler("buy", self.buy_command))
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        
        # Платежи
        self.application.add_handler(PreCheckoutQueryHandler(self.pre_checkout))
        self.application.add_handler(MessageHandler(
            filters.SUCCESSFUL_PAYMENT, self.successful_payment
        ))
        
        # Callback queries
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Web App данные
        self.application.add_handler(MessageHandler(
            filters.StatusUpdate.WEB_APP_DATA, self.web_app_data
        ))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user = update.effective_user
        user_id = user.id
        
        # Регистрация пользователя
        await self.db.register_user(user_id, user.username, user.first_name)
        
        # Приветственное сообщение
        welcome_text = f"""
🎰 *Добро пожаловать в Casino Royale!*

👤 *{user.first_name}*, рады видеть вас!

*Доступные игры:*
🎯 *МОНО* - Увеличивайте шанс выигрыша свайпом!
🎨 *LUCKY2* - Ставки на цвета с множителями до 5x!
🎡 *РУЛЕТКА* - Классическая игра как в Rolls

*Ваш баланс:*
🎰 Спины: {await self.db.get_spins_balance(user_id)}
⭐ Stars: {await self.db.get_stars_balance(user_id)}

*Команды:*
/mono - Играть в Моно
/buy - Пополнить баланс
/balance - Проверить баланс
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🎯 ИГРАТЬ В МОНО", callback_data="play_mono"),
                InlineKeyboardButton("💰 ПОПОЛНИТЬ", callback_data="buy_stars")
            ],
            [
                InlineKeyboardButton("👛 БАЛАНС", callback_data="balance"),
                InlineKeyboardButton("📊 СТАТИСТИКА", callback_data="stats")
            ]
        ]
        
        # Установка меню кнопки для Web App
        await self.setup_webapp_menu(user_id)
        
        await update.message.reply_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def mono_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /mono - запуск игры Моно"""
        user_id = update.effective_user.id
        
        # Проверяем баланс спинов
        spins_balance = await self.db.get_spins_balance(user_id)
        
        if spins_balance <= 0:
            keyboard = [[
                InlineKeyboardButton("💰 КУПИТЬ СПИНЫ", callback_data="buy_spins"),
                InlineKeyboardButton("🎮 ДЕМО-РЕЖИМ", callback_data="demo_mono")
            ]]
            
            await update.message.reply_text(
                "⚠️ *У вас нет спинов!*\n\n"
                "Для игры в Моно нужны спины.\n"
                "1 спин = 50 stars\n\n"
                "Купите спины или попробуйте демо-режим",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return
        
        # Открываем Web App для игры Моно
        web_app_url = f"{self.config.WEBAPP_URL}/mono.html?user_id={user_id}"
        
        # Получаем настройки игры для отображения
        chance_settings = self.mono_game.get_chance_settings()
        
        rules_text = """
🎯 *ИГРА МОНО - ПРАВИЛА*

*Как играть:*
1. Выберите шанс выигрыша (1%-65%)
2. Установите ставку (мин. зависит от шанса)
3. Крутите колесо
4. Если выпадает зеленый сектор - победа!

*Минимальные ставки:*
        """
        
        # Добавляем информацию о минимальных ставках
        for setting in chance_settings[:6]:  # Первые 6 для краткости
            min_spins = self.mono_game.get_min_spins_for_chance(setting["chance"])
            rules_text += f"\n{setting['chance']}% - {setting['min_bet_stars']} stars ({min_spins} спин)"
        
        rules_text += "\n\n*Множители:*"
        for setting in chance_settings[:6]:
            rules_text += f"\n{setting['chance']}% = {setting['multiplier']}x"
        
        rules_text += f"\n\n🎰 *Ваш баланс спинов:* {spins_balance}"
        rules_text += f"\n⭐ *Ваш баланс stars:* {await self.db.get_stars_balance(user_id)}"
        
        keyboard = [[
            InlineKeyboardButton(
                "🎯 НАЧАТЬ ИГРУ",
                web_app=WebAppInfo(url=web_app_url)
            )
        ], [
            InlineKeyboardButton("💰 КУПИТЬ СПИНЫ", callback_data="buy_spins"),
            InlineKeyboardButton("📖 ПОДРОБНЫЕ ПРАВИЛА", callback_data="mono_rules")
        ]]
        
        await update.message.reply_text(
            rules_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /buy - покупка валюты"""
        await self.show_buy_menu(update, context)
    
    async def show_buy_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню покупки"""
        keyboard = [
            [
                InlineKeyboardButton("⭐ 50 STARS - 88 ₽", callback_data="buy_50_stars"),
                InlineKeyboardButton("⭐ 250 STARS - 400 ₽", callback_data="buy_250_stars")
            ],
            [
                InlineKeyboardButton("⭐ 500 STARS - 750 ₽", callback_data="buy_500_stars"),
                InlineKeyboardButton("💎 1000 STARS - 1400 ₽", callback_data="buy_1000_stars")
            ],
            [
                InlineKeyboardButton("🎰 КУПИТЬ СПИНЫ", callback_data="buy_spins_menu"),
                InlineKeyboardButton("« НАЗАД", callback_data="main_menu")
            ]
        ]
        
        text = """
🛒 *МАГАЗИН*

*STARS (для всех игр):*
⭐ *50 stars* - 88 ₽ (1 star = 1.76 ₽)
⭐ *250 stars* - 400 ₽ (1 star = 1.6 ₽) *-9%*
⭐ *500 stars* - 750 ₽ (1 star = 1.5 ₽) *-15%*
💎 *1000 stars* - 1400 ₽ (1 star = 1.4 ₽) *-20%*

*СПИНЫ (для Моно):*
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
                InlineKeyboardButton("« НАЗАД В МАГАЗИН", callback_data="buy_stars")
            ]
        ]
        
        text = """
🎰 *МАГАЗИН СПИНОВ*

*Для игры Моно:*
🎰 *1 спин* - 50 stars
🎰 *5 спинов* - 225 stars (-10%)
🎰 *10 спинов* - 400 stars (-20%)
🎰 *25 спинов* - 900 stars (-28%)

*Минимальные ставки в Моно:*
1% - 4 stars (0.08 спин)
65% - 260 stars (5.2 спинов)
        """
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /balance"""
        user_id = update.effective_user.id
        
        stars = await self.db.get_stars_balance(user_id)
        spins = await self.db.get_spins_balance(user_id)
        
        text = f"""
👛 *ВАШ БАЛАНС*

💰 *Stars:* {stars}
   Для: Моно (конвертация в спины), Lucky2

🎰 *Спины:* {spins}
   Для: Моно (1 спин = 50 stars)

*Конвертация:*
50 stars = 1 спин
1 спин = 50 stars

*Быстрые действия:*
        """
        
        keyboard = [
            [
                InlineKeyboardButton("💰 ПОПОЛНИТЬ STARS", callback_data="buy_stars"),
                InlineKeyboardButton("🎰 КУПИТЬ СПИНЫ", callback_data="buy_spins_menu")
            ],
            [
                InlineKeyboardButton("🔄 ОБМЕНЯТЬ STARS→СПИНЫ", callback_data="exchange_stars"),
                InlineKeyboardButton("🎯 ИГРАТЬ В МОНО", callback_data="play_mono")
            ]
        ]
        
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "play_mono":
            await self.mono_command(update, context)
        elif data == "buy_stars":
            await self.show_buy_menu(update, context)
        elif data == "buy_spins_menu":
            await self.show_buy_spins_menu(update, context)
        elif data == "balance":
            await self.balance_command(update, context)
        elif data == "main_menu":
            await self.start_command(update, context)
        elif data.startswith("buy_"):
            # Обработка покупки
            parts = data.split("_")
            if len(parts) >= 3:
                await self.process_purchase(query, parts[1], parts[2])
    
    async def process_purchase(self, query, product_type: str, amount: str):
        """Обработка покупки"""
        user_id = query.from_user.id
        
        # Определяем продукт
        products = {
            # Stars
            "50_stars": {"type": "stars", "amount": 50, "price": 88, "currency": "RUB"},
            "250_stars": {"type": "stars", "amount": 250, "price": 400, "currency": "RUB"},
            "500_stars": {"type": "stars", "amount": 500, "price": 750, "currency": "RUB"},
            "1000_stars": {"type": "stars", "amount": 1000, "price": 1400, "currency": "RUB"},
            
            # Spins
            "1_spin": {"type": "spins", "amount": 1, "price": 50, "currency": "stars"},
            "5_spins": {"type": "spins", "amount": 5, "price": 225, "currency": "stars"},
            "10_spins": {"type": "spins", "amount": 10, "price": 400, "currency": "stars"},
            "25_spins": {"type": "spins", "amount": 25, "price": 900, "currency": "stars"}
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
            
            # Начисление спинов
            if product["type"] == "spins":
                await self.db.update_spins_balance(user_id, product["amount"])
                
                success_text = f"""
✅ *Покупка успешна!*

🎰 *Начислено:* {product['amount']} спинов
💰 *Потрачено:* {product['price']} stars
👛 *Баланс stars:* {await self.db.get_stars_balance(user_id)}
🎰 *Баланс спинов:* {await self.db.get_spins_balance(user_id)}
                """
            else:
                success_text = f"✅ Куплено {product['amount']} stars"
            
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
                currency=product["currency"]
            )
    
    async def pre_checkout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Подтверждение платежа"""
        query = update.pre_checkout_query
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
            total_amount=payment.total_amount // 100,
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
🎯 Играть в Моно (конвертировать в спины)
🎰 Купить спины (1 спин = 50 stars)
                """
            
            keyboard = [[
                InlineKeyboardButton("🎯 ИГРАТЬ В МОНО", callback_data="play_mono"),
                InlineKeyboardButton("💰 КУПИТЬ СПИНЫ", callback_data="buy_spins_menu")
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
    
    async def web_app_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка данных из Web App"""
        import json
        
        try:
            data = json.loads(update.effective_message.web_app_data.data)
            user_id = update.effective_user.id
            action = data.get('action')
            
            if action == 'mono_spin':
                # Обработка спина в Моно
                chance = data.get('chance', 1)
                bet_spins = data.get('bet_spins', 1)
                
                # Выполняем спин через игровую логику
                result = await self.mono_game.spin(user_id, chance, bet_spins)
                
                if result["success"]:
                    # Успешный спин
                    if result["won"]:
                        # Победа
                        win_text = f"""
🎉 *ПОБЕДА В МОНО!*

🎯 Шанс: {chance}%
🎰 Ставка: {bet_spins} спинов ({bet_spins * 50} stars)
💰 Множитель: {result['multiplier']}x
🏆 Выигрыш: {result['win_spins']:.2f} спинов ({result['win_stars']:.0f} stars)

👛 *Новый баланс:* {result['balance']} спинов
                        """
                        
                        if result.get('nft_awarded'):
                            nft = result['nft_awarded']
                            win_text += f"\n\n🎁 *ПОЛУЧЕН NFT!*\n{nft['name']} (ID: #{nft['id']})"
                        
                        # Показываем уведомление в боте
                        await update.message.reply_text(win_text, parse_mode='Markdown')
                        
                    else:
                        # Проигрыш
                        lose_text = f"""
😔 *ПРОИГРЫШ В МОНО*

🎯 Шанс: {chance}%
🎰 Ставка: {bet_spins} спинов ({bet_spins * 50} stars)
🎲 Выпало число: {result['win_number']}

💔 Потеряно: {bet_spins} спинов ({bet_spins * 50} stars)
👛 *Баланс:* {result['balance']} спинов

💪 *Не сдавайтесь! Удача обязательно улыбнется вам в следующий раз!*
                        """
                        
                        await update.message.reply_text(lose_text, parse_mode='Markdown')
                else:
                    # Ошибка
                    await update.message.reply_text(
                        f"❌ Ошибка: {result.get('error', 'Неизвестная ошибка')}",
                        parse_mode='Markdown'
                    )
            
        except json.JSONDecodeError:
            await update.message.reply_text("❌ Ошибка обработки данных")
        except Exception as e:
            logger.error(f"Ошибка обработки Web App данных: {e}")
            await update.message.reply_text("❌ Внутренняя ошибка сервера")
    
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
        except Exception as e:
            logger.error(f"Ошибка установки меню кнопки: {e}")
    
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
