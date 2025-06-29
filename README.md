# nova-oar-mcp

MCP server for managing cluster jobs on NOVA's university cluster using OAR.

## What is this?

This is a Model Context Protocol (MCP) server that provides tools for interacting with NOVA's university cluster via OAR (OAR Resource and Job Management System). It allows you to:

- List machines and clusters
- Create, monitor, and delete jobs
- Extend job walltime
- Get detailed job status information

## Installation

This tool requires [uv](https://docs.astral.sh/uv/) to be installed.

Install the MCP server using Claude Code:

```bash
claude mcp add nova-oar-mcp -e CLUSTER_HOSTNAME=<your-cluster-hostname> -- uvx --from git+https://github.com/diogo464/nova-oar-mcp nova-oar-mcp
```

Replace `<your-cluster-hostname>` with your actual cluster hostname (e.g., `cluster.example.edu`), the same you would use when running `ssh`.

## Configuration

The server requires SSH access to your cluster. Make sure:

1. You have SSH key-based authentication set up for your cluster
2. The `CLUSTER_HOSTNAME` environment variable points to your cluster's SSH hostname
