import threading
from src.watcher import watch_stories
from src.code_watcher import watch_code


if __name__ == "__main__":
    t1 = threading.Thread(target=watch_stories)
    t2 = threading.Thread(target=watch_code)

    t1.start()
    t2.start()

    t1.join()
    t2.join()


