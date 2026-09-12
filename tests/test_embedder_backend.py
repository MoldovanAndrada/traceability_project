import os
import subprocess
import sys
import unittest


class EmbedderBackendTest(unittest.TestCase):
    def test_tensorflow_is_disabled_by_default(self):
        env = os.environ.copy()
        env.pop("USE_TF", None)

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os; import src.embedder; print(os.environ['USE_TF'])",
            ],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(result.stdout.strip(), "0")

    def test_tensorflow_is_disabled_when_inherited_from_the_shell(self):
        env = os.environ.copy()
        env["USE_TF"] = "1"

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os; import src.embedder; print(os.environ['USE_TF'])",
            ],
            cwd=os.path.dirname(os.path.dirname(__file__)),
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )

        self.assertEqual(result.stdout.strip(), "0")


if __name__ == "__main__":
    unittest.main()
