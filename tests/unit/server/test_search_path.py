"""AIRMAN_MCP_SEARCH_PATH: a search_path applied to every pooled connection."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pg_airman_mcp.server import ServerSettings
from pg_airman_mcp.sql import DbConnPool


def test_search_path_default_none():
    with patch.dict(os.environ, {}, clear=True):
        assert ServerSettings().search_path is None


def test_search_path_from_env():
    with patch.dict(os.environ, {"AIRMAN_MCP_SEARCH_PATH": "sales, public"}):
        assert ServerSettings().search_path == "sales, public"


def test_search_path_blank_is_none():
    with patch.dict(os.environ, {"AIRMAN_MCP_SEARCH_PATH": "  "}):
        assert ServerSettings().search_path is None


@pytest.mark.asyncio
async def test_pool_sets_search_path_on_new_connections():
    pool_instance = MagicMock()
    pool_instance.open = AsyncMock()
    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.__aenter__ = AsyncMock(return_value=cursor)
    cursor.__aexit__ = AsyncMock(return_value=None)
    conn = MagicMock()
    conn.cursor = MagicMock(return_value=cursor)
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    pool_instance.connection = MagicMock(return_value=conn)

    with patch(
        "pg_airman_mcp.sql.sql_driver.AsyncConnectionPool",
        return_value=pool_instance,
    ) as pool_cls:
        db = DbConnPool(search_path="sales, public")
        await db.pool_connect("postgresql://u@localhost/db")

    configure = pool_cls.call_args.kwargs["configure"]
    new_conn = MagicMock()
    new_conn.execute = AsyncMock()
    new_conn.commit = AsyncMock()
    await configure(new_conn)
    new_conn.execute.assert_awaited_once_with(
        "SELECT set_config('search_path', %s, false)", ["sales, public"]
    )
    new_conn.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_pool_without_search_path_has_no_configure():
    pool_instance = MagicMock()
    pool_instance.open = AsyncMock()
    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.__aenter__ = AsyncMock(return_value=cursor)
    cursor.__aexit__ = AsyncMock(return_value=None)
    conn = MagicMock()
    conn.cursor = MagicMock(return_value=cursor)
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=None)
    pool_instance.connection = MagicMock(return_value=conn)

    with patch(
        "pg_airman_mcp.sql.sql_driver.AsyncConnectionPool",
        return_value=pool_instance,
    ) as pool_cls:
        await DbConnPool().pool_connect("postgresql://u@localhost/db")

    assert pool_cls.call_args.kwargs.get("configure") is None
