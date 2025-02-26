import os
import time
from urllib.parse import urlparse
import logging
from typing import Optional, List, Tuple

# @TODO: Remove this import when the package fix is available.
from azure.ai.evaluation._evaluate._eval_run import RunInfo, RunStatus
LOGGER = logging.getLogger(__name__)
CUSTOM_TAGS: List[Tuple[str, str]] = []

def custom_start_run(self):
    """
    Custom _start_run implementation that updates the 'tags' field.
    Instead of accepting tags as a method parameter, this version retrieves additional
    tag information from:
      - An environment variable "MY_CUSTOM_TAGS", expected as a semicolon-separated list of key=value pairs, and/or
      - A global variable `CUSTOM_TAGS`, which should be a list of (key, value) tuples.
    These additional tags are appended to the default tag.
    """
    # Check state and log before starting the run.
    self._check_state_and_log("start run", {v for v in RunStatus if v != RunStatus.NOT_STARTED}, True)
    self._status = RunStatus.STARTED

    if self._tracking_uri is None:
        LOGGER.warning("A tracking_uri was not provided. Results will be saved locally but not logged to Azure.")
        self._url_base = None
        self._status = RunStatus.BROKEN
        self._info = RunInfo.generate(self._run_name)
    else:
        self._url_base = urlparse(self._tracking_uri).netloc
        if self._promptflow_run is not None:
            self._info = RunInfo(
                self._promptflow_run.name,
                self._promptflow_run._experiment_name or "",
                self._promptflow_run.name,
            )
        else:
            url = f"https://{self._url_base}/mlflow/v2.0{self._get_scope()}/api/2.0/mlflow/runs/create"
            # Build the default tag using an environment variable.
            default_tags = [{"key": "mlflow.user", "value": "azure-ai-evaluation"}]

            # Retrieve additional tags from the global variable CUSTOM_TAGS.
            additional_tags: List[dict] = []
            if CUSTOM_TAGS:
                additional_tags.extend([{"key": k, "value": v} for k, v in CUSTOM_TAGS])

            all_tags = default_tags + additional_tags

            body = {
                "experiment_id": "0",
                "user_id": "azure-ai-evaluation",
                "start_time": int(time.time() * 1000),
                "tags": all_tags,
            }
            if self._run_name:
                body["run_name"] = self._run_name
            response = self.request_with_retry(url=url, method="POST", json_dict=body)
            if response.status_code != 200:
                self._info = RunInfo.generate(self._run_name)
                LOGGER.warning(
                    "The run failed to start: %s: %s. Results will be saved locally but not logged to Azure.",
                    response.status_code,
                    response.text(),
                )
                self._status = RunStatus.BROKEN
            else:
                parsed_response = response.json()
                self._info = RunInfo(
                    run_id=parsed_response["run"]["info"]["run_id"],
                    experiment_id=parsed_response["run"]["info"]["experiment_id"],
                    run_name=parsed_response["run"]["info"]["run_name"],
                )
                self._status = RunStatus.STARTED
