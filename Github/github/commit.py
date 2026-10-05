from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class FileChange:
    path: str
    status: str
    additions: int = 0
    deletions: int = 0

@dataclass(frozen=True)
class CommitPlan:
    repository: str
    branch: str
    message: str
    changes: Sequence[FileChange]

    @property
    def additions(self) -> int:
        return sum(item.additions for item in self.changes)

    @property
    def deletions(self) -> int:
        return sum(item.deletions for item in self.changes)

    def validate(self) -> None:
        if not self.repository or not self.branch:
            raise ValueError("Repository and branch are required")
        if not self.message.strip():
            raise ValueError("Commit message is required")
        if not self.changes:
            raise ValueError("At least one file change is required")
