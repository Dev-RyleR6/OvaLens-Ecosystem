"""
InferenceWorker — Dedicated ONNX inference thread.
Decouples the ChamberController FSM from model execution latency
so that frame grabbing and result delivery do not block the
state machine's timing loop.
"""

import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Optional

from .inference import InferenceEngine


@dataclass(frozen=True)
class InferenceRequest:
    frame: object
    request_id: str


class InferenceWorker:
    """
    Consumes frames from frame_queue, runs ONNX inference,
    and publishes results to result_queue.

    Queue sizes are capped at 1 to ensure we always operate
    on the freshest available frame (no stale frame backlog).
    """

    def __init__(self, engine: InferenceEngine):
        self.engine = engine
        self.frame_queue:  queue.Queue = queue.Queue(maxsize=1)
        self.result_queue: queue.Queue = queue.Queue(maxsize=1)
        self._stop = threading.Event()
        self._busy = threading.Event()
        self._preview = queue.Queue(maxsize=1)
        self._captures = queue.Queue(maxsize=1)
        self.metrics = {"inference_ms": 0.0, "queue_depth": 0}
        self._thread: Optional[threading.Thread] = threading.Thread(
            target=self._loop,
            daemon=True,
            name="OvaLens-InferenceWorker",
        )

    def start(self) -> None:
        """Start the inference worker thread."""
        self._stop.clear()
        if not self._thread.is_alive():
            self._thread = threading.Thread(
                target=self._loop, daemon=True, name="OvaLens-InferenceWorker"
            )
            self._thread.start()

    def stop(self) -> None:
        """Signal the worker thread to exit."""
        self._stop.set()
        # Unblock any blocking queue.get()
        try:
            self.frame_queue.put_nowait(None)
        except queue.Full:
            pass
        for pending in (self._preview, self._captures):
            try:
                _, future = pending.get_nowait()
                if not future.done():
                    future.set_exception(RuntimeError("Inference stopped"))
            except queue.Empty:
                pass
        if self._thread.is_alive() and self._thread is not threading.current_thread():
            self._thread.join(timeout=1)

    def predict(self, frame, timeout=2.0, *, capture=False):
        """Synchronous worker-facing API; never call from the Tk thread."""
        if self._stop.is_set():
            raise RuntimeError("Inference stopped")
        if capture:
            self._drop_preview()
        future = Future()
        (self._captures if capture else self._preview).put_nowait((frame, future))
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise

    def _drop_preview(self):
        try:
            _, future = self._preview.get_nowait()
            future.cancel()
        except queue.Empty:
            pass

    @property
    def busy(self) -> bool:
        return self._busy.is_set() or not self.frame_queue.empty() or not self._captures.empty()

    def submit(self, frame, request_id: str) -> None:
        if self._stop.is_set() or self.busy:
            raise RuntimeError("Inference is still busy or stopping")
        self._drop_preview()
        self.frame_queue.put_nowait(InferenceRequest(frame, request_id))

    def _loop(self) -> None:
        while not self._stop.is_set():
            request_id = None
            future = None
            formal = True
            try:
                try:
                    frame = self.frame_queue.get_nowait()
                except queue.Empty:
                    try:
                        frame, future = self._captures.get_nowait()
                    except queue.Empty:
                        formal = False
                        frame, future = self._preview.get(timeout=0.01)
                if frame is None:
                    break  # Poison pill — clean shutdown
                if future and not future.set_running_or_notify_cancel():
                    continue
                if formal:
                    self._busy.set()
                if isinstance(frame, InferenceRequest):
                    request_id, frame = frame.request_id, frame.frame
                started = time.monotonic()
                result = dict(frame() if callable(frame) else self.engine.predict(frame))
                self.metrics = {"inference_ms": (time.monotonic() - started) * 1000,
                                "queue_depth": self.frame_queue.qsize() + self._captures.qsize() + self._preview.qsize()}
                if future:
                    future.set_result(result)
                    continue
                if request_id is not None:
                    result["request_id"] = request_id
                # If result_queue is full, discard old stale result
                try:
                    self.result_queue.put_nowait(result)
                except queue.Full:
                    try:
                        self.result_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self.result_queue.put_nowait(result)
            except queue.Empty:
                continue
            except Exception as e:
                if future:
                    future.set_exception(e)
                    continue
                print(f"[InferenceWorker] Error: {e}")
                error = {"final_class": None, "confidence": 0.0,
                         "routing_action": "MANUAL_REVIEW", "detections": [],
                         "inference_ms": 0, "error_code": "INFERENCE_ERROR"}
                if request_id is not None:
                    error["request_id"] = request_id
                try:
                    self.result_queue.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self.result_queue.put_nowait(error)
                except queue.Full:
                    pass
            finally:
                self._busy.clear()
