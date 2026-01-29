"""
Telegram Bot Integration
"""
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from typing import Dict, Any
from .agent import Agent


class TelegramBot:
    def __init__(self, token: str, agent: Agent, allowed_users: list = None):
        self.token = token
        self.agent = agent
        self.allowed_users = set(allowed_users) if allowed_users else None
        self.application = None
        
    def _is_allowed(self, user_id: int) -> bool:
        """
        Check if user is allowed to use the bot
        """
        if self.allowed_users is None:
            return True  # No restriction
        return user_id in self.allowed_users
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /start command
        """
        user_id = update.effective_user.id
        
        if not self._is_allowed(user_id):
            await update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return
        
        welcome_msg = (
            "🤖 **vLLM Bot**\n\n"
            "I'm an AI assistant powered by vLLM with access to:\n"
            "- File operations (read/write/edit)\n"
            "- Command execution (exec)\n\n"
            "Send me a message to get started!\n\n"
            "Commands:\n"
            "/start - Show this message\n"
            "/reset - Reset conversation history"
        )
        await update.message.reply_text(welcome_msg, parse_mode="Markdown")
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle /reset command
        """
        user_id = update.effective_user.id
        
        if not self._is_allowed(user_id):
            return
        
        self.agent.reset_conversation(user_id)
        await update.message.reply_text("✅ Conversation history reset!")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle text messages
        """
        user_id = update.effective_user.id
        
        if not self._is_allowed(user_id):
            await update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return
        
        user_message = update.message.text
        
        # Send typing indicator
        await update.message.chat.send_action("typing")
        
        try:
            # Get response from agent
            response = self.agent.chat(user_id, user_message)
            
            # Split long messages (Telegram limit: 4096 chars)
            max_length = 4096
            if len(response) <= max_length:
                await update.message.reply_text(response)
            else:
                # Split into chunks
                chunks = [response[i:i+max_length] for i in range(0, len(response), max_length)]
                for chunk in chunks:
                    await update.message.reply_text(chunk)
                    await asyncio.sleep(0.5)  # Avoid rate limiting
                    
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            await update.message.reply_text(error_msg)
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle errors
        """
        print(f"Error occurred: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "An error occurred while processing your request."
            )
    
    def run(self):
        """
        Start the bot
        """
        # Create application
        self.application = Application.builder().token(self.token).build()
        
        # Add handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Add error handler
        self.application.add_error_handler(self.error_handler)
        
        # Start polling
        print("🤖 Bot started! Polling for messages...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
