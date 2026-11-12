"""Progress reporting for PA processing, independent of any UI framework.

``PAProcessingPipeline.run`` used to call Streamlit directly. It now reports
through a :class:`ProgressReporter`; the Streamlit reporter emits the exact same
messages, and the FastAPI backend or an agent host can pass a callback instead.
"""

from __future__ import annotations

from typing import Any, Callable, Optional, Protocol

ProgressCallback = Callable[[str, str, Optional[float]], Any]


class ProgressReporter(Protocol):
    def step(self, message: str, fraction: float) -> None: ...

    def success(self, message: str) -> None: ...

    def error(self, message: str) -> None: ...


class NullReporter:
    def step(self, message: str, fraction: float) -> None:
        pass

    def success(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


class CallbackReporter:
    """Calls ``callback(kind, message, fraction)`` with kind in step/success/error."""

    def __init__(self, callback: ProgressCallback) -> None:
        self.callback = callback

    def step(self, message: str, fraction: float) -> None:
        self.callback("step", message, fraction)

    def success(self, message: str) -> None:
        self.callback("success", message, 1.0)

    def error(self, message: str) -> None:
        self.callback("error", message, None)


class StreamlitReporter:
    """Streamlit is imported lazily so the pipeline runs without it installed."""

    def __init__(self) -> None:
        import streamlit as st

        self._st = st
        self._bar = None
        self._status = None

    def _ensure(self) -> None:
        if self._bar is None:
            self._bar = self._st.progress(0)
            self._status = self._st.empty()

    def step(self, message: str, fraction: float) -> None:
        self._ensure()
        self._status.write(message)
        self._bar.progress(fraction)

    def success(self, message: str) -> None:
        self._ensure()
        self._status.success(message)
        self._bar.progress(1.0)

    def error(self, message: str) -> None:
        self._st.error(message)


def make_reporter(
    streamlit: bool = False, progress_callback: Optional[ProgressCallback] = None
) -> ProgressReporter:
    if progress_callback is not None:
        return CallbackReporter(progress_callback)
    if streamlit:
        return StreamlitReporter()
    return NullReporter()
