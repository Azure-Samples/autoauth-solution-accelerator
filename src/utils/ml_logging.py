import functools
import logging
import os
import time
from threading import Lock
from typing import Callable, Optional

from azure.monitor.opentelemetry import configure_azure_monitor
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Globals
_cloud_logging_configured = False
_logger_cache = {}
_logger_cache_lock = Lock()

# Define a custom logging level
KEYINFO_LEVEL_NUM = 25
logging.addLevelName(KEYINFO_LEVEL_NUM, "KEYINFO")


def keyinfo(self: logging.Logger, message, *args, **kws):
    if self.isEnabledFor(KEYINFO_LEVEL_NUM):
        self._log(KEYINFO_LEVEL_NUM, message, args, **kws)


logging.Logger.keyinfo = keyinfo


class CustomFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record.funcName = getattr(record, "func_name_override", record.funcName)
        record.filename = getattr(record, "file_name_override", record.filename)
        return super().format(record)


def initialize_azure_monitor():
    global _cloud_logging_configured
    if not _cloud_logging_configured:
        configure_azure_monitor(
            connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"),
            logging_exporter_enabled=True,
            tracing_exporter_enabled=True,
            metrics_exporter_enabled=True,
        )
        if not isinstance(trace.get_tracer_provider(), TracerProvider):
            tracer_provider = TracerProvider()
            trace.set_tracer_provider(tracer_provider)
            exporter = AzureMonitorTraceExporter(
                connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
            )
            span_processor = BatchSpanProcessor(exporter)
            tracer_provider.add_span_processor(span_processor)
        _cloud_logging_configured = True


def get_logger(
    name: str = "micro",
    level: Optional[int] = None,
    include_stream_handler: bool = True,
    tracing_enabled: bool = False,
) -> logging.Logger:
    global _logger_cache

    # Thread-safe caching of loggers
    with _logger_cache_lock:
        if name in _logger_cache:
            return _logger_cache[name]

        formatter = CustomFormatter(
            "%(asctime)s - %(name)s - %(processName)-10s - "
            "%(levelname)-8s %(message)s (%(filename)s:%(funcName)s:%(lineno)d)"
        )
        logger = logging.getLogger(name)

        if level is not None or logger.level == 0:
            logger.setLevel(level or logging.INFO)

        if include_stream_handler and not any(
            isinstance(h, logging.StreamHandler) for h in logger.handlers
        ):
            sh = logging.StreamHandler()
            sh.setFormatter(formatter)
            logger.addHandler(sh)

        if tracing_enabled:
            initialize_azure_monitor()

        _logger_cache[name] = logger
        return logger


def log_function_call(
    logger_name: Optional[str] = None,
    log_inputs: bool = False,
    log_output: bool = False,
) -> Callable:
    def decorator_log_function_call(func):
        @functools.wraps(func)
        def wrapper_log_function_call(*args, **kwargs):
            # Access 'self' if available
            if args and hasattr(args[0], "__class__"):
                self = args[0]
                case_id = getattr(self, "caseId", "default_caseId")
            else:
                case_id = "default_caseId"

            # Use caseId in logger name
            current_logger_name = logger_name or f"case_{case_id}"
            logger = get_logger(current_logger_name)

            func_name = func.__name__

            logger.info(f"Function {func_name} called for caseId: {case_id}")

            if log_inputs:
                args_str = ", ".join(map(str, args))
                kwargs_str = ", ".join(f"{k}={v}" for k, v in kwargs.items())
                logger.info(f"Arguments: {args_str}, Keyword arguments: {kwargs_str}")

            start_time = time.time()
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            if log_output:
                logger.info(f"Output for caseId {case_id}: {result}")

            logger.info(
                f"Function {func_name} executed in {duration:.2f} seconds for caseId: {case_id}"
            )
            logger.info(f"Function {func_name} completed for caseId: {case_id}")

            return result

        return wrapper_log_function_call

    return decorator_log_function_call
