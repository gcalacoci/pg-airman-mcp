# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-11-12

First release of the community continuation, published on PyPI as
`airman-mcp`. The command (`pg-airman-mcp`), the Python module
(`pg_airman_mcp`) and the configuration are unchanged.

### Security
- Restricted mode now checks functions called in `FROM` against the function
  allowlist. Before, `SELECT * FROM pg_read_file('/etc/passwd')` passed
  validation even though `SELECT pg_read_file(...)` was rejected (#5, #6).
  Reported by @geo-chen in crystaldba/postgres-mcp#178; same approach as
  @jssmith's fix in crystaldba/postgres-mcp#200.

### Fixed
- Tables in a non-public schema: index tuning keeps the schema, and the new
  `--search-path` option / `AIRMAN_MCP_SEARCH_PATH` setting lets unqualified
  names resolve (#1, #3). Reported by @iBehruz in
  EnterpriseDB/pg-airman-mcp#23.
- Restricted mode tells the agent why a query was rejected, including
  "EXPLAIN ANALYZE is not available in restricted mode" and the parser's
  syntax error (#2, #7).
- `pip install` works again: pglast is pinned to 7.22, since 7.2 is no longer
  on PyPI.

### Changed
- Package renamed to `airman-mcp` on PyPI (was `pg-airman-mcp`).
- `mcp` is capped below 2.0, because mcp 2.x changes the imports this server
  uses (#4). Reported by @camball in crystaldba/postgres-mcp#187 and #237;
  upstream fix by @jssmith.
- All other dependencies refreshed to current versions (#4), including the
  security updates from EnterpriseDB's pending Dependabot PRs.
- Added a `NOTICE` file crediting EnterpriseDB and Crystal DBA.

## [1.1.1] and earlier

Released by EnterpriseDB as `pg-airman-mcp`. See
https://github.com/EnterpriseDB/pg-airman-mcp/releases.

[1.2.0]: https://github.com/gcalacoci/pg-airman-mcp/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/EnterpriseDB/pg-airman-mcp/releases/tag/v1.1.1
