"""
Bot configuration module for setup and initialization.
Handles command setup and other bot-wide configuration.
"""

import os
import logging
from telegram import BotCommand, BotCommandScopeAllPrivateChats, BotCommandScopeAllGroupChats
from telegram import MenuButtonWebApp, WebAppInfo
from telegram.ext import Application

logger = logging.getLogger(__name__)


async def setup_bot_commands(application: Application) -> None:
    """
    Configure bot commands for different chat types.
    Sets up commands visible in Telegram's command menu.
    """
    try:
        # Commands for private chats
        private_commands = [
            BotCommand("cast", "Open position"),
            BotCommand("hook", "Close position"),
            BotCommand("status", "View current position"),
            BotCommand("leaderboard", "View leaderboard"),
            BotCommand("help", "Game help and instructions"),
        ]

        # Commands for group chats
        group_commands = [
            BotCommand("gofishing", "Start fishing in this group"),
            BotCommand("leaderboard", "View group leaderboard"),
        ]

        # Set commands for private chats
        await application.bot.set_my_commands(
            private_commands,
            scope=BotCommandScopeAllPrivateChats()
        )
        logger.info(f"✅ Set {len(private_commands)} commands for private chats")

        # Set commands for group chats
        await application.bot.set_my_commands(
            group_commands,
            scope=BotCommandScopeAllGroupChats()
        )
        logger.info(f"✅ Set {len(group_commands)} commands for group chats")

    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")
        # Don't raise - bot can still work without commands in menu


async def setup_menu_button(application: Application) -> None:
    """
    Configure the menu button to open Mini App.
    This button appears next to the message input field.
    """
    webapp_url = os.environ.get('WEBAPP_URL')

    if not webapp_url:
        logger.info("ℹ️ WEBAPP_URL not set - skipping menu button setup")
        return

    try:
        # Set menu button for all private chats
        menu_button = MenuButtonWebApp(
            text="🎣 Play Game",
            web_app=WebAppInfo(url=webapp_url)
        )

        await application.bot.set_chat_menu_button(menu_button=menu_button)
        logger.info(f"✅ Set menu button with Mini App URL: {webapp_url}")

    except Exception as e:
        logger.error(f"Failed to set menu button: {e}")
        # Don't raise - bot can still work without menu button


async def configure_bot(application: Application) -> None:
    """
    Main bot configuration function.
    Call this during bot startup to apply all configurations.
    """
    await setup_bot_commands(application)
    # await setup_menu_button(application)  # Disabled - standard menu with commands is better

    # Add more bot-wide configurations here as needed:
    # - Set bot description
    # - Set bot short description
    # - Configure default settings
    # etc.
