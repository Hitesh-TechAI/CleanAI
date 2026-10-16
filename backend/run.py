import argparse
import multiprocessing
import os
import threading
import time

import psutil
import uvicorn

from api.main import app


def _watch_parent(pid: int):
    """If Electron dies without cleanup, don't leave an orphaned backend."""
    while True:
        time.sleep(2)
        if not psutil.pid_exists(pid):
            os._exit(0)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--parent-pid", type=int, default=0)
    a = ap.parse_args()
    if a.parent_pid:
        threading.Thread(target=_watch_parent, args=(a.parent_pid,), daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=a.port, log_config=None)