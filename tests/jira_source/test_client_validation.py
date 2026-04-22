"""Regression tests for JIRA client creation when config is incomplete.

Before v0.10.1 these paths silently fell through to the `jira` library's
default `localhost:2990` and retried 3 times before bubbling up a
ConnectionError — a confusing user experience especially for people who
don't use JIRA at all. Now both clients validate config.url and
config.token up front with a clear error pointing at config.yaml.
"""

import pytest

from saymo.config import JiraConfig


def test_tasks_client_raises_on_empty_url():
    from saymo.jira_source.tasks import _create_jira_client
    with pytest.raises(RuntimeError, match="JIRA URL is not configured"):
        _create_jira_client(JiraConfig())


def test_tasks_client_raises_on_empty_token():
    from saymo.jira_source.tasks import _create_jira_client
    with pytest.raises(RuntimeError, match="JIRA token is not configured"):
        _create_jira_client(JiraConfig(url="https://jira.example.com"))


def test_confluence_client_raises_on_empty_url():
    from saymo.jira_source.confluence_tasks import _jira_client
    with pytest.raises(RuntimeError, match="JIRA URL is not configured"):
        _jira_client(JiraConfig())


def test_confluence_client_raises_on_empty_token():
    from saymo.jira_source.confluence_tasks import _jira_client
    with pytest.raises(RuntimeError, match="JIRA token is not configured"):
        _jira_client(JiraConfig(url="https://jira.example.com"))


def test_error_mentions_speech_source_workaround():
    """The message should guide users who don't need JIRA at all."""
    from saymo.jira_source.tasks import _create_jira_client
    with pytest.raises(RuntimeError) as exc_info:
        _create_jira_client(JiraConfig())
    msg = str(exc_info.value)
    assert "speech.source" in msg
    assert "obsidian" in msg.lower() or "confluence" in msg.lower() or "jira" in msg.lower()
