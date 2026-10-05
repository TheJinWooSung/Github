from dataclasses import dataclass
from typing import Sequence
from .repositories import RepositoryService

@dataclass(frozen=True)
class FileChange:
    path: str
    status: str
    content: str | None = None
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
        seen = set()
        for change in self.changes:
            path = change.path.strip().strip("/")
            if not path or path in seen:
                raise ValueError("Every changed path must be unique")
            if "\x00" in path:
                raise ValueError("Invalid file path")
            seen.add(path)
            if change.status not in {"added", "modified", "deleted"}:
                raise ValueError("Unsupported file change")
            if change.status != "deleted" and change.content is None:
                raise ValueError("File content is required")

class CommitConflict(RuntimeError):
    pass

class CommitEngine:
    def __init__(self, service: RepositoryService):
        self.service = service

    async def prepare(self, plan: CommitPlan) -> dict:
        plan.validate()
        owner, name = plan.repository.split("/", 1)
        reference = await self.service.ref(owner, name, f"heads/{plan.branch}")
        current_sha = reference["object"]["sha"]
        current_commit = await self.service.commit(owner, name, current_sha)
        return {"owner": owner, "name": name, "branch": plan.branch, "head_sha": current_sha, "tree_sha": current_commit["tree"]["sha"], "plan": plan}

    async def execute(self, plan: CommitPlan, expected_head: str | None = None) -> dict:
        prepared = await self.prepare(plan)
        owner = prepared["owner"]
        name = prepared["name"]
        current_head = prepared["head_sha"]
        if expected_head and expected_head != current_head:
            raise CommitConflict("Branch changed after the review")
        entries = []
        for change in plan.changes:
            path = change.path.strip().strip("/")
            if change.status == "deleted":
                entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
                continue
            blob = await self.service.create_blob(owner, name, change.content or "", "utf-8")
            entries.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = await self.service.create_tree(owner, name, entries, prepared["tree_sha"])
        commit = await self.service.create_commit(owner, name, plan.message.strip(), tree["sha"], [current_head])
        latest = await self.service.ref(owner, name, f"heads/{plan.branch}")
        if latest["object"]["sha"] != current_head:
            raise CommitConflict("Branch changed before commit update")
        updated = await self.service.update_branch(owner, name, plan.branch, commit["sha"], False)
        return {"commit": commit, "reference": updated, "head_sha": current_head, "new_sha": commit["sha"], "tree_sha": tree["sha"], "changes": len(plan.changes)}
