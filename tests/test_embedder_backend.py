import os
import subprocess
import sys
import unittest


class EmbedderBackendTest(unittest.TestCase):
    def test_import_disables_optional_tensorflow_backend(self):
        environment = os.environ.copy()
        environment["USE_TF"] = "1"

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os; import src.embedder; print(os.environ['USE_TF'])",
            ],
            check=True,
            capture_output=True,
            env=environment,
            text=True,
        )

        self.assertEqual(result.stdout.strip(), "0")


if __name__ == "__main__":
    unittest.main()
