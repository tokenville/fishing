"""
State Machine - User state management and transitions.

This module implements a finite state machine for managing user states
in the fishing game, similar to state management in Vue.js (Vuex/Pinia).

Architecture:
- UserState: Enum of all possible states
- StateData: Data associated with current state
- StateMachine: Manages transitions and validates actions

Design Principles:
1. All user states are explicit and defined
2. State transitions are validated before execution
3. State is derived from both DB (persistent) and context (ephemeral)
4. Each state defines available actions for UI
"""

from enum import Enum
from typing import Optional, Dict, Any, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class UserState(Enum):
    """
    All possible user states in the fishing game.

    State categories:
    - Onboarding: Tutorial flow for new users
    - Main game: Core fishing gameplay loop
    - Special: Edge cases and auxiliary flows
    """

    # Onboarding states (tutorial flow)
    ONBOARDING_INTRO = "onboarding_intro"              # Initial welcome screen
    ONBOARDING_JOIN_GROUP = "onboarding_join_group"    # Waiting for group join
    ONBOARDING_CAST = "onboarding_cast"                # First cast instruction
    ONBOARDING_HOOK = "onboarding_hook"                # First hook instruction

    # Main game states (core loop)
    IDLE = "idle"                                      # Ready to fish, no active position
    CASTING = "casting"                                # Cast animation playing
    FISHING = "fishing"                                # Active position, waiting for hook
    HOOKING = "hooking"                                # Hook animation playing
    CATCH_COMPLETE = "catch_complete"                  # Fish caught, showing result

    # Special states
    NO_BAIT = "no_bait"                                # Out of BAITs
    POND_SELECTION = "pond_selection"                  # Choosing fishing pond
    BUYING = "buying"                                  # In purchase flow

    def __str__(self):
        return self.value


@dataclass
class StateData:
    """
    Data associated with current state (like Vue reactive data).

    Attributes:
        state: Current UserState
        position_id: Active fishing position ID (for FISHING state)
        animation_message_id: Message being animated
        cta_message_id: Active CTA block message ID
        pending_data: Temporary data for state (share data, rewards, etc.)
    """
    state: UserState
    position_id: Optional[int] = None
    animation_message_id: Optional[int] = None
    cta_message_id: Optional[int] = None
    pending_data: Optional[Dict[str, Any]] = None


class StateMachine:
    """
    User State Machine.

    Manages state transitions and validates allowed actions.
    Works with both persistent DB state and ephemeral context state.

    State Priority (for determining current state):
    1. Ephemeral context flags (animations, selections)
    2. DB persistent state (positions, onboarding)
    3. Default to IDLE
    """

    # Define valid state transitions (directed graph)
    TRANSITIONS: Dict[UserState, Set[UserState]] = {
        # Onboarding flow
        UserState.ONBOARDING_INTRO: {
            UserState.ONBOARDING_JOIN_GROUP,
            UserState.IDLE  # Skip onboarding
        },
        UserState.ONBOARDING_JOIN_GROUP: {
            UserState.ONBOARDING_CAST,
            UserState.IDLE  # Skip
        },
        UserState.ONBOARDING_CAST: {
            UserState.CASTING,
            UserState.POND_SELECTION
        },
        UserState.ONBOARDING_HOOK: {
            UserState.HOOKING
        },

        # Main game flow (core loop)
        UserState.IDLE: {
            UserState.POND_SELECTION,
            UserState.NO_BAIT,
            UserState.BUYING,
            UserState.CASTING  # Direct cast if only one pond
        },
        UserState.POND_SELECTION: {
            UserState.CASTING,
            UserState.IDLE  # Cancel selection
        },
        UserState.CASTING: {
            UserState.FISHING  # Animation completes
        },
        UserState.FISHING: {
            UserState.HOOKING,
            UserState.FISHING  # Can check status while fishing
        },
        UserState.HOOKING: {
            UserState.CATCH_COMPLETE
        },
        UserState.CATCH_COMPLETE: {
            UserState.IDLE,           # Done with catch
            UserState.POND_SELECTION  # Cast again (different pond)
        },

        # Special state transitions
        UserState.NO_BAIT: {
            UserState.BUYING,
            UserState.IDLE  # Got BAIT somehow (reward, purchase)
        },
        UserState.BUYING: {
            UserState.IDLE,     # Purchase complete
            UserState.NO_BAIT   # Purchase failed/cancelled
        }
    }

    def __init__(self, user_id: int):
        """
        Initialize state machine for a user.

        Args:
            user_id: Telegram user ID
        """
        self.user_id = user_id
        self._state_data: Optional[StateData] = None

    async def get_current_state(self, context_data: Dict[str, Any]) -> UserState:
        """
        Determine current user state from DB and context.

        Priority:
        1. Ephemeral context state (animations, selections) - highest priority
        2. DB persistent state (positions, onboarding)
        3. Default to IDLE

        Args:
            context_data: context.user_data dictionary

        Returns:
            Current UserState
        """
        from src.database.db_manager import (
            get_active_position,
            is_onboarding_completed,
            get_onboarding_progress,
            get_user
        )

        # Check ephemeral states first (highest priority)
        # These are temporary UI states stored in context
        if context_data.get('is_casting'):
            return UserState.CASTING

        if context_data.get('is_hooking'):
            return UserState.HOOKING

        if context_data.get('is_pond_selection'):
            return UserState.POND_SELECTION

        if context_data.get('is_buying'):
            return UserState.BUYING

        if context_data.get('is_catch_complete'):
            return UserState.CATCH_COMPLETE

        # Check DB persistent states
        onboarding_complete = await is_onboarding_completed(self.user_id)

        if not onboarding_complete:
            progress = await get_onboarding_progress(self.user_id)
            if progress:
                step = progress.get('current_step', 'intro')
                if step == 'intro':
                    return UserState.ONBOARDING_INTRO
                elif step == 'join_group':
                    return UserState.ONBOARDING_JOIN_GROUP
                elif step == 'cast_instruction':
                    return UserState.ONBOARDING_CAST
                elif step == 'hook_instruction':
                    return UserState.ONBOARDING_HOOK

        # Check active fishing position
        active_position = await get_active_position(self.user_id)
        if active_position:
            return UserState.FISHING

        # Check BAITs
        user = await get_user(self.user_id)
        if user and user['bait_tokens'] <= 0:
            return UserState.NO_BAIT

        # Default state - ready to fish
        return UserState.IDLE

    def can_transition(self, from_state: UserState, to_state: UserState) -> bool:
        """
        Check if transition is valid according to state machine graph.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            True if transition is allowed
        """
        allowed = self.TRANSITIONS.get(from_state, set())
        return to_state in allowed

    async def transition_to(
        self,
        new_state: UserState,
        context_data: Dict[str, Any],
        force: bool = False
    ) -> bool:
        """
        Attempt to transition to new state.

        Args:
            new_state: Target state
            context_data: Context user_data dict (will be modified)
            force: Skip validation (for error recovery)

        Returns:
            True if transition succeeded

        Side effects:
            - Updates context_data flags for ephemeral states
            - Logs transition
        """
        current_state = await self.get_current_state(context_data)

        # Validate transition unless forced
        if not force and not self.can_transition(current_state, new_state):
            logger.warning(
                f"Invalid state transition for user {self.user_id}: "
                f"{current_state} -> {new_state}"
            )
            return False

        # Update context flags based on new state
        self._update_context_for_state(new_state, context_data)

        logger.info(
            f"User {self.user_id} state transition: {current_state} -> {new_state}"
        )

        return True

    def _update_context_for_state(
        self,
        state: UserState,
        context_data: Dict[str, Any]
    ) -> None:
        """
        Update context flags for ephemeral states.

        Clears all ephemeral flags and sets the appropriate one
        for the new state.

        Args:
            state: New state
            context_data: Context user_data dict (modified in place)
        """
        # Clear all ephemeral flags
        context_data.pop('is_casting', None)
        context_data.pop('is_hooking', None)
        context_data.pop('is_pond_selection', None)
        context_data.pop('is_buying', None)
        context_data.pop('is_catch_complete', None)

        # Set flag for new ephemeral state
        if state == UserState.CASTING:
            context_data['is_casting'] = True
        elif state == UserState.HOOKING:
            context_data['is_hooking'] = True
        elif state == UserState.POND_SELECTION:
            context_data['is_pond_selection'] = True
        elif state == UserState.BUYING:
            context_data['is_buying'] = True
        elif state == UserState.CATCH_COMPLETE:
            context_data['is_catch_complete'] = True

    def get_available_actions(self, current_state: UserState) -> Set[str]:
        """
        Get list of available actions for current state.

        Used to determine which buttons/commands to show in UI.

        Args:
            current_state: Current UserState

        Returns:
            Set of action names available in this state

        Example:
            actions = sm.get_available_actions(UserState.IDLE)
            # Returns: {'cast', 'status', 'help', 'buy'}
        """
        actions_map: Dict[UserState, Set[str]] = {
            # Main game states
            UserState.IDLE: {'cast', 'status', 'help', 'buy', 'leaderboard'},
            UserState.FISHING: {'hook', 'status'},
            UserState.CATCH_COMPLETE: {'cast', 'share', 'status'},
            UserState.POND_SELECTION: {'select_pond', 'cancel'},

            # Special states
            UserState.NO_BAIT: {'buy', 'help', 'status'},
            UserState.BUYING: {'cancel'},

            # Onboarding states
            UserState.ONBOARDING_INTRO: {'start_tutorial', 'skip'},
            UserState.ONBOARDING_JOIN_GROUP: {'join', 'skip'},
            UserState.ONBOARDING_CAST: {'cast'},
            UserState.ONBOARDING_HOOK: {'hook'},

            # Animation states (no user actions)
            UserState.CASTING: set(),
            UserState.HOOKING: set(),
        }

        return actions_map.get(current_state, set())

    def get_state_description(self, state: UserState) -> str:
        """
        Get human-readable description of state.

        Args:
            state: UserState to describe

        Returns:
            Description string

        Example:
            desc = sm.get_state_description(UserState.FISHING)
            # Returns: "Fishing position active"
        """
        descriptions = {
            UserState.IDLE: "Ready to fish",
            UserState.FISHING: "Fishing position active",
            UserState.CASTING: "Casting animation",
            UserState.HOOKING: "Hooking animation",
            UserState.CATCH_COMPLETE: "Fish caught",
            UserState.NO_BAIT: "Out of BAITs",
            UserState.POND_SELECTION: "Selecting fishing pond",
            UserState.BUYING: "Purchase in progress",
            UserState.ONBOARDING_INTRO: "Tutorial: Introduction",
            UserState.ONBOARDING_JOIN_GROUP: "Tutorial: Join group",
            UserState.ONBOARDING_CAST: "Tutorial: First cast",
            UserState.ONBOARDING_HOOK: "Tutorial: First hook",
        }

        return descriptions.get(state, f"Unknown state: {state}")


def get_state_machine(user_id: int) -> StateMachine:
    """
    Factory function to create StateMachine for user.

    Args:
        user_id: Telegram user ID

    Returns:
        StateMachine instance

    Example:
        sm = get_state_machine(user_id)
        current_state = await sm.get_current_state(context.user_data)
    """
    return StateMachine(user_id)
