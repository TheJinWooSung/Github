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


if __name__ == "__main__":
    unittest.main()
