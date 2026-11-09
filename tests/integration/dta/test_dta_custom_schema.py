"""Index tuning and search_path for tables outside the public schema.

Regression tests for gcalacoci/pg-airman-mcp#1 (EnterpriseDB/pg-airman-mcp#23).
"""

import pytest
import pytest_asyncio

from pg_airman_mcp.index.dta_calc import DatabaseTuningAdvisor
from pg_airman_mcp.sql import DbConnPool, SqlDriver

SCHEMA = "airman_custom"


@pytest_asyncio.fixture
async def driver(test_postgres_connection_string):
    connection_string, _version = test_postgres_connection_string
    drv = SqlDriver(engine_url=connection_string)
    try:
        await drv.execute_query(
            "CREATE EXTENSION IF NOT EXISTS hypopg", force_readonly=False
        )
    except Exception:
        pytest.skip("hypopg extension is not available")

    await drv.execute_query(
        f"""
        DROP SCHEMA IF EXISTS {SCHEMA} CASCADE;
        CREATE SCHEMA {SCHEMA};
        CREATE TABLE {SCHEMA}.orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            status VARCHAR(20),
            amount NUMERIC(10, 2)
        );
        INSERT INTO {SCHEMA}.orders
        SELECT i, i % 5000,
               CASE WHEN i % 10 < 7 THEN 'completed' ELSE 'pending' END,
               (i % 1000)::numeric
        FROM generate_series(1, 100000) i;
        ANALYZE {SCHEMA}.orders;
        """,
        force_readonly=False,
    )
    await drv.execute_query("SELECT hypopg_reset()", force_readonly=False)
    yield drv, connection_string
    await drv.execute_query(
        f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE", force_readonly=False
    )
    if isinstance(drv.conn, DbConnPool):
        await drv.conn.close()


@pytest.mark.asyncio
async def test_dta_recommends_index_on_schema_qualified_table(driver):
    drv, _ = driver
    dta = DatabaseTuningAdvisor(
        sql_driver=drv, budget_mb=100, max_runtime_seconds=60, max_index_width=2
    )
    result = await dta.analyze_workload(
        query_list=[f"SELECT * FROM {SCHEMA}.orders WHERE customer_id = 42"],
        min_calls=1,
        min_avg_time_ms=0,
    )
    assert result.error is None, result.error
    tables = {rec.table for rec in result.recommendations}
    assert f"{SCHEMA}.orders" in tables, result.recommendations
    for rec in result.recommendations:
        assert f" ON {SCHEMA}.orders " in rec.definition


@pytest.mark.asyncio
async def test_search_path_resolves_unqualified_names(driver):
    _, connection_string = driver
    pool = DbConnPool(search_path=f"{SCHEMA}, public")
    await pool.pool_connect(connection_string)
    try:
        rows = await SqlDriver(conn=pool).execute_query(
            "SELECT count(*) AS n FROM orders"
        )
        assert rows is not None and rows[0].cells["n"] == 100000
    finally:
        await pool.close()
