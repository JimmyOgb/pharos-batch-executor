"""Manifest schema and validation for batch execution actions."""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from batch.config import MIN_BATCH_ACTIONS

HEX_ADDRESS_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")
HEX_DATA_REGEX = re.compile(r"^0x[a-fA-F0-9]*$")


class ManifestValidationError(ValueError):
    """Raised when a batch manifest violates requirements."""
    pass


@dataclass
class ActionItem:
    """Represents a single independent action within a batch."""
    target: str
    call_data: str = "0x"
    allow_failure: bool = True
    action_type: str = "call"  # "call", "read", "transfer", "approval"
    description: str = ""
    value: int = 0  # in wei
    expected_result_type: Optional[str] = None  # e.g., "uint256", "address", "bool"

    def __post_init__(self):
        # Validate target address
        if not HEX_ADDRESS_REGEX.match(self.target):
            raise ManifestValidationError(
                f"Invalid target EVM address: '{self.target}'. Must be 0x followed by 40 hex characters."
            )
        # Normalize target address
        self.target = self.target.lower()

        # Validate call data
        if not HEX_DATA_REGEX.match(self.call_data):
            raise ManifestValidationError(
                f"Invalid call data hex string: '{self.call_data}'. Must start with 0x and contain only hex digits."
            )
        # Ensure even number of hex characters
        if len(self.call_data) % 2 != 0:
            raise ManifestValidationError(
                f"Call data hex string length must be even. Got {len(self.call_data)} characters."
            )
        if self.value < 0:
            raise ManifestValidationError(
                f"Action value cannot be negative. Got {self.value}."
            )


@dataclass
class BatchManifest:
    """Represents a validated batch containing at least MIN_BATCH_ACTIONS items."""
    actions: List[ActionItem] = field(default_factory=list)
    title: str = "Batch Execution"
    require_success: bool = False  # Default to False for safe partial-failure execution

    def __post_init__(self):
        self.validate()

    def validate(self) -> None:
        """Validate that the manifest meets official Arena acceptance criteria."""
        if not isinstance(self.actions, list):
            raise ManifestValidationError("Actions must be provided as a list.")

        count = len(self.actions)
        if count < MIN_BATCH_ACTIONS:
            raise ManifestValidationError(
                f"Official requirement 01 mandates a list of at least {MIN_BATCH_ACTIONS} independent actions. "
                f"Only {count} action(s) provided."
            )

        for idx, action in enumerate(self.actions):
            if not isinstance(action, ActionItem):
                raise ManifestValidationError(
                    f"Action at index {idx} must be an instance of ActionItem, got {type(action).__name__}."
                )

    def add_action(self, action: ActionItem) -> None:
        """Add an action and re-validate."""
        self.actions.append(action)
        self.validate()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchManifest":
        """Construct and validate a BatchManifest from a dictionary (e.g., parsed JSON)."""
        actions_raw = data.get("actions", [])
        if not isinstance(actions_raw, list):
            raise ManifestValidationError("'actions' field in manifest must be a list.")

        actions = []
        for idx, item in enumerate(actions_raw):
            if not isinstance(item, dict):
                raise ManifestValidationError(f"Action at index {idx} must be a dictionary.")
            target = item.get("target")
            if not target:
                raise ManifestValidationError(f"Action at index {idx} missing required 'target' field.")

            actions.append(ActionItem(
                target=target,
                call_data=item.get("call_data", "0x"),
                allow_failure=item.get("allow_failure", True),
                action_type=item.get("action_type", "call"),
                description=item.get("description", f"Action #{idx + 1}"),
                value=int(item.get("value", 0)),
                expected_result_type=item.get("expected_result_type")
            ))

        return cls(
            actions=actions,
            title=data.get("title", "Batch Execution"),
            require_success=bool(data.get("require_success", False))
        )
