# airman-mcp

**A Postgres MCP server for AI agents: index tuning, explain plans, health checks and guarded SQL execution.**

[Quick start](#quick-start) • [Install](#install) • [Connect your client](#connect-your-mcp-client) • [Access modes](#access-modes) • [Configuration](#configuration-reference) • [Tools](#tools) • [FAQ](#faq)

> **Status (November 2026).** airman-mcp is an independent community fork of
> [EnterpriseDB/pg-airman-mcp](https://github.com/EnterpriseDB/pg-airman-mcp), continuing from its
> 1.1.1 release (May 2026). Version 1.2.0 is on GitHub only, as source and as the files attached to the
> [v1.2.0 release](https://github.com/gcalacoci/pg-airman-mcp/releases/tag/v1.2.0). It is **not on
> PyPI or any image registry yet**: install it from a checkout or from the release files.
>
> The `enterprisedb/pg-airman-mcp` Docker image and the `pg-airman-mcp` 1.1.1 package on PyPI are the
> old release. They do not have the 1.2.0 fixes, including a restricted-mode security fix.

## What it does

airman-mcp gives an AI agent a connection to your Postgres database, plus tools that help it reason
about performance:

- **Database health:** index health, connection use, buffer cache, vacuum and wraparound risk,
  sequence limits, replication lag, invalid constraints.
- **Index tuning:** searches many candidate indexes for your workload and weighs speed against size,
  with `hypopg` to ask the planner "what if this index existed?".
- **Query plans:** `EXPLAIN`, `EXPLAIN ANALYZE`, and plans with hypothetical indexes.
- **Schema tools:** schemas, tables, columns, constraints and indexes, so the agent writes correct SQL.
- **Guarded SQL:** a restricted mode for databases you care about. Queries run read-only, they are
  parsed and checked before they run, and they have a time limit.
- **Authentication:** optional OAuth 2.0 bearer tokens (token introspection or local JWT checks).
- **Governance:** label connections by purpose and trace agent sessions in `pg_stat_activity`.

It speaks the three MCP transports: stdio, SSE and streamable HTTP.

## Quick start

1. **Get the code:**

   ```bash
   git clone https://github.com/gcalacoci/pg-airman-mcp.git
   cd pg-airman-mcp
   ```

2. **Build the Docker image** (or install with Python, see [Install](#install)):

   ```bash
   docker build -t airman-mcp .
   ```

3. **Check your database URL works**, for example with `psql "postgresql://user:password@localhost:5432/dbname"`.

4. **Add the server to your MCP client.** For Claude Code:

   ```bash
   claude mcp add airman -e AIRMAN_MCP_DATABASE_URL=postgresql://user:password@localhost:5432/dbname \
     -- docker run -i --rm -e AIRMAN_MCP_DATABASE_URL airman-mcp --access-mode=restricted
   ```

   Other clients: see [Connect your MCP client](#connect-your-mcp-client).

5. **Ask something:** "Check the health of my database and list any problems."

## Install

You need a database URL that works, and either Docker or Python 3.12+.
Docker is the easier path: the image carries every dependency.

### Option A: Docker image from the checkout

```bash
git clone https://github.com/gcalacoci/pg-airman-mcp.git
cd pg-airman-mcp
git checkout v1.2.0          # optional: pin the release
docker build -t airman-mcp .
```

The image runs `pg-airman-mcp` as its entry point, so any option in the
[configuration reference](#configuration-reference) goes after the image name.

Inside the container, the entry point rewrites `localhost` in the database URL to the Docker host
(`host.docker.internal` on Docker Desktop, `172.17.0.1` on Linux), so a URL that works on your machine
works in the container too. On Kubernetes it leaves `localhost` alone, for sidecar setups.

### Option B: Python from the checkout

Install the command with [uv](https://docs.astral.sh/uv/getting-started/installation/) or pipx.
No compiler is needed: psycopg's binary wheel ships its own libpq.

```bash
git clone https://github.com/gcalacoci/pg-airman-mcp.git
cd pg-airman-mcp
uv tool install .            # or: pipx install .
pg-airman-mcp --help
```

On a platform with no psycopg binary wheel, install the `c` extra instead: `uv tool install '.[c]'`.
It builds psycopg against your system libpq, so it needs a C compiler, the libpq headers and
`pg_config` (`libpq-dev` on Debian and Ubuntu, `libpq` from Homebrew on macOS). The
[psycopg install guide](https://www.psycopg.org/psycopg3/docs/basic/install.html#local-installation)
lists the packages for each system.

### Option C: the files from the GitHub release

Each release has a wheel and a source archive attached. Install the wheel directly:

```bash
uv tool install https://github.com/gcalacoci/pg-airman-mcp/releases/download/v1.2.0/airman_mcp-1.2.0-py3-none-any.whl
```

## Connect your MCP client

Every example below uses restricted mode. Switch to `--access-mode=unrestricted` only for a database
you can rebuild (see [Access modes](#access-modes)).

Replace the URL with your own [Postgres connection URI](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING-URIS).

### Claude Code

```bash
# Docker image
claude mcp add airman -e AIRMAN_MCP_DATABASE_URL=postgresql://user:password@localhost:5432/dbname \
  -- docker run -i --rm -e AIRMAN_MCP_DATABASE_URL airman-mcp --access-mode=restricted

# Installed command (Option B or C)
claude mcp add airman -e AIRMAN_MCP_DATABASE_URL=postgresql://user:password@localhost:5432/dbname \
  -- pg-airman-mcp --access-mode=restricted
```

### Claude Desktop

Open the configuration file from **Settings → Developer → Edit Config**, or directly:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add the server under `mcpServers`. With the Docker image:

```json
{
  "mcpServers": {
    "airman": {
      "command": "docker",
      "args": ["run", "-i", "--rm", "-e", "AIRMAN_MCP_DATABASE_URL",
               "airman-mcp", "--access-mode=restricted"],
      "env": {
        "AIRMAN_MCP_DATABASE_URL": "postgresql://user:password@localhost:5432/dbname"
      }
    }
  }
}
```

With the installed command:

```json
{
  "mcpServers": {
    "airman": {
      "command": "pg-airman-mcp",
      "args": ["--access-mode=restricted"],
      "env": {
        "AIRMAN_MCP_DATABASE_URL": "postgresql://user:password@localhost:5432/dbname"
      }
    }
  }
}
```

If the client cannot find `pg-airman-mcp`, use the full path that `which pg-airman-mcp` prints.

### Other clients

Cursor, Windsurf, Cline, Goose and most other clients take the same `command`, `args` and `env`
fields. Cursor: Command Palette → Cursor Settings → MCP. Windsurf: Command Palette → Open Windsurf
Settings Page. Goose: `goose configure` → Add Extension.

## Access modes

| Mode | What the agent can do | Use it for |
|---|---|---|
| `restricted` | Read-only queries, checked before they run, with a time limit | Any database you care about |
| `unrestricted` (default) | Anything the database role can do, including writes and DDL | Development databases you can rebuild |

In restricted mode every query goes through three layers:

1. **Parsing.** The query is parsed with [pglast](https://pglast.readthedocs.io/) and rejected unless
   every statement is a read-only type (`SELECT`, `EXPLAIN`, `SHOW`, `ANALYZE`, `VACUUM` and similar)
   and every function it calls, anywhere in the query, is on an allowlist. `COMMIT`, `ROLLBACK`,
   locking clauses and `EXPLAIN ANALYZE` (it runs the query) are rejected.
2. **A read-only transaction.** The query runs inside `BEGIN TRANSACTION READ ONLY`.
3. **A time limit:** each query is cancelled after 30 seconds.

When a query is rejected, the agent gets the reason, for example
`Function pg_read_file is not allowed` or
`EXPLAIN ANALYZE is not available in restricted mode`, so it can change course instead of retrying.

The database role still matters. A superuser, or a role with `pg_read_server_files`, can do more
than you may expect if a check is ever missed. Connect with the least-privileged role that does the
job.

### Writes allowed in restricted mode

Two kinds of small writes can be switched on in restricted mode:

| Setting | Default | Allows |
|---|---|---|
| `ALLOW_COMMENT_IN_RESTRICTED` | `true` | `COMMENT ON` through the `add_comment_to_object` tool |
| `ALLOW_ALIAS_WRITE_IN_RESTRICTED` | `false` | `create_alias` and `delete_alias` (semantic aliases, see [Tools](#tools)) |

These writes bypass the read-only checks through one code path, and each one is logged.

## Transports

The default transport is **stdio**: the client starts the server and talks to it over standard
input and output. All the examples above use it.

**SSE** and **streamable HTTP** run the server as a long-lived HTTP service that several clients can
share:

```bash
# Streamable HTTP, Docker image (the image listens on port 8080)
docker run -p 8080:8080 -e AIRMAN_MCP_DATABASE_URL=postgresql://user:password@localhost:5432/dbname \
  airman-mcp --access-mode=restricted --transport=streamable-http

# SSE, installed command (listens on localhost:8000)
pg-airman-mcp --access-mode=restricted --transport=sse
```

Ports differ by how you run it:

| | SSE | Streamable HTTP |
|---|---|---|
| Installed command | `localhost:8000` | `localhost:8001` |
| Docker image | `0.0.0.0:8000` | `0.0.0.0:8080` |

Pass `--sse-port` or `--streamable-http-port` to change them.

Client configuration:

```json
{ "mcpServers": { "airman": { "url": "http://localhost:8080/mcp" } } }
```

For SSE use `"type": "sse", "url": "http://localhost:8000/sse"`. Windsurf calls the field
`serverUrl` instead of `url`.

### DNS rebinding protection

The MCP SDK can check the `Host` and `Origin` headers of incoming HTTP requests. It is **off** by
default, because it answers `421 Misdirected Request` behind proxies and Kubernetes services. Turn it
on for servers reachable from a browser:

```bash
AIRMAN_MCP_DNS_REBINDING_PROTECTION=true                 # SDK default: localhost only
AIRMAN_MCP_ALLOWED_HOSTS="airman-service:*,localhost:*"  # setting a list turns it on
AIRMAN_MCP_ALLOWED_ORIGINS="http://airman-service:*,http://localhost:*"
```

## Authentication (optional)

Off by default. When on, every tool call needs an OAuth 2.0 bearer token, checked in one of two ways:

- **Token introspection** (default): asks your authorization server about each token
  ([RFC 7662](https://datatracker.ietf.org/doc/html/rfc7662)). Revocation takes effect at once.
- **JWT**: checks the token signature locally against the server's published keys
  ([JWKS](https://datatracker.ietf.org/doc/html/rfc7517)). No network call per request.

```bash
# Introspection
AIRMAN_MCP_AUTH_ENABLED=true
AIRMAN_MCP_AUTH_SERVER_URL=https://auth.example.com

# JWT
AIRMAN_MCP_AUTH_ENABLED=true
AIRMAN_MCP_AUTH_TYPE=jwt
AIRMAN_MCP_AUTH_SERVER_URL=https://auth.example.com
AIRMAN_MCP_JWT_ISSUER=https://auth.example.com
```

With stdio, also set `AIRMAN_MCP_SERVER_URL` (for example `http://localhost:8000`): the token's
resource check needs a server URL, and stdio has none. With SSE and streamable HTTP it is detected.

Safeguards: endpoint URLs must be `https://` or `localhost`; TLS certificates are verified; JWT
accepts only asymmetric algorithms (RS256/384/512, ES256/384/512, never `HS*` or `none`); keys are
cached (5 minutes by default); tokens must carry the required scopes (`mcp:postgres:access` by
default).

Provider examples, the choice between the two methods and every option:
[docs/jwt-authentication.md](docs/jwt-authentication.md) and the
[configuration reference](#authentication-settings).

## Governance

### Purpose labels

Give each server a purpose, and every connection it opens shows up as `airman:<purpose>` in
`application_name`:

```bash
AIRMAN_MCP_PURPOSE=credit-scoring     # lowercase letters, digits and hyphens
```

DBAs can then filter `pg_stat_activity`, add `%a` to `log_line_prefix`, or alert by purpose.

### Session tracing

```bash
AIRMAN_MCP_TRACING=true
```

The server takes the session ID from the MCP request (`_meta.sessionId`; a random ID per server if the
client sends none) and adds its first 8 characters to `application_name`:
`airman:credit-scoring/91c11602`, or `airman:_/91c11602` without a purpose. It stays on the connection
while idle, so slow queries in `pg_stat_activity` and in the logs trace back to an agent session.

The pool keeps 1 to 5 connections. A connection shows the session suffix from its first tool call on.

## Postgres extensions (optional)

Index tuning and query statistics need two extensions:

- `pg_stat_statements`: which queries run slowest or most often.
- `hypopg`: hypothetical indexes, to see the planner's choice before you build anything.

On managed services (Amazon RDS, Azure, Google Cloud SQL) both are usually available:

```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS hypopg;
```

On your own server, add `pg_stat_statements` to `shared_preload_libraries` and restart first, and
install `hypopg` from your package manager (for example `postgresql-16-hypopg` on Debian and Ubuntu).

## Tables outside the `public` schema

Postgres finds an unqualified name such as `orders` only through the `search_path`, which is
`"$user", public` by default. Either qualify names (`sales.orders`) or set the path for the server:

```bash
AIRMAN_MCP_SEARCH_PATH="sales,public"     # or --search-path "sales,public"
```

The connection URL works too: `postgresql://user:password@host/db?options=-csearch_path%3Dsales,public`.
Index tuning keeps the schema, so recommendations come back as `CREATE INDEX ... ON sales.orders ...`.

## Tools

| Tool | What it does |
|---|---|
| `list_schemas` | Lists the schemas in the database |
| `list_objects` | Lists tables, views, sequences or extensions in a schema |
| `get_object_details` | Columns, constraints and indexes of one object |
| `execute_sql` | Runs SQL (restricted mode applies its checks) |
| `explain_query` | Shows the plan, optionally with `ANALYZE` (unrestricted only) or with hypothetical indexes |
| `get_top_queries` | Slowest queries from `pg_stat_statements`, by total or mean time |
| `analyze_workload_indexes` | Finds the heaviest queries and recommends indexes for them |
| `analyze_query_indexes` | Recommends indexes for up to 10 queries you give it |
| `analyze_db_health` | Runs the health checks listed under [What it does](#what-it-does) |
| `add_comment_to_object` / `remove_comment` | Sets or removes `COMMENT ON` a table, view or column |

**Semantic tools (need EDB's AIDB extension).** These work only on a database with
[AIDB](https://www.enterprisedb.com/docs/edb-postgres-ai/ai-accelerator/) installed:
`search_kb`, `list_kbs`, `get_kb_stats`, `refresh_kb`, `create_alias`, `delete_alias`,
`search_aliases`, `execute_alias`, `list_aliases`, `discover_context`. They search a knowledge base of
your schema by meaning and keep reusable, named SQL queries ("aliases"). `execute_alias` takes an
optional `execute_as_role`; the connecting role needs `SET ROLE` rights for it.

### Things to ask

- "Check the health of my database and list any problems."
- "What are the slowest queries, and how can I speed them up?"
- "Analyze my workload and suggest indexes."
- "Help me optimize this query: `SELECT * FROM orders JOIN customers ON ...`"

## Configuration reference

Settings come from, in order: command-line options, environment variables, defaults.
Environment variables start with `AIRMAN_MCP_`.

### Server settings

| Variable | Option | Description | Default |
|---|---|---|---|
| `AIRMAN_MCP_DATABASE_URL` | first argument | Postgres connection URL | *(required)* |
| `AIRMAN_MCP_ACCESS_MODE` | `--access-mode` | `unrestricted` or `restricted` | `unrestricted` |
| `AIRMAN_MCP_TRANSPORT` | `--transport` | `stdio`, `sse` or `streamable-http` | `stdio` |
| `AIRMAN_MCP_SSE_HOST` | `--sse-host` | SSE host | `localhost` |
| `AIRMAN_MCP_SSE_PORT` | `--sse-port` | SSE port | `8000` |
| `AIRMAN_MCP_STREAMABLE_HTTP_HOST` | `--streamable-http-host` | Streamable HTTP host | `localhost` |
| `AIRMAN_MCP_STREAMABLE_HTTP_PORT` | `--streamable-http-port` | Streamable HTTP port | `8001` |
| `AIRMAN_MCP_SEARCH_PATH` | `--search-path` | `search_path` for every connection, e.g. `sales,public` | role default |
| `AIRMAN_MCP_PURPOSE` | `--purpose` | Purpose label in `application_name` | none |
| `AIRMAN_MCP_TRACING` | `--tracing` | Session ID in `application_name` | `false` |
| `AIRMAN_MCP_DNS_REBINDING_PROTECTION` | `--dns-rebinding-protection` | Check `Host`/`Origin` headers | `false` |
| `AIRMAN_MCP_ALLOWED_HOSTS` | `--allowed-hosts` | Allowed `Host` values, comma-separated | empty |
| `AIRMAN_MCP_ALLOWED_ORIGINS` | `--allowed-origins` | Allowed `Origin` values, comma-separated | empty |

The Docker image sets the HTTP host to `0.0.0.0`, and the streamable HTTP port to `8080`, unless you pass your own.

### Authentication settings

| Variable | Option | Description | Default |
|---|---|---|---|
| `AIRMAN_MCP_AUTH_ENABLED` | `--auth-enabled` | Require bearer tokens | `false` |
| `AIRMAN_MCP_AUTH_TYPE` | `--auth-type` | `introspection` or `jwt` | `introspection` |
| `AIRMAN_MCP_AUTH_SERVER_URL` | `--auth-server-url` | Authorization server base URL | `http://localhost:9000` |
| `AIRMAN_MCP_AUTH_INTROSPECTION_ENDPOINT` | `--auth-introspection-endpoint` | Introspection URL | `{server}/introspect` |
| `AIRMAN_MCP_AUTH_INTROSPECTION_CLIENT_ID` | `--auth-introspection-client-id` | Client ID for introspection | none |
| `AIRMAN_MCP_AUTH_INTROSPECTION_CLIENT_SECRET` | `--auth-introspection-client-secret` | Client secret for introspection | none |
| `AIRMAN_MCP_AUTH_REQUIRED_SCOPES` | `--auth-required-scopes` | Required scopes, comma-separated | `mcp:postgres:access` |
| `AIRMAN_MCP_AUTH_VALIDATE_RESOURCE` | `--auth-validate-resource` | RFC 8707 resource check | `false` |
| `AIRMAN_MCP_JWT_JWKS_URL` | `--jwt-jwks-url` | JWKS URL | `{server}/.well-known/jwks.json` |
| `AIRMAN_MCP_JWT_ISSUER` | `--jwt-issuer` | Expected `iss` (required for JWT) | none |
| `AIRMAN_MCP_JWT_AUDIENCE` | `--jwt-audience` | Expected `aud` | server URL |
| `AIRMAN_MCP_JWT_ALGORITHMS` | `--jwt-algorithms` | Allowed algorithms | `RS256` |
| `AIRMAN_MCP_JWT_CLOCK_SKEW` | `--jwt-clock-skew` | Clock skew, seconds | `30` |
| `AIRMAN_MCP_JWT_JWKS_CACHE_TTL` | `--jwt-jwks-cache-ttl` | Key cache lifetime, seconds | `300` |
| `AIRMAN_MCP_SERVER_URL` | environment only | This server's URL (needed for stdio with auth) | detected for HTTP |

### Other settings

| Variable | Description | Default |
|---|---|---|
| `ALLOW_COMMENT_IN_RESTRICTED` | Allow `COMMENT ON` in restricted mode | `true` |
| `ALLOW_ALIAS_WRITE_IN_RESTRICTED` | Allow alias create/delete in restricted mode | `false` |
| `OPENAI_API_KEY` | Turns on the experimental LLM index tuning | none |

## How it works

### Index tuning

1. **Pick the queries.** Either the ones you pass in, or the heaviest ones in `pg_stat_statements`.
   Queries that differ only in their constants count as one.
2. **List candidate indexes** from the columns used in filters, joins, grouping and sorting, including
   multi-column combinations.
3. **Search.** A greedy search adapted from Microsoft's
   [Anytime algorithm](https://www.microsoft.com/en-us/research/wp-content/uploads/2020/06/Anytime-Algorithm-of-Database-Tuning-Advisor-for-Microsoft-SQL-Server.pdf):
   find the best single index, then the best one to add to it, and so on. `hypopg` gives the
   planner's cost for each set, with realistic constants sampled from table statistics. The search
   stops when time runs out or a round gains less than 10%.
4. **Weigh speed against size.** By default an index set must earn its space: up to 10× the storage
   for a 100× speed-up.

The answer shows each round's work and the plans before and after, so the agent can explain the
choice. Compared to [Dexter](https://github.com/ankane/dexter/), the search covers more options and
takes longer.

**Experimental:** with `OPENAI_API_KEY` set, an LLM proposes index sets instead of the greedy
search ([Optimization by LLM](https://arxiv.org/abs/2309.03409)), and `hypopg` scores each proposal.

### Health checks

Adapted from [PgHero](https://github.com/ankane/pghero): unused, duplicate and bloated indexes;
buffer cache hit rate; connection use; vacuum and transaction ID wraparound; replication lag and
slots; invalid constraints; sequences close to their maximum.

### Why tools, not resources

MCP clients support tools far more widely than resources, so schema information comes through tools
such as `list_objects` and `get_object_details`.

## FAQ

**Which Postgres versions?** CI runs the test suite against Postgres 13, 14, 15, 16 and 17.

**How is it different from other Postgres MCP servers?** Most give the agent a connection. This one
adds deterministic tools: decades-old index tuning and health check methods that are faster,
cheaper and more repeatable than asking the model to work it out.

**Why does the agent see "relation does not exist"?** The table is probably outside `public`. See
[Tables outside the `public` schema](#tables-outside-the-public-schema).

**Is restricted mode safe for production?** It is built to be conservative, and 1.2.0 closed a hole
where functions in `FROM` skipped the allowlist. Treat it as one layer: also use a least-privileged
role, and do not enable untrusted procedural languages on that database.

## Development

```bash
git clone https://github.com/gcalacoci/pg-airman-mcp.git
cd pg-airman-mcp
uv sync
uv run pg-airman-mcp "postgresql://user:password@localhost:5432/dbname"
uv run pytest                             # integration tests start Postgres 13-17 in Docker
uv run ruff check . && uv run ruff format --check . && uv run pyright
```

The AIDB integration tests need a Postgres with AIDB:
`AIDB_TEST_DSN=postgresql://user@localhost:28816/aidb SKIP_AIDB_TESTS=0 uv run pytest tests/integration/semantics/`.

**Contributing:** open an issue first, then a pull request that references it. If the problem was
reported or fixed in an upstream project, link that issue and credit the people involved.

## History and credits

- [Crystal DBA](https://www.crystaldba.ai) created the server as
  [postgres-mcp](https://github.com/crystaldba/postgres-mcp).
- [EnterpriseDB](https://www.enterprisedb.com) forked it as
  [pg-airman-mcp](https://github.com/EnterpriseDB/pg-airman-mcp) and added authentication,
  governance, semantic tools and more, up to version 1.1.1.
- This repository is a community fork of EDB's code from 1.1.1 onwards, published as `airman-mcp`.
  It is not affiliated with EnterpriseDB or Crystal DBA.

Fixes ported from those projects credit their authors in the
[changelog](CHANGELOG.md) and the release notes. License: MIT, see [LICENSE](LICENSE) and
[NOTICE](NOTICE). Issues and plans: [GitHub issues](https://github.com/gcalacoci/pg-airman-mcp/issues).
