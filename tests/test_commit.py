import asyncio
import unittest

from Github.github.commit import CommitConflict, CommitEngine, CommitPlan, FileChange


class CommitPlanTests(unittest.TestCase):
    def test_requires_owner_and_repository_name(self):
        for repository in ("", "owner", "/repo", "owner/"):
            with self.subTest(repository=repository):
                with self.assertRaises(ValueError):
                    CommitPlan(repository, "main", "update", [FileChange("README.md", "modified", "ok")]).validate()

    def test_rejects_traversal_and_backslash_paths(self):
        for path in ("../secret", "src/../secret", ".", "folder\\secret"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    CommitPlan("owner/repo", "main", "update", [FileChange(path, "modified", "ok")]).validate()

    def test_rejects_duplicate_normalized_paths(self):
        plan = CommitPlan("owner/repo", "main", "update", [
            FileChange("src/file.py", "modified", "one"),
            FileChange("/src/file.py/", "modified", "two"),
        ])
        with self.assertRaises(ValueError):
            plan.validate()


class CommitEngineTests(unittest.TestCase):
    def test_stale_review_does_not_create_blobs(self):
        class FakeService:
            blobs_created = 0

            async def ref(self, owner, name, ref):
                return {"object": {"sha": "current-head"}}

            async def commit(self, owner, name, sha):
                return {"tree": {"sha": "tree-sha"}}

            async def create_blob(self, *args):
                self.blobs_created += 1
                return {"sha": "blob-sha"}

        service = FakeService()
        plan = CommitPlan("owner/repo", "main", "update", [FileChange("README.md", "modified", "new")])
        with self.assertRaises(CommitConflict):
            asyncio.run(CommitEngine(service).execute(plan, expected_head="old-head"))
        self.assertEqual(service.blobs_created, 0)

    def test_branch_move_during_commit_is_rejected_before_ref_update(self):
        class FakeService:
            def __init__(self):
                self.ref_calls = 0
                self.updated = False

            async def ref(self, owner, name, ref):
                self.ref_calls += 1
                sha = "original-head" if self.ref_calls == 1 else "newer-head"
                return {"object": {"sha": sha}}

            async def commit(self, owner, name, sha):
                return {"tree": {"sha": "base-tree"}}

            async def create_blob(self, owner, name, content, encoding):
                return {"sha": "new-blob"}

            async def create_tree(self, owner, name, entries, base_tree):
                return {"sha": "new-tree"}

            async def create_commit(self, owner, name, message, tree, parents):
                self.asserted_parent = parents[0]
                return {"sha": "new-commit"}

            async def update_branch(self, *args, **kwargs):
                self.updated = True
                return {}

        service = FakeService()
        plan = CommitPlan("owner/repo", "main", "update", [FileChange("README.md", "modified", "new")])
        with self.assertRaises(CommitConflict):
            asyncio.run(CommitEngine(service).execute(plan, expected_head="original-head"))
        self.assertFalse(service.updated)

    def test_ref_update_uses_non_force_mode(self):
        class FakeService:
            async def ref(self, owner, name, ref):
                return {"object": {"sha": "original-head"}}

            async def commit(self, owner, name, sha):
                return {"tree": {"sha": "base-tree"}}

            async def create_blob(self, owner, name, content, encoding):
                return {"sha": "new-blob"}

            async def create_tree(self, owner, name, entries, base_tree):
                return {"sha": "new-tree"}

            async def create_commit(self, owner, name, message, tree, parents):
                return {"sha": "new-commit"}

            async def update_branch(self, owner, name, branch, sha, force):
                self.force = force
                return {"ref": f"refs/heads/{branch}"}

        service = FakeService()
        plan = CommitPlan("owner/repo", "main", "update", [FileChange("README.md", "modified", "new")])
        result = asyncio.run(CommitEngine(service).execute(plan, expected_head="original-head"))
        self.assertFalse(service.force)
        self.assertEqual(result["new_sha"], "new-commit")


if __name__ == "__main__":
    unittest.main()
