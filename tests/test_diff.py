import unittest

from Github.github.diff import unified_diff


class UnifiedDiffTests(unittest.TestCase):
    def test_shows_file_headers_and_changed_lines(self):
        patch = unified_diff("first\nold line\nlast", "first\nnew line\nlast", "src/example.py")
        self.assertIn("--- a/src/example.py", patch)
        self.assertIn("+++ b/src/example.py", patch)
        self.assertIn("-old line", patch)
        self.assertIn("+new line", patch)

    def test_identical_content_has_no_diff(self):
        self.assertEqual(unified_diff("same\ncontent", "same\ncontent", "README.md"), "")

    def test_addition_and_deletion_are_visible(self):
        patch = unified_diff("keep\nremove", "keep\nadd", "file.txt", context=0)
        self.assertIn("-remove", patch)
        self.assertIn("+add", patch)


if __name__ == "__main__":
    unittest.main()
