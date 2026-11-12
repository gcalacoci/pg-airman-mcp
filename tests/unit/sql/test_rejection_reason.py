"""Restricted-mode rejections must tell the agent why (issue #2).

The validator used to raise "Error validating query: <query>" and keep the
reason only in __cause__, so the agent could not tell a blocked option from a
broken query and kept retrying.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

import pg_airman_mcp.server as server
from pg_airman_mcp.artifacts import ErrorResult
from pg_airman_mcp.explain.explain_plan import ExplainPlanTool
from pg_airman_mcp.sql import SafeSqlDriver, SqlDriver


def _safe_driver() -> SafeSqlDriver:
    driver = Mock(spec=SqlDriver)
    driver.execute_query = AsyncMock(return_value=[])
    return SafeSqlDriver(driver)


@pytest.mark.asyncio
async def test_validation_error_carries_the_reason():
    with pytest.raises(ValueError, match="Function pg_read_file is not allowed"):
        await _safe_driver().execute_query("SELECT pg_read_file('/etc/passwd')")


@pytest.mark.asyncio
async def test_validation_error_keeps_prefix_and_query():
    with pytest.raises(ValueError) as exc:
        await _safe_driver().execute_query("DELETE FROM users")
    assert str(exc.value).startswith("Error validating query")
    assert "DELETE FROM users" in str(exc.value)


@pytest.mark.asyncio
async def test_explain_analyze_reason_reaches_the_tool_result():
    result = await ExplainPlanTool(sql_driver=_safe_driver()).explain_analyze(
        "SELECT 1"
    )
    assert isinstance(result, ErrorResult)
    assert "EXPLAIN ANALYZE is not available in restricted mode" in result.to_text()


@pytest.mark.asyncio
async def test_explain_query_tool_reports_restricted_analyze():
    with patch.object(server, "get_sql_driver", AsyncMock(return_value=_safe_driver())):
        response = await server.explain_query(
            "SELECT 1", analyze=True, hypothetical_indexes=[]
        )
    text = response[0].text  # type: ignore[union-attr]
    assert "EXPLAIN ANALYZE is not available in restricted mode" in text


def test_analyze_parameter_says_unrestricted_only():
    import inspect

    field = inspect.signature(server.explain_query).parameters["analyze"].default
    assert "restricted mode" in (field.description or "")


@pytest.mark.asyncio
async def test_parse_error_carries_the_reason():
    with pytest.raises(ValueError, match='Failed to parse SQL statement: .*"SELEC"'):
        await _safe_driver().execute_query("SELEC 1")
