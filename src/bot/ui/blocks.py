"""
UI Blocks - Reusable message components for Telegram bot.

This module implements a component-based UI system similar to Vue.js,
where each block is a reusable component that renders to (text, markup) tuple.

Architecture:
- BlockData: Props/data container (like Vue props)
- Block: Base component class with render() mTACod
- CTABlock: Call-to-action block with buttons
- InfoBlock: Information display without buttons
- AnimationBlock: Temporary editable block for processes
- ErrorBlock: Error display with recovery actions

Design Principles:
1. All interactive elements should use buttons (not text commands)
2. One CTA block active at a time on user's screen
3. Each block has structure: Header + Body + (optional) Footer + Buttons
4. Text commands are for pro users only (shown in hints)
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
import os


def get_webapp_url() -> Optional[str]:
    """Get WebApp URL from environment or return None if not configured."""
    return os.environ.get('WEBAPP_URL')


def get_miniapp_button() -> List[Tuple[str, str]]:
    """
    Get MiniApp button as web_app_buttons list.
    Returns empty list if WEBAPP_URL is not configured.

    Usage:
        data = BlockData(
            header="Success!",
            body="...",
            buttons=[("Action", "callback")],
            web_app_buttons=get_miniapp_button()
        )
    """
    webapp_url = get_webapp_url()
    if webapp_url:
        return [("🐟 Open MiniApp", webapp_url)]
    return []


@dataclass
class BlockData:
    """
    Data container for block rendering (similar to Vue props).

    Attributes:
        header: Bold header text (what happened / current status)
        body: Main paragraph (context, explanation, why act)
        buttons: List of (button_text, callback_data) tuples for callback buttons
        web_app_buttons: List of (button_text, web_app_url) tuples for WebApp buttons
        footer: Optional italic footer (hints, additional info)
        image_url: Optional image URL (for future use)

    Example:
        data = BlockData(
            header="🎣 Great Catch!",
            body="You caught a rare fish. Share it with the group?",
            buttons=[("📢 Share", "share_hook")],
            web_app_buttons=[("🐟 Open Collection", "https://app.example.com")],
            footer="Sharing gives +1 BAIT token"
        )
    """
    header: str
    body: str
    buttons: List[Tuple[str, str]] = field(default_factory=list)
    web_app_buttons: List[Tuple[str, str]] = field(default_factory=list)
    footer: Optional[str] = None
    image_url: Optional[str] = None


class Block:
    """
    Base Block class - abstract component.

    All blocks implement render() mTACod that converts BlockData
    into (message_text, keyboard_markup) tuple.
    """

    @staticmethod
    def render(data: BlockData) -> Tuple[str, Optional[InlineKeyboardMarkup]]:
        """
        Render block to (text, markup) tuple.

        Args:
            data: BlockData with content

        Returns:
            Tuple of (message_text, keyboard_markup or None)
        """
        raise NotImplementedError("Subclasses must implement render()")


class CTABlock(Block):
    """
    CTA (Call-To-Action) Block Component.

    Primary UI pattern for interactive moments. Shows user what happened
    and provides clear buttons for next actions.

    Structure:
        <b>Bold Header</b>

        Body paragraph explaining context and why user should act.

        <i>Optional footer with hints</i>

        [Button 1] [Button 2] [Button 3]

    Usage:
        data = BlockData(
            header="🎉 Payment Successful!",
            body="You received 10 BAIT tokens. Ready to fish?",
            buttons=[("🎣 Start Fishing", "quick_cast")],
            footer="Each cast costs 1 BAIT token"
        )
        text, markup = CTABlock.render(data)

        await bot.send_message(chat_id=user_id, text=text, reply_markup=markup)
    """

    @staticmethod
    def render(data: BlockData) -> Tuple[str, InlineKeyboardMarkup]:
        """Render CTA block with header, body, optional footer, and buttons."""
        from telegram import WebAppInfo

        # Build message text
        message = f"<b>{data.header}</b>\n\n{data.body}"

        if data.footer:
            message += f"\n\n<i>{data.footer}</i>"

        # Build keyboard (one button per row for clarity)
        keyboard = []

        # Add callback buttons
        for btn_text, callback_data in data.buttons:
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])

        # Add WebApp buttons
        for btn_text, web_app_url in data.web_app_buttons:
            keyboard.append([InlineKeyboardButton(btn_text, web_app=WebAppInfo(url=web_app_url))])

        markup = InlineKeyboardMarkup(keyboard) if keyboard else InlineKeyboardMarkup([])

        return message, markup


class InfoBlock(Block):
    """
    Info Block Component.

    Pure information display without action buttons. Used for:
    - Status displays
    - Help/guide content
    - Process status (fishing in progress)
    - Statistics and data

    Structure:
        <b>Bold Header</b>

        Body with information, stats, data.
        Can be multi-line with formatted content.

        <i>Optional pro tip command hint</i>

    No buttons - commands are mentioned in footer for pro users.

    Usage:
        data = BlockData(
            header="📊 Fishing Status",
            body="Rod: Long rod (2.0x)\\nPnL: +2.5%\\nTime: 5min 32s",
            footer="Pro tip: Use /hook to complete your catch"
        )
        text, _ = InfoBlock.render(data)

        await bot.send_message(chat_id=user_id, text=text)
    """

    @staticmethod
    def render(data: BlockData) -> Tuple[str, None]:
        """Render info block with header, body, and optional hint. No buttons."""
        message = f"<b>{data.header}</b>\n\n{data.body}"

        if data.footer:
            message += f"\n\n<i>{data.footer}</i>"

        return message, None


class AnimationBlock(Block):
    """
    Animation Block Component.

    Temporary editable message for processes and animations.
    No buttons - will be replaced by CTA block when complete.

    Used for:
    - Cast animation sequence
    - Hook animation sequence
    - Loading states
    - Progress indicators

    Structure:
        Animated Header

        Animated body content

    Note: Message will be edited via edit_message_text() during animation.

    Usage:
        # Initial frame
        data = BlockData(
            header="🎣 Casting...",
            body="💦 SPLASH! Bait sinking..."
        )
        text, _ = AnimationBlock.render(data)
        msg = await bot.send_message(chat_id=user_id, text=text)

        # Update frames
        for frame in animation_frames:
            data.body = frame
            text, _ = AnimationBlock.render(data)
            await msg.edit_text(text)
    """

    @staticmethod
    def render(data: BlockData) -> Tuple[str, None]:
        """Render animation frame. No buttons."""
        if data.body:
            message = f"{data.header}\n\n{data.body}"
        else:
            message = data.header

        return message, None


class ErrorBlock(Block):
    """
    Error Block Component.

    Similar to CTA block but specifically for error states.
    Shows what went wrong and provides recovery action buttons.

    Structure:
        ❌ <b>Error Header</b>

        Error description explaining what happened and why.

        [Recovery Action 1] [Alternative Action 2]

    Usage:
        data = BlockData(
            header="❌ Already Fishing!",
            body="You already have a rod in the water. Complete your current catch first.",
            buttons=[
                ("🪝 Hook Now", "quick_hook"),
                ("📊 Check Status", "show_status")
            ]
        )
        text, markup = ErrorBlock.render(data)

        await bot.send_message(chat_id=user_id, text=text, reply_markup=markup)
    """

    @staticmethod
    def render(data: BlockData) -> Tuple[str, InlineKeyboardMarkup]:
        """
        Render error block with recovery actions.
        Uses same structure as CTA block.
        """
        return CTABlock.render(data)


# Convenience factory functions for common patterns

def build_success_block(
    header: str,
    body: str,
    primary_action: Tuple[str, str],
    secondary_action: Optional[Tuple[str, str]] = None,
    footer: Optional[str] = None
) -> BlockData:
    """
    Build a success CTA block with 1-2 action buttons.

    Args:
        header: Success header (e.g., "🎉 Great Catch!")
        body: Success message body
        primary_action: (button_text, callback_data) for main action
        secondary_action: Optional (button_text, callback_data) for alternative
        footer: Optional footer hint

    Returns:
        BlockData ready for CTABlock.render()

    Example:
        data = build_success_block(
            header="🎉 Payment Complete!",
            body="You received 10 BAIT tokens.",
            primary_action=("🎣 Start Fishing", "quick_cast"),
            footer="Each cast costs 1 BAIT"
        )
    """
    buttons = [primary_action]
    if secondary_action:
        buttons.append(secondary_action)

    return BlockData(
        header=header,
        body=body,
        buttons=buttons,
        footer=footer
    )


def build_error_block(
    header: str,
    body: str,
    recovery_action: Tuple[str, str],
    alternative_action: Optional[Tuple[str, str]] = None
) -> BlockData:
    """
    Build an error block with recovery actions.

    Args:
        header: Error header (should start with ❌)
        body: Error explanation
        recovery_action: Primary recovery button
        alternative_action: Optional alternative action

    Returns:
        BlockData ready for ErrorBlock.render()

    Example:
        data = build_error_block(
            header="❌ No BAIT Tokens!",
            body="You need BAIT to go fishing.",
            recovery_action=("💰 Buy BAIT", "buy_bait_1_1"),
            alternative_action=("📊 Check Balance", "show_status")
        )
    """
    buttons = [recovery_action]
    if alternative_action:
        buttons.append(alternative_action)

    return BlockData(
        header=header,
        body=body,
        buttons=buttons
    )


def build_info_block(
    header: str,
    body: str,
    command_hint: Optional[str] = None
) -> BlockData:
    """
    Build an info block for displaying information.

    Args:
        header: Info header
        body: Information content
        command_hint: Optional command hint for pro users

    Returns:
        BlockData ready for InfoBlock.render()

    Example:
        data = build_info_block(
            header="📊 Your Stats",
            body="Catches: 42\\nBalance: $12,500",
            command_hint="Use /cast to continue fishing"
        )
    """
    return BlockData(
        header=header,
        body=body,
        footer=command_hint
    )
