"""Bounded daemon jobs; completion callbacks are drained only by the UI thread."""
import queue
import threading


class BackgroundJobs:
    def __init__(self):
        self.pending = queue.Queue(maxsize=8)
        self.completed = queue.Queue()
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True, name="OvaLens-Operations")
        self.thread.start()

    def submit(self, work, success, error):
        if self.closed.is_set():
            raise RuntimeError("Operation worker is closed")
        self.pending.put_nowait((work, success, error))

    def _run(self):
        while not self.closed.is_set():
            try:
                work, success, error = self.pending.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                result = work()
                self.completed.put((success, result))
            except Exception as exc:
                self.completed.put((error, str(exc)))
            finally:
                self.pending.task_done()

    def drain(self):
        for _ in range(16):
            try:
                callback, result = self.completed.get_nowait()
            except queue.Empty:
                break
            callback(result)

    def close(self):
        self.closed.set()
