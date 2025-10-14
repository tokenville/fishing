"""
View Controller - Manages user's screen state and UI rendering.

This module implements a view controller similar to Vue Router + State Management,
controlling what the user sees on their screen at any given time.

Architecture:
- ViewController: Main controller class
- Manages active CTA blocks and animations
- Ensures only ONE active CTA block at a time
- Handles transitions between UI states

Design Principles:
1. One active CTA block at a time on user's screen
2. Clear old CTA before showing new one
3. Animation → CTA transitions are smooth
4. State-aware UI (different UI for different states)
"""

import asyncio
import logging
from typing import Optional, List, Type
from telegram import Message
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from .blocks import Block, BlockData, CTABlock, InfoBlock, AnimationBlock, ErrorBlock
from .state_machine import StateMachine, UserState, get_state_machine

logger = logging.getLogger(__name__)


class ViewController:
    """
    View Controller - Manages the visual state of user's chat screen.

    Similar to Vue Router - manages what user sees and ensures
    consistent UI state throughout the application.

    Responsibilities:
    - Track active CTA block message_id
    - Ensure only ONE active CTA block at a time
    - Handle block transitions (animation → CTA)
    - Clean up old blocks before showing new ones
    - Provide state-aware UI rendering
    """

    def __init__(self, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """
        Initialize view controller.

        Args:
            context: Telegram context
            user_id: Telegram user ID
        """
        self.context = context
        self.user_data = context.user_data
        self.user_id = user_id
        self.state_machine = get_state_machine(user_id)

    @property
    def active_cta_message_id(self) -> Optional[int]:
        """Get currently active CTA block message ID."""
        return self.user_data.get('active_cta_message_id')

    @active_cta_message_id.setter
    def active_cta_message_id(self, value: Optional[int]):
        """Set active CTA block message ID."""
        if value is None:
            self.user_data.pop('active_cta_message_id', None)
        else:
            self.user_data['active_cta_message_id'] = value

    @property
    def animation_message_id(self) -> Optional[int]:
        """Get currently active animation message ID."""
        return self.user_data.get('animation_message_id')

    @animation_message_id.setter
    def animation_message_id(self, value: Optional[int]):
        """Set animation message ID."""
        if value is None:
            self.user_data.pop('animation_message_id', None)
        else:
            self.user_data['animation_message_id'] = value

    async def clear_active_cta(self, chat_id: int) -> None:
        """
        Clear currently active CTA block.

        Removes buttons from the previous CTA message to prevent
        user confusion and ensure only one set of actions visible.

        Args:
            chat_id: User chat ID
        """
        if not self.active_cta_message_id:
            return

        try:
            # Remove buttons from old CTA
            await self.context.bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=self.active_cta_message_id,
                reply_markup=None
            )
            logger.debug(f"Cleared CTA buttons from message {self.active_cta_message_id}")
        except TelegramError as e:
            logger.debug(f"Could not clear old CTA: {e}")
        finally:
            self.active_cta_message_id = None

    async def show_cta_block(
        self,
        chat_id: int,
        block_type: Type[Block],
        data: BlockData,
        clear_previous: bool = True
    ) -> Message:
        """
        Show a CTA block (primary UI pattern).

        Pattern:
        1. Clear previous CTA (if exists and clear_previous=True)
        2. Render new block
        3. Send message
        4. Store message_id as active CTA

        Args:
            chat_id: User chat ID
            block_type: CTABlock or ErrorBlock class
            data: BlockData with content
            clear_previous: Clear previous CTA before showing new one (default: True)

        Returns:
            Sent message object

        Example:
            view = get_view_controller(context, user_id)
            await view.show_cta_block(
                chat_id=user_id,
                block_type=CTABlock,
                data=BlockData(
                    header="🎉 Success!",
                    body="Operation complete",
                    buttons=[("Continue", "continue")]
                )
            )
        """
        # Step 1: Clear previous CTA
        if clear_previous:
            await self.clear_active_cta(chat_id)

        # Step 2: Render block
        text, markup = block_type.render(data)

        # Step 3: Send message
        message = await self.context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=markup,
            parse_mode='HTML'
        )

        # Step 4: Track as active CTA
        self.active_cta_message_id = message.message_id

        logger.info(f"Showed {block_type.__name__} for user {chat_id}, msg_id={message.message_id}")
        return message

    async def show_info_block(
        self,
        chat_id: int,
        data: BlockData
    ) -> Message:
        """
        Show an info block (no buttons, no state tracking).

        Used for status displays, help content, and informational messages.
        Does not track message_id since it's not interactive.

        Args:
            chat_id: User chat ID
            data: BlockData with content

        Returns:
            Sent message object

        Example:
            await view.show_info_block(
                chat_id=user_id,
                data=BlockData(
                    header="📊 Status",
                    body="Current state info...",
                    footer="Use /command for more"
                )
            )
        """
        text, _ = InfoBlock.render(data)

        message = await self.context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML'
        )

        return message

    async def start_animation(
        self,
        chat_id: int,
        initial_data: BlockData
    ) -> Message:
        """
        Start an animation sequence.

        Returns message that can be edited for animation frames.
        Tracks animation_message_id for updates.

        Args:
            chat_id: User chat ID
            initial_data: Initial frame data

        Returns:
            Message object for animation

        Example:
            msg = await view.start_animation(
                chat_id=user_id,
                initial_data=BlockData(
                    header="🎣 Casting...",
                    body="Starting cast..."
                )
            )
        """
        text, _ = AnimationBlock.render(initial_data)

        message = await self.context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='HTML'
        )

        # Track animation message
        self.animation_message_id = message.message_id

        logger.debug(f"Started animation for user {chat_id}, msg_id={message.message_id}")
        return message

    async def update_animation(
        self,
        chat_id: int,
        data: BlockData
    ) -> bool:
        """
        Update animation frame.

        Args:
            chat_id: User chat ID
            data: New frame data

        Returns:
            True if update succeeded, False otherwise
        """
        if not self.animation_message_id:
            logger.warning(f"No active animation to update for user {chat_id}")
            return False

        text, _ = AnimationBlock.render(data)

        try:
            await self.context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=self.animation_message_id,
                text=text,
                parse_mode='HTML'
            )
            return True
        except TelegramError as e:
            logger.debug(f"Animation update failed: {e}")
            return False

    async def finish_animation(self) -> None:
        """Mark animation as finished, clear tracking."""
        self.animation_message_id = None

    async def delete_animation(self, chat_id: int) -> bool:
        """
        Delete animation message.

        Args:
            chat_id: User chat ID

        Returns:
            True if deleted successfully
        """
        if not self.animation_message_id:
            return False

        try:
            await self.context.bot.delete_message(
                chat_id=chat_id,
                message_id=self.animation_message_id
            )
            self.finish_animation()
            return True
        except TelegramError as e:
            logger.debug(f"Could not delete animation: {e}")
            return False

    async def transition_animation_to_cta(
        self,
        chat_id: int,
        cta_data: BlockData,
        keep_animation: bool = True
    ) -> Message:
        """
        Transition from animation to CTA block.

        Pattern: Animation completes → Show CTA with next actions

        Args:
            chat_id: User chat ID
            cta_data: CTA block data
            keep_animation: If True, keep animation message; if False, delete it

        Returns:
            New CTA message

        Example:
            # After animation completes
            await view.transition_animation_to_cta(
                chat_id=user_id,
                cta_data=BlockData(
                    header="✅ Complete!",
                    body="What's next?",
                    buttons=[("Continue", "continue")]
                ),
                keep_animation=True  # Keep animation visible
            )
        """
        # Optionally delete animation message
        if not keep_animation and self.animation_message_id:
            await self.delete_animation(chat_id)
        else:
            self.finish_animation()

        # Show CTA
        return await self.show_cta_block(
            chat_id=chat_id,
            block_type=CTABlock,
            data=cta_data
        )

    async def get_current_state(self) -> UserState:
        """
        Get current user state from state machine.

        Returns:
            Current UserState
        """
        return await self.state_machine.get_current_state(self.user_data)

    async def show_cta_for_state(
        self,
        chat_id: int,
        state: Optional[UserState] = None,
        custom_data: Optional[dict] = None
    ) -> None:
        """
        Show appropriate CTA block for current state.

        Automatically determines which buttons to show based on state
        and available actions.

        Args:
            chat_id: User chat ID
            state: Specific state to show CTA for (default: current state)
            custom_data: Optional custom data to include in CTA

        Example:
            # Show CTA for current state
            await view.show_cta_for_state(chat_id=user_id)

            # Show CTA for specific state
            await view.show_cta_for_state(
                chat_id=user_id,
                state=UserState.IDLE
            )
        """
        if state is None:
            state = await self.get_current_state()

        # Get available actions for state
        available_actions = self.state_machine.get_available_actions(state)

        # Build CTA based on state
        if state == UserState.IDLE:
            await self.show_cta_block(
                chat_id=chat_id,
                block_type=CTABlock,
                data=BlockData(
                    header="🌊 Ready to Fish",
                    body="Cast your line and catch crypto fish based on real market moves!",
                    buttons=[("🎣 Start Fishing", "quick_cast")],
                    footer="Each cast costs 1 BAIT token"
                )
            )

        elif state == UserState.FISHING:
            # Fishing state shows info block, not CTA
            # CTA will be shown after hook
            pass

        elif state == UserState.CATCH_COMPLETE:
            await self.show_cta_block(
                chat_id=chat_id,
                block_type=CTABlock,
                data=BlockData(
                    header="🎉 Fish Caught!",
                    body="Great catch! Share it with your group or continue fishing.",
                    buttons=[
                        ("🎣 Cast Again", "quick_cast"),
                        ("📢 Share", "share_hook")
                    ]
                )
            )

        elif state == UserState.NO_BAIT:
            await self.show_cta_block(
                chat_id=chat_id,
                block_type=ErrorBlock,
                data=BlockData(
                    header="🪱 Out of BAIT!",
                    body="You need BAIT tokens to go fishing. Purchase now with Telegram Stars?",
                    buttons=[
                        ("💰 Buy 10 BAIT", "buy_bait_1_1"),
                        ("📊 Check Balance", "show_status")
                    ]
                )
            )

        else:
            logger.warning(f"No default CTA defined for state {state}")

    async def transition_with_animation(
        self,
        chat_id: int,
        to_state: UserState,
        animation_frames: List[BlockData],
        final_cta: Optional[BlockData] = None,
        frame_delay: float = 2.0
    ) -> None:
        """
        Perform animated transition between states.

        Pattern:
        1. Transition to animation state
        2. Play animation frames
        3. Transition to final state
        4. Show CTA for new state (or custom CTA)

        Args:
            chat_id: User chat ID
            to_state: Target state after animation
            animation_frames: List of BlockData for each frame
            final_cta: Optional custom CTA (default: use state's default)
            frame_delay: Delay between frames in seconds

        Example:
            await view.transition_with_animation(
                chat_id=user_id,
                to_state=UserState.FISHING,
                animation_frames=[
                    BlockData(header="🎣 Casting...", body="Swing!"),
                    BlockData(header="🎣 Casting...", body="Splash!"),
                    BlockData(header="🎣 Casting...", body="Bait sinking...")
                ],
                frame_delay=2.5
            )
        """
        if not animation_frames:
            logger.warning("No animation frames provided")
            return

        # Start animation with first frame
        await self.start_animation(chat_id, animation_frames[0])

        # Update through remaining frames
        for frame_data in animation_frames[1:]:
            await asyncio.sleep(frame_delay)
            await self.update_animation(chat_id, frame_data)

        # Transition to final state
        await self.state_machine.transition_to(to_state, self.user_data)

        # Show CTA
        if final_cta:
            await self.transition_animation_to_cta(chat_id, final_cta)
        else:
            await self.show_cta_for_state(chat_id, to_state)


def get_view_controller(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int
) -> ViewController:
    """
    Factory function to get ViewController for current context.

    Args:
        context: Telegram context
        user_id: Telegram user ID

    Returns:
        ViewController instance

    Example:
        view = get_view_controller(context, user_id)
        await view.show_cta_block(...)
    """
    return ViewController(context, user_id)
