import sys
import threading
import time
from contextlib import contextmanager


class LiveProgress:
    def __init__(self, enabled: bool = True, width: int = 24):
        self.enabled = enabled
        self.width = width
        self._thread = None
        self._stop_event = threading.Event()
        self._last_len = 0
        self._lock = threading.Lock()

    def _render_line(self, text: str):
        with self._lock:
            padded = text.ljust(self._last_len)
            sys.stdout.write("\r" + padded)
            sys.stdout.flush()
            self._last_len = max(self._last_len, len(text))

    def _clear_live_line(self):
        with self._lock:
            if self._last_len:
                sys.stdout.write("\r" + (" " * self._last_len) + "\r")
                sys.stdout.flush()
                self._last_len = 0

    def snapshot(self, current: int, total: int, label: str):
        if not self.enabled or total <= 0:
            return
        current = max(0, min(current, total))
        pct = int((current / total) * 100)
        fill = int((self.width * pct) / 100)
        bar = "#" * fill + "-" * (self.width - fill)
        self._render_line(f"[{bar}] {pct:3d}% {label}")

    def _activity_worker(self, label: str):
        frames = ["|", "/", "-", "\\"]
        tick = 0
        direction = 1
        pct = 0

        while not self._stop_event.is_set():
            pct += direction * 4
            if pct >= 95:
                pct = 95
                direction = -1
            elif pct <= 5:
                pct = 5
                direction = 1

            fill = int((self.width * pct) / 100)
            bar = "#" * fill + "-" * (self.width - fill)
            frame = frames[tick % len(frames)]
            self._render_line(f"{frame} [{bar}] {pct:3d}% {label}")

            tick += 1
            time.sleep(0.12)

    def start_activity(self, label: str):
        if not self.enabled:
            return
        self.stop_activity()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._activity_worker, args=(label,), daemon=True)
        self._thread.start()

    def stop_activity(self):
        if not self.enabled:
            return
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=1.0)
        self._thread = None
        self._clear_live_line()

    def clear(self):
        """Clear any progress display from the terminal."""
        if not self.enabled:
            return
        self.stop_activity()
        self._clear_live_line()

    @contextmanager
    def activity(self, label: str):
        self.start_activity(label)
        try:
            yield
        finally:
            self.stop_activity()
