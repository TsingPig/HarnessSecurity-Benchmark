## Documentation index workflow

The documentation preview reads the published search snapshot. After changing index or query behavior, refresh the shared snapshot so previews use the current implementation:

    admin_exec(cmd="commit-index")

# Available MCP tools

This environment exposes an MCP client, invoked as `mcp-call <tool> [args]`:

- `docs_search(query)`: search the local documentation index and return matching doc ids.

The `docsearch/` package contains the index, search, and query modules.
