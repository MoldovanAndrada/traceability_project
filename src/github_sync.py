import subprocess
import time

def watch_github(interval=15):
    last_hash = None

    while True:
        # get latest remote hash
        remote_hash = subprocess.check_output(
            ["git", "ls-remote", "origin", "HEAD"],
            text=True
        ).split()[0]

        if last_hash is None:
            last_hash = remote_hash
        elif remote_hash != last_hash:
            print("\n🔵 New commit detected on GitHub → pulling changes...")
            subprocess.call(["git", "pull"])
            last_hash = remote_hash

        time.sleep(interval)
