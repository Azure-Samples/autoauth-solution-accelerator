"""
This is a configuration file for pytest containing customizations and fixtures.

In VSCode, Code Coverage is recorded in config.xml. Delete this file to reset reporting.
"""

from __future__ import annotations

import pytest
import os
from _pytest.nodes import Item


def pytest_collection_modifyitems(items: list[Item]):
    """
    Auto-mark tests based on node ID:
      - If "spark" is in the test path, mark as 'spark'
      - If "_int_" is in the test path, mark as 'e2e'
    """
    for item in items:
        if "spark" in item.nodeid:
            item.add_marker(pytest.mark.spark)
        elif "_int_" in item.nodeid:
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def set_o1_env_vars(monkeypatch):
    monkeypatch.setenv(
        "AZURE_OPENAI_CHAT_DEPLOYMENT_01",
        os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_01", "o1-preview")
    )

@pytest.fixture(scope="function")
def evaluation_setup(monkeypatch):
    required_envs = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_AI_FOUNDRY_CONNECTION_STRING",
        "AZURE_OPENAI_CHAT_DEPLOYMENT_ID"
    ]

    missing_envs = []
    for env_var in required_envs:
        value = os.environ.get(env_var, "")
        if not value:
            missing_envs.append(env_var)

    if missing_envs:
        missing_list = ", ".join(missing_envs)
        raise EnvironmentError(
            f"The following environment variables are not set or are empty: {missing_list}"
        )

    print("[evaluation_setup] Environment variables validated.")
    yield
    print("[evaluation_setup] Evaluation tests completed.")