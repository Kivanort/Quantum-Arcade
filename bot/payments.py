import logging
from typing import Dict, Optional
from telegram import LabeledPrice

logger = logging.getLogger(__name__)

class PaymentSystem:
    """Система обработки платежей"""
    
    def __init__(self, provider_token: str, db):
        self.provider_token = provider_token
        self.db = db
    
    async def create_invoice(self, chat_id: int, product_type: str, 
                            amount: int, price: int, currency: str = "RUB"):
        """Создать счет для оплаты"""
        from telegram import Bot
        
        # Получаем бота из контекста или создаем новый
        # В реальном проекте нужно передать бота
        bot = Bot(token="YOUR_BOT_TOKEN")  # Замените на ваш токен
        
        title = ""
        description = ""
        
        if product_type == "stars":
            title = f"Пополнение баланса на {amount} stars"
            description = f"Покупка {amount} stars для игр в казино"
        elif product_type == "spins":
            title = f"Покупка {amount} спинов"
            description = f"Покупка {amount} спинов для игры в Моно"
        
        payload = f"{product_type}_{amount}_{chat_id}"
        prices = [LabeledPrice(title, price * 100)]  # в копейках
        
        try:
            await bot.send_invoice(
                chat_id=chat_id,
                title=title,
                description=description,
                payload=payload,
                provider_token=self.provider_token,
                currency=currency,
                prices=prices,
                need_name=False,
                need_phone_number=False,
                need_email=False,
                need_shipping_address=False,
                is_flexible=False
            )
            
            logger.info(f"Счет создан для {chat_id}: {title}")
            
        except Exception as e:
            logger.error(f"Ошибка создания счета для {chat_id}: {e}")
    
    async def process_successful_payment(self, user_id: int, 
                                        telegram_payment_charge_id: str,
                                        provider_payment_charge_id: str,
                                        total_amount: int,
                                        invoice_payload: str) -> Dict:
        """Обработать успешный платеж"""
        
        # Проверяем, не обрабатывался ли уже этот платеж
        existing_payment = await self.db.get_payment_by_telegram_id(
            telegram_payment_charge_id
        )
        
        if existing_payment:
            logger.warning(f"Платеж {telegram_payment_charge_id} уже обработан")
            return {
                "success": False,
                "error": "Платеж уже обработан"
            }
        
        # Парсим payload для определения типа продукта
        try:
            parts = invoice_payload.split("_")
            if len(parts) >= 2:
                product_type = parts[0]
                amount = int(parts[1])
            else:
                product_type = "stars"
                amount = total_amount
        except:
            product_type = "stars"
            amount = total_amount
        
        # Сохраняем платеж в БД
        payment_id = await self.db.add_payment(
            user_id=user_id,
            amount=total_amount,
            currency="RUB",
            provider="yookassa",  # или другой провайдер
            provider_payment_charge_id=provider_payment_charge_id,
            telegram_payment_charge_id=telegram_payment_charge_id,
            status="completed",
            product_type=product_type,
            product_amount=amount,
            invoice_payload=invoice_payload
        )
        
        logger.info(f"Платеж {payment_id} сохранен для пользователя {user_id}")
        
        return {
            "success": True,
            "payment_id": payment_id,
            "product_type": product_type,
            "amount": amount
        }
