# NOVA OAR MCP Server

An MCP (Model Context Protocol) server for managing cluster jobs on NOVA's university cluster using OAR (OAR Resource Manager).

## Features

- **List cluster machines**: Get all machine hostnames in the cluster
- **List cluster types**: Get unique cluster names/types
- **Create jobs**: Submit jobs to the cluster with customizable parameters
- **Delete jobs**: Remove jobs by ID
- **Extend job walltime**: Add more time to running jobs
- **Check job status**: Get detailed information about specific jobs
- **List user jobs**: View all jobs for the current user

## Configuration

Set the `CLUSTER_HOSTNAME` environment variable to specify the SSH hostname for the cluster frontend:

```bash
export CLUSTER_HOSTNAME="your-cluster-frontend.example.com"
```

Default value is `cluster`.

## Installation and Usage

1. Install dependencies:
```bash
uv add "mcp[cli]"
```

2. Test the server in development mode:
```bash
uv run mcp dev main.py
```

3. Install in Claude Desktop:
```bash
uv run mcp install main.py --name "NOVA OAR Cluster Manager"
```

## Available Tools

### Machine Management
- **`list_machines()`**: Returns a simple list of all machine hostnames in the cluster
- **`list_machines_detailed()`**: Returns detailed machine information in JSON format with states, properties, and resources
- **`list_clusters()`**: Returns a list of unique cluster names (machine types)

### Job Management
- **`create_job(clusters, nodes, walltime, command, name, best_effort)`**: Creates a new job on the cluster
  - `clusters`: List of cluster names to target (e.g., ['alakazam', 'bulbasaur'])
  - `nodes`: Number of nodes (default: 1)
  - `walltime`: Time in hh:mm:ss format (default: "1:00:00")
  - `command`: Command to execute (default: "sleep 365d")
  - `name`: Optional job name
  - `best_effort`: Whether to make it a best effort job (default: False)

- **`delete_job(job_id)`**: Deletes a job by its ID

### Job Information
- **`get_job_status(job_id)`**: Gets detailed status of a specific job in JSON format
- **`list_all_jobs()`**: Lists all jobs in the cluster with detailed JSON information
- **`list_my_jobs()`**: Lists jobs for the current SSH user with detailed JSON information

### Walltime Management
- **`extend_walltime(job_id, additional_time, force)`**: Adds more walltime to a job
  - `job_id`: The job ID to extend
  - `additional_time`: Time in hh:mm:ss format (e.g., "1:30:00")
  - `force`: Whether to force the change to apply immediately (default: False)

- **`get_walltime_status(job_id)`**: Gets the current walltime change status for a job

## Resources

### `cluster://config`
Provides the current cluster configuration and available OAR commands.

## Features

- **Full cluster targeting**: Create jobs on specific cluster types (alakazam, bulbasaur, etc.)
- **Multiple cluster support**: Target multiple clusters with OR logic
- **JSON-based data**: Structured output for easy integration
- **Comprehensive job management**: Full lifecycle from creation to deletion

## Examples

```python
# List available clusters
clusters = await list_clusters()
# Output: ['alakazam', 'bulbasaur', 'charmander', ...]

# Get detailed machine information
machines = await list_machines_detailed()
# Returns JSON with detailed info for all 2500+ cluster resources

# Create a simple job
job_result = await create_job(
    walltime="0:30:00",
    command="echo 'Hello from cluster'"
)

# Create a job on specific cluster
job_result = await create_job(
    clusters=["alakazam"],
    walltime="2:00:00",
    command="gpu_program",
    name="alakazam-job"
)

# Create a job with multiple cluster options
job_result = await create_job(
    clusters=["alakazam", "bulbasaur"],
    nodes=4,
    walltime="2:00:00",
    command="mpi_program",
    name="multi-cluster-job"
)

# Check detailed job status (returns JSON)
status = await get_job_status(12345)
# Returns: {"Job_Id": 12345, "state": "Running", "owner": "user", ...}

# List all jobs in cluster
all_jobs = await list_all_jobs()

# List jobs for the current SSH user
my_jobs = await list_my_jobs()

# Delete a job
result = await delete_job(12345)

# Extend job walltime by 2 hours
result = await extend_walltime(12345, "2:00:00")

# Force walltime extension
result = await extend_walltime(12345, "1:00:00", force=True)

# Check walltime change status
walltime_status = await get_walltime_status(12345)
```

## Architecture

The server uses SSH to execute OAR commands on the cluster frontend. All commands are executed with a 30-second timeout for safety.

## Security

- Commands are properly escaped to prevent injection attacks
- SSH timeouts prevent hanging connections
- Error messages are sanitized before returning to the user