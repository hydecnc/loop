from abc import ABC, abstractmethod
from typing import Literal

from pydantic import BaseModel, Field, NonNegativeInt, model_validator
from typing_extensions import Self


class Snippet(BaseModel):
    file_name: str
    line_start: NonNegativeInt
    line_end: NonNegativeInt


class Crash(BaseModel):
    type: str = Field(
        description="Type of the crash (e.g. Xid errors, KASAN OOB, etc.)."
    )
    site: Snippet = Field(description="Location of the crash.")
    cause: str = Field(description="Why the crash happened.")


class Stale(BaseModel):
    cause: str = Field(description="Why the crash happened.")
    blocker: Snippet = Field(
        description="Location where the execution path blocks/halts."
    )


class Constraint(BaseModel):
    type: Literal["static", "dynamic", "both"]
    action: Literal["add", "modify", "delete"]
    site: Snippet = Field(description="Location of the constraint.")
    summary: str = Field(description="Concise description of the constraint itself.")
    reason: str = Field(description="Reason why the constraint was changed.")
    forfeit: str | None = Field(
        None,
        description="Execution paths the constraint closes off. Must be null when action is 'delete'.",
    )


class Seed(BaseModel):
    action: Literal["add", "modify", "delete"]
    file_name: str = Field(description="File name of the changed seed.")
    reason: str = Field(description="Reason why the seed was changed.")


class Analysis(BaseModel):
    """Analysis result of a fuzzer round. When no change is made, keep constraints and seeds empty."""

    round: Crash | Stale = Field(description="Classification of the round.")
    constraints: list[Constraint]
    seeds: list[Seed]


class Verification(BaseModel):
    verified: bool
    reason: str | None = Field(
        None, description="Detailed reason why the changes are invalid."
    )

    @model_validator(mode="after")
    def require_reason_if_not_verified(self) -> Self:
        if not self.verified and self.reason is None:
            raise ValueError("reason is required when verified is false")
        return self


class AnalysisAgent(ABC):
    @abstractmethod
    async def _analysis(self, prompt: str) -> Analysis:
        pass

    @abstractmethod
    def analyze_instance(self, iteration: int) -> Analysis:
        pass

    @abstractmethod
    def fix_analysis(self, verification: Verification) -> Analysis:
        pass


class VerificationAgent(ABC):
    @abstractmethod
    async def _run_agent(self, prompt: str) -> Verification:
        pass

    @abstractmethod
    def verify_changes(self, analysis: Analysis) -> Verification:
        pass
