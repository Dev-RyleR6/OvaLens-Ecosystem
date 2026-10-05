"""
InferenceWorker — Dedicated ONNX inference thread.
Decouples the ChamberController FSM from model execution latency
so that frame grabbing and result delivery do not block the
state machine's timing loop.
"""

import queue
import threading
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

    @property
    def busy(self) -> bool:
        return self._busy.is_set() or not self.frame_queue.empty()

    def submit(self, frame, request_id: str) -> None:
        if self._stop.is_set() or self.busy:
            raise RuntimeError("Inference is still busy or stopping")
        self.frame_queue.put_nowait(InferenceRequest(frame, request_id))

    def _loop(self) -> None:
        while not self._stop.is_set():
            request_id = None
            try:
                frame = self.frame_queue.get(timeout=0.1)
                if frame is None:
                    break  # Poison pill — clean shutdown
                self._busy.set()
                if isinstance(frame, InferenceRequest):
                    request_id, frame = frame.request_id, frame.frame
                result = dict(self.engine.predict(frame))
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
