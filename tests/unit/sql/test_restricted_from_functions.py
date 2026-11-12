"""Functions called in FROM must go through the function allowlist (issue #5).

pglast stores a FROM function as RangeFunction.functions = ((FuncCall, None),),
a tuple of tuples. The validator used to skip the inner tuple, so any function
in FROM ran unchecked in restricted mode. Same fix as
crystaldba/postgres-mcp#200 by jssmith (recursive here, so any nesting depth
is covered).
"""

import pytest

from pg_airman_mcp.sql import SafeSqlDriver

BLOCKED = [
    "SELECT * FROM pg_read_file('/etc/passwd')",
    "SELECT * FROM pg_ls_dir('.')",
    "SELECT * FROM pg_read_binary_file('/etc/passwd')",
    "SELECT * FROM pg_stat_file('/etc/passwd')",
    "SELECT * FROM pg_terminate_backend(12345)",
    "SELECT * FROM pg_catalog.pg_read_file('/etc/passwd')",
    "SELECT * FROM (SELECT * FROM pg_read_file('/etc/passwd')) s",
    "SELECT * FROM users u, LATERAL pg_ls_dir(u.name) d",
    "SELECT * FROM ROWS FROM (unnest(ARRAY[1]), pg_ls_dir('.')) t",
    "WITH x AS (SELECT * FROM pg_ls_dir('.')) SELECT * FROM x",
    "SELECT 1 WHERE EXISTS (SELECT 1 FROM pg_read_file('/etc/passwd'))",
]

ALLOWED = [
    "SELECT * FROM unnest(ARRAY[1, 2, 3]) AS t(x)",
    "SELECT * FROM jsonb_array_elements('[1, 2]'::jsonb)",
    "SELECT * FROM ROWS FROM (unnest(ARRAY[1]), unnest(ARRAY[2])) t",
]


@pytest.mark.parametrize("query", BLOCKED)
def test_disallowed_function_in_from_is_rejected(query):
    with pytest.raises(ValueError):
        SafeSqlDriver(sql_driver=None)._validate(query)  # type: ignore[arg-type]


@pytest.mark.parametrize("query", ALLOWED)
def test_allowed_function_in_from_still_passes(query):
    SafeSqlDriver(sql_driver=None)._validate(query)  # type: ignore[arg-type]
