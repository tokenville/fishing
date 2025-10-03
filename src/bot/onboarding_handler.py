"""Onboarding system handler for the fishing bot.
Implements a lightweight state-driven tutorial that wraps core commands.
"""

import logging
import os
from typing import Callable, Dict, List, Optional, Tuple

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

from src.database.db_manager import (
    create_onboarding_progress,
    get_available_ponds,
    get_onboarding_progress,
    get_user,
    get_user_group_ponds,
    update_onboarding_step,
    complete_onboarding,
    is_onboarding_completed,
    award_group_bonus,
    award_first_catch_reward,
    ensure_user_has_level,
)

logger = logging.getLogger(__name__)


class OnboardingHandler:
    """Handles the onboarding flow for new users."""

    STEP_INTRO = "intro"
    STEP_JOIN_GROUP = "join_group"
    STEP_CAST = "cast_instruction"
    STEP_HOOK = "hook_instruction"
    STEP_COMPLETED = "completed"

    def __init__(self) -> None:
        self.group_invite_link = os.environ.get("ONBOARDING_GROUP_INVITE_URL")
        group_chat_id = os.environ.get("ONBOARDING_GROUP_CHAT_ID")
        try:
            self.group_chat_id = int(group_chat_id) if group_chat_id else None
        except ValueError:
            logger.warning("Invalid ONBOARDING_GROUP_CHAT_ID value: %s", group_chat_id)
            self.group_chat_id = None
        self._step_builders: Dict[str, Callable[..., Tuple[str, List[List[InlineKeyboardButton]]]]] = {
            self.STEP_INTRO: self._build_intro_step,
            self.STEP_JOIN_GROUP: self._build_join_group_step,
            self.STEP_CAST: self._build_cast_step,
            self.STEP_HOOK: self._build_hook_step,
            self.STEP_COMPLETED: self._build_completion_step,
        }

    async def get_user_current_step(self, user_id: int) -> str:
        """Return the current onboarding step for the user."""
        progress = await get_onboarding_progress(user_id)
        if not progress:
            logger.info("Creating onboarding progress record for user %s", user_id)
            await create_onboarding_progress(user_id, step=self.STEP_INTRO)
            return self.STEP_INTRO

        if progress.get("completed"):
            return self.STEP_COMPLETED

        return progress.get("current_step", self.STEP_INTRO)

    async def advance_step(self, user_id: int, next_step: str) -> None:
        """Persist the next onboarding step for the user."""
        if next_step == self.STEP_COMPLETED:
            await complete_onboarding(user_id)
        else:
            await update_onboarding_step(user_id, next_step)
        logger.info("Advanced user %s to onboarding step %s", user_id, next_step)

    async def send_step_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        step_id: str,
        **kwargs,
    ) -> None:
        """Render and send a message for the requested step."""
        message, markup = await self._build_step_payload(user_id, step_id, **kwargs)

        chat_id = user_id
        if update and getattr(update, "effective_chat", None):
            chat_id = update.effective_chat.id

        if update and getattr(update, "callback_query", None):
            try:
                await update.callback_query.answer()
            except Exception:
                logger.debug("Callback query answer failed for user %s", user_id)

        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=markup,
            parse_mode='HTML'
        )

    async def handle_command_trigger(
        self,
        user_id: int,
        command: str,
        **kwargs,
    ) -> Optional[Dict[str, InlineKeyboardMarkup]]:
        """React to tutorial-sensitive commands (/cast, /hook)."""
        current_step = await self.get_user_current_step(user_id)

        if current_step == self.STEP_CAST and command == "/cast":
            await self.advance_step(user_id, self.STEP_HOOK)
            message, keyboard = await self._build_hook_step(user_id)
            markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            return {"send_message": message, "reply_markup": markup}

        if current_step == self.STEP_HOOK and command == "/hook":
            # Don't advance step yet - we'll do it after reward claim
            reward_summary = await award_first_catch_reward(user_id)
            message, keyboard = await self._build_first_catch_congrats(user_id)
            markup = InlineKeyboardMarkup(keyboard) if keyboard else None
            return {
                "send_message": message,
                "reply_markup": markup,
                "reward_message": reward_summary
            }

        return None

    async def should_show_mini_app(self, user_id: int) -> bool:
        """Show Mini App button only after tutorial completion."""
        return await is_onboarding_completed(user_id)

    async def _build_step_payload(
        self, user_id: int, step_id: str, **kwargs
    ) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        builder = self._step_builders.get(step_id, self._build_intro_step)
        message, keyboard = await builder(user_id, **kwargs)
        markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        return message, markup

    async def _build_intro_step(
        self, user_id: int, **_: Dict[str, str]
    ) -> Tuple[str, List[List[InlineKeyboardButton]]]:
        message = (
            "🎣 Welcome to the degen fishing simulator.\n"
            "Here you scalp crypto by catching fish JPEGs.\n"
            "Learn the mechanics in 3 steps:\n"
            "• Cast = open a position\n"
            "• Telegram group = your trading pond\n"
            "• Hook = close position & collect JPEG\n\n"
            "Start fishing now and dominate your pond's leaderboard!"
        )
        keyboard = [
            [InlineKeyboardButton("🚀 Start tutorial (+10 BAIT)", callback_data="ob_start")],
            [InlineKeyboardButton("⏭️ Skip (no bonuses)", callback_data="ob_skip")],
        ]
        return message, keyboard

    async def _build_join_group_step(
        self, user_id: int, **_: Dict[str, str]
    ) -> Tuple[str, List[List[InlineKeyboardButton]]]:
        await ensure_user_has_level(user_id)
        user = await get_user(user_id)
        user_level = user["level"] if user else 1

        available_ponds = await get_available_ponds(user_level)
        user_group_ponds = await get_user_group_ponds(user_id)

        pond_names = {
            pond["name"]
            for pond in available_ponds
            if pond["is_active"]
        }
        pond_names.update(
            pond["name"]
            for pond in user_group_ponds
            if pond["is_active"]
        )

        if pond_names:
            pond_lines = "\n".join(f"• {name}" for name in sorted(pond_names)[:5])
            ponds_text = (
                "<b>Your available ponds:</b>\n"
                f"{pond_lines}\n\n"
            )
        else:
            ponds_text = (
                "<i>No active ponds yet. Connect your first one to cast your rod.</i>\n\n"
            )

        message = (
            "🏞️ <b>Step 1 of 3 — connect to a pond</b>\n\n"
            "Every Telegram group with this bot = a trading pond.\n"
            "You fish (trade) there, compete on the leaderboard, flex your catches.\n\n"
            f"{ponds_text}"
            "Join the main pond now and claim +10 BAIT for your first cast."
        )

        keyboard: List[List[InlineKeyboardButton]] = []
        if self.group_invite_link:
            keyboard.append([
                InlineKeyboardButton("👥 Join TAC Fishing Club", url=self.group_invite_link)
            ])

        keyboard.append([
            InlineKeyboardButton("✅ I joined — claim 10 BAIT", callback_data="ob_claim_bonus")
        ])
        keyboard.append([
            InlineKeyboardButton("➡️ Continue to cast", callback_data="ob_continue_cast")
        ])

        return message, keyboard

    async def _build_cast_step(
        self, user_id: int, **_: Dict[str, str]
    ) -> Tuple[str, List[List[InlineKeyboardButton]]]:
        message = (
            "🎯 <b>Step 2 of 3 — cast your rod</b>\n\n"
            "1. Hit /cast or tap the button below.\n"
            "2. Pick your pond (group).\n"
            "3. Rod drops into water = position opens at current price.\n\n"
            "Each cast costs 1 BAIT token.\n\n"
            "Your first cast is free and unlocks starter rods: Long & Short with different leverage.\n\n"
            "Track your open position anytime with /status."
        )

        keyboard = [
            [InlineKeyboardButton("🎣 Cast", callback_data="ob_send_cast")],
        ]
        return message, keyboard

    async def _build_hook_step(
        self, user_id: int, **_: Dict[str, str]
    ) -> Tuple[str, List[List[InlineKeyboardButton]]]:
        message = (
            "⚡ <b>Step 3 of 3 — hook your catch</b>\n\n"
            "Once your rod is in the water, /hook closes the position.\n"
            "Higher PnL = rarer fish JPEG. Even losses give you collectible trash fish.\n\n"
            "Your rod determines leverage: Long for upside, Short for downside (more rods coming soon).\n\n"
            "First catch bonus: +$1000 virtual balance to kickstart your leaderboard grind!"
        )

        keyboard = [
            [InlineKeyboardButton("🐟 Hook (+$1000)", callback_data="ob_send_hook")],
        ]
        return message, keyboard

    async def _build_first_catch_congrats(
        self,
        user_id: int,
        **_: Dict[str, str],
    ) -> Tuple[str, List[List[InlineKeyboardButton]]]:
        message = (
            "🎉 <b>Congrats on your first catch!</b>\n\n"
            "You've earned +$1000 virtual balance to kickstart your trading journey.\n"
            "Claim it now to boost your leaderboard position!"
        )
        keyboard = [
            [InlineKeyboardButton("🏆 Claim $1000 reward", callback_data="ob_claim_reward")],
        ]
        return message, keyboard

    async def _build_completion_step(
        self,
        user_id: int,
        **_: Dict[str, str],
    ) -> Tuple[str, List[List[InlineKeyboardButton]]]:
        message = (
            "🎉 <b>Tutorial complete!</b>\n\n"
            "You're now unrestricted. Cast and hook at will."
            " Keep grinding and push for #1 on your pond's leaderboard."
            " Open the Mini App to flex your fish collection, swap rods, and prepare for new drops."
        )

        keyboard = [
            [InlineKeyboardButton("🎣 Catch more", callback_data="ob_send_cast")],
        ]
        webapp_url = os.environ.get('WEBAPP_URL')
        if webapp_url:
            keyboard.append([
                InlineKeyboardButton("🎮 Open Mini App", web_app=WebAppInfo(url=webapp_url))
            ])
        return message, keyboard

    async def build_completion_message(
        self,
        user_id: int,
    ) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        message, keyboard = await self._build_completion_step(user_id)
        markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        return message, markup


# Global onboarding handler instance
onboarding_handler = OnboardingHandler()


# Convenience functions for other modules
async def get_current_onboarding_step(user_id: int) -> str:
    return await onboarding_handler.get_user_current_step(user_id)


async def send_onboarding_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    step_id: str,
    **kwargs,
) -> None:
    await onboarding_handler.send_step_message(update, context, user_id, step_id, **kwargs)


async def handle_onboarding_command(user_id: int, command: str, **kwargs):
    return await onboarding_handler.handle_command_trigger(user_id, command, **kwargs)


async def should_show_mini_app_button(user_id: int) -> bool:
    return await onboarding_handler.should_show_mini_app(user_id)


async def skip_onboarding(user_id: int) -> None:
    await complete_onboarding(user_id)
    logger.info("User %s skipped onboarding", user_id)


def reload_onboarding_scenario() -> None:
    """Backward compatibility hook for legacy tooling."""
    logger.info("reload_onboarding_scenario() called — state-based onboarding is in-memory and needs no reload")
