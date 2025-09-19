"""
Payment handlers for Telegram Stars transactions.
Handles pre-checkout queries, successful payments, and purchase commands.
"""

import os
import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import ContextTypes

from src.database.db_manager import (
    get_available_products, get_product_by_id, create_transaction, 
    get_transaction_by_payload, complete_transaction, fail_transaction,
    get_user_transactions, get_user
)
from src.bot.animations import safe_reply

logger = logging.getLogger(__name__)

async def handle_pre_checkout_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pre-checkout query for Telegram Stars payments"""
    query = update.pre_checkout_query
    
    logger.info(f"Pre-checkout query from user {query.from_user.id}: {query.invoice_payload}")
    
    try:
        # Parse payload to get transaction info
        payload_parts = query.invoice_payload.split('_')
        if len(payload_parts) != 3 or payload_parts[0] != 'bait':
            logger.error(f"Invalid invoice payload: {query.invoice_payload}")
            await query.answer(ok=False, error_message="Invalid order data")
            return
        
        product_id = int(payload_parts[1])
        quantity = int(payload_parts[2])
        
        # Validate product
        product = await get_product_by_id(product_id)
        if not product:
            logger.error(f"Product not found: {product_id}")
            await query.answer(ok=False, error_message="Product not available")
            return
        
        # Validate amount
        expected_amount = product['stars_price'] * quantity
        if query.total_amount != expected_amount:
            logger.error(f"Amount mismatch: expected {expected_amount}, got {query.total_amount}")
            await query.answer(ok=False, error_message="Price mismatch")
            return
        
        # Validate user exists
        user = await get_user(query.from_user.id)
        if not user:
            logger.error(f"User not found: {query.from_user.id}")
            await query.answer(ok=False, error_message="User not registered")
            return
        
        # Create transaction record
        bait_amount = product['bait_amount'] * quantity
        transaction_id = await create_transaction(
            user_id=query.from_user.id,
            product_id=product_id,
            quantity=quantity,
            stars_amount=expected_amount,
            bait_amount=bait_amount,
            payload=query.invoice_payload
        )
        
        logger.info(f"Pre-checkout approved for user {query.from_user.id}, transaction: {transaction_id}")
        await query.answer(ok=True)
        
    except Exception as e:
        logger.error(f"Error in pre-checkout query: {e}")
        await query.answer(ok=False, error_message="Processing error")

async def handle_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle successful payment and deliver BAIT tokens"""
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    logger.info(f"Successful payment from user {user_id}: {payment.invoice_payload}")
    
    try:
        # Find transaction by payload
        transaction = await get_transaction_by_payload(payment.invoice_payload)
        if not transaction:
            logger.error(f"Transaction not found for payload: {payment.invoice_payload}")
            await safe_reply(update, "❌ Payment processing error. Please contact support.")
            return
        
        # Complete transaction
        success = await complete_transaction(
            transaction_id=transaction['id'],
            payment_charge_id=payment.provider_payment_charge_id or '',
            telegram_payment_charge_id=payment.telegram_payment_charge_id or '',
            provider_payment_charge_id=payment.provider_payment_charge_id or ''
        )
        
        if success:
            bait_received = transaction['bait_amount'] * transaction['quantity']
            
            success_message = f"""🎉 <b>Payment Successful!</b>

💰 <b>Purchase:</b> {transaction['quantity']}x BAIT Pack
🪱 <b>BAIT Received:</b> {bait_received} tokens
⭐ <b>Stars Paid:</b> {transaction['stars_amount']}

<b>🎣 Ready to fish!</b>
Your BAIT tokens have been added to your account. Use /cast to start fishing!

<i>Thank you for supporting Big Catchy! 🐟</i>"""
            
            await safe_reply(update, success_message)
            logger.info(f"Payment completed successfully for user {user_id}, added {bait_received} BAIT")
        else:
            await safe_reply(update, "❌ Payment processing error. Please contact support.")
            logger.error(f"Failed to complete transaction {transaction['id']}")
            
    except Exception as e:
        logger.error(f"Error in successful payment handler: {e}")
        await safe_reply(update, "❌ Payment processing error. Please contact support.")

async def buy_bait_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /buy command - show BAIT purchase options"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    try:
        # Check if user exists
        user = await get_user(user_id)
        if not user:
            await safe_reply(update, "🎣 Please start the bot first with /start")
            return
        
        # Get available products
        products = await get_available_products()
        if not products:
            await safe_reply(update, "❌ No products available at the moment.")
            return
        
        # Create purchase options
        keyboard = []
        for product in products:
            button_text = f"🪱 {product['bait_amount']} BAIT - ⭐{product['stars_price']}"
            callback_data = f"buy_bait_{product['id']}_1"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        purchase_message = f"""🛒 <b>BAIT Token Store</b>

<b>💰 Current Balance:</b> {user['bait_tokens']} BAIT tokens

<b>🪱 Available Packages:</b>
Choose a BAIT package below to continue fishing adventures!

⭐ <i>Payments are processed securely through Telegram Stars</i>"""
        
        await update.message.reply_text(
            purchase_message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in buy command: {e}")
        await safe_reply(update, "❌ Error loading store. Try again later.")

async def buy_bait_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle BAIT purchase callback"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    try:
        # Parse callback data: "buy_bait_<product_id>_<quantity>"
        if not query.data.startswith("buy_bait_"):
            return
        
        parts = query.data.split("_")
        if len(parts) != 4:
            await query.edit_message_text("❌ Invalid purchase data")
            return
        
        product_id = int(parts[2])
        quantity = int(parts[3])
        
        # Get product info
        product = await get_product_by_id(product_id)
        if not product:
            await query.edit_message_text("❌ Product not found")
            return
        
        # Calculate totals
        total_stars = product['stars_price'] * quantity
        total_bait = product['bait_amount'] * quantity
        
        # Generate unique payload
        payload = f"bait_{product_id}_{quantity}"
        
        # Create invoice
        title = f"BAIT Tokens x{quantity}"
        description = f"{total_bait} BAIT tokens for fishing"
        prices = [LabeledPrice(label="BAIT Tokens", amount=total_stars)]
        
        await context.bot.send_invoice(
            chat_id=user_id,
            title=title,
            description=description,
            payload=payload,
            provider_token="",  # Empty for Stars
            currency="XTR",
            prices=prices
        )
        
        # Update the message
        await query.edit_message_text(
            f"💳 <b>Invoice Sent!</b>\n\n"
            f"📦 <b>Product:</b> {product['name']}\n"
            f"🪱 <b>BAIT Amount:</b> {total_bait} tokens\n"
            f"⭐ <b>Price:</b> {total_stars} Stars\n\n"
            f"<i>Complete the payment to receive your BAIT tokens!</i>",
            parse_mode='HTML'
        )
        
        logger.info(f"Invoice sent to user {user_id}: {payload}")
        
    except Exception as e:
        logger.error(f"Error in buy callback: {e}")
        await query.edit_message_text("❌ Error creating invoice. Try again.")

async def transactions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /transactions command - show user's purchase history"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    try:
        # Get user transactions
        transactions = await get_user_transactions(user_id, limit=10)
        
        if not transactions:
            await safe_reply(update, 
                "📝 <b>Transaction History</b>\n\n"
                "No transactions found.\n\n"
                "<i>Use /buy to purchase BAIT tokens!</i>"
            )
            return
        
        # Format transaction history
        message_lines = ["📝 <b>Transaction History</b>\n"]
        
        for t in transactions:
            status_emoji = {
                'completed': '✅',
                'pending': '⏳',
                'failed': '❌',
                'refunded': '🔄'
            }.get(t['status'], '❓')
            
            date_str = t['created_at'].strftime('%Y-%m-%d %H:%M')
            
            message_lines.append(
                f"{status_emoji} <b>{t['product_name'] or 'BAIT Pack'}</b>\n"
                f"   🪱 {t['bait_amount']} BAIT • ⭐{t['stars_amount']} Stars\n"
                f"   📅 {date_str}\n"
            )
        
        message_lines.append("\n<i>Last 10 transactions shown</i>")
        
        await safe_reply(update, "\n".join(message_lines))
        
    except Exception as e:
        logger.error(f"Error in transactions command: {e}")
        await safe_reply(update, "❌ Error loading transaction history.")

async def send_low_bait_purchase_offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send purchase offer when user has no BAIT tokens"""
    user_id = update.effective_user.id
    
    try:
        # Get available products (quick options)
        products = await get_available_products()
        if not products:
            await safe_reply(update, "🎣 No $BAIT tokens! You need BAIT tokens to go fishing.")
            return
        
        # Create purchase buttons for all products
        keyboard = []
        for product in products:  # All 3 products
            button_text = f"🪱 Buy {product['bait_amount']} BAIT - ⭐{product['stars_price']}"
            callback_data = f"buy_bait_{product['id']}_1"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        no_bait_message = """🎣 <b>Out of BAIT Tokens!</b>

You need BAIT tokens to go fishing. Each cast costs 1 BAIT token.

🛒 <b>Quick Purchase Options:</b>
Get BAIT tokens instantly with Telegram Stars!

⭐ <i>Secure payment through Telegram</i>"""
        
        await update.message.reply_text(
            no_bait_message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error in low BAIT purchase offer: {e}")
        await safe_reply(update, "🎣 No $BAIT tokens! Use /buy to purchase more.")

