"""Tables in a non-public schema keep their schema through index tuning.

Regression tests for gcalacoci/pg-airman-mcp#1 (EnterpriseDB/pg-airman-mcp#23).
"""

from typing import Any

import pytest
from pglast import parse_sql

from pg_airman_mcp.index.dta_calc import ConditionColumnCollector
from pg_airman_mcp.sql import ColumnCollector, IndexDefinition, TableAliasVisitor
from pg_airman_mcp.sql.index import split_table_name


def _stmt(sql: str) -> Any:
    return parse_sql(sql)[0].stmt


def test_alias_visitor_keeps_schema():
    visitor = TableAliasVisitor()
    visitor(_stmt("SELECT * FROM sales.orders o JOIN public.users u ON true"))
    assert visitor.tables == {"sales.orders", "public.users"}
    assert visitor.aliases["o"] == "sales.orders"
    assert visitor.aliases["u"] == "public.users"


def test_alias_visitor_maps_bare_name_of_qualified_table():
    visitor = TableAliasVisitor()
    visitor(_stmt("SELECT orders.id FROM sales.orders"))
    assert visitor.tables == {"sales.orders"}
    assert visitor.aliases["orders"] == "sales.orders"


def test_alias_visitor_unqualified_unchanged():
    visitor = TableAliasVisitor()
    visitor(_stmt("SELECT * FROM orders o"))
    assert visitor.tables == {"orders"}
    assert visitor.aliases == {"o": "orders"}


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM sales.orders WHERE customer_id = 5",
        "SELECT * FROM sales.orders o WHERE o.customer_id = 5",
        "SELECT * FROM sales.orders WHERE orders.customer_id = 5",
        "SELECT * FROM sales.orders WHERE sales.orders.customer_id = 5",
    ],
)
def test_column_collector_qualified_table(sql):
    columns = ColumnCollector()(_stmt(sql))
    assert columns.get("sales.orders", set()) >= {"customer_id"}
    assert "orders" not in columns
    assert "sales" not in columns


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM sales.orders WHERE customer_id = 5",
        "SELECT * FROM sales.orders o WHERE o.customer_id = 5",
        "SELECT * FROM sales.orders WHERE sales.orders.customer_id = 5",
    ],
)
def test_condition_collector_qualified_table(sql):
    collector = ConditionColumnCollector()
    collector(_stmt(sql))
    assert collector.condition_columns == {"sales.orders": {"customer_id"}}


def test_index_definition_qualified_table():
    idx = IndexDefinition("sales.orders", ("customer_id",))
    assert idx.name == "enterprisedb_idx_sales_orders_customer_id_1"
    assert idx.definition == (
        "CREATE INDEX enterprisedb_idx_sales_orders_customer_id_1 "
        "ON sales.orders USING btree (customer_id)"
    )
    # The definition must parse and keep the schema
    rel = _stmt(idx.definition).relation
    assert (rel.schemaname, rel.relname) == ("sales", "orders")


def test_index_definition_unqualified_unchanged():
    idx = IndexDefinition("orders", ("customer_id",))
    assert idx.name == "enterprisedb_idx_orders_customer_id_1"


@pytest.mark.parametrize(
    "name,expected",
    [
        ("orders", (None, "orders")),
        ("sales.orders", ("sales", "orders")),
    ],
)
def test_split_table_name(name, expected):
    assert split_table_name(name) == expected
