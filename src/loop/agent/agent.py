from abc import ABC, abstractmethod
from typing import Literal, override

from pydantic import BaseModel, Field, NonNegativeInt, model_validator
from typing_extensions import Self


class Snippet(BaseModel):
    file_name: str
    line_start: NonNegativeInt
    line_end: NonNegativeInt

    @override
    def __str__(self) -> str:
        return f"{self.file_name}: {self.line_start}-{self.line_end}"


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
    memory_bug: bool = Field(
        description="Whether the round has a memory bug that is potentially exploitable by attackers."
    )

    @override
    def __str__(self) -> str:
        out: list[str] = []
        r = self.round
        if isinstance(r, Crash):
            out.append(f"Round type: CRASH ({r.type}) at {r.site} due to {r.cause}")
        else:
            out.append(f"Round type: STALE at {r.blocker} due to {r.cause}")

        out.append("Constraints:")
        for i, c in enumerate(self.constraints):
            out.append(f"{i}. {c.action} {c.type} at {c.site}")
            out.append(f"  summary: {c.summary}")
            out.append(f"  reason: {c.reason}")
            if c.forfeit is not None:
                out.append(f"  forfeit: {c.forfeit}")

        out.append("Seeds:")
        for i, s in enumerate(self.seeds):
            out.append(f"{i}. {s.action} {s.file_name}")
            out.append(f"  reason: {s.reason}")

        return "\n".join(out)


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
    async def analyze_instance(self, iteration: int) -> Analysis:
        pass

    @abstractmethod
    async def fix_analysis(self, verification: Verification) -> Analysis:
        pass


class VerificationAgent(ABC):
    @abstractmethod
    async def _run_agent(self, prompt: str) -> Verification:
        pass

    @abstractmethod
    async def verify_changes(self, analysis: Analysis) -> Verification:
        pass
