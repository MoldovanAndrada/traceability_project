import unittest
from unittest.mock import patch

from src import watcher


class _StopWatching(Exception):
    pass


class WatcherDataSourceTest(unittest.TestCase):
    def test_reads_the_configured_csv_file(self):
        with (
            patch.object(watcher.pd, "read_csv", side_effect=_StopWatching) as read_csv,
            self.assertRaises(_StopWatching),
        ):
            watcher.watch_stories()

        read_csv.assert_called_once_with(watcher.USER_STORIES)


if __name__ == "__main__":
    unittest.main()
