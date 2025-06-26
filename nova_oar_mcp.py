#!/usr/bin/env python3
"""
NOVA OAR MCP Server

An MCP server for managing cluster jobs on NOVA's university cluster using OAR.
Provides tools to list machines, manage jobs, and interact with the cluster.
"""

import os
import subprocess
import asyncio
import json
from typing import Optional, List, Dict, Any
import re
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP

# Configuration
CLUSTER_HOSTNAME = os.environ.get("CLUSTER_HOSTNAME", "cluster")

# Create the MCP server
mcp = FastMCP("NOVA OAR Cluster Manager")


@dataclass
class JobCreationParams:
    """Parameters for creating a new job"""
    clusters: Optional[List[str]] = None
    nodes: int = 1
    walltime: str = "1:00:00"
    command: str = "sleep 365d"
    name: Optional[str] = None
    best_effort: bool = False


async def run_ssh_command(command: str) -> str:
    """Execute a command on the cluster via SSH"""
    full_command = ["ssh", CLUSTER_HOSTNAME, command]
    try:
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            check=True,
            timeout=30
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Command failed: {e.stderr.strip()}")
    except subprocess.TimeoutExpired:
        raise ValueError("Command timed out")


@mcp.tool()
async def list_machines() -> List[str]:
    """List all machine hostnames in the cluster"""
    output = await run_ssh_command("oarnodes -l")
    machines = [line.strip() for line in output.split('\n') if line.strip()]
    return machines


@mcp.tool()
async def list_machines_detailed() -> Dict[str, Any]:
    """List all machines with detailed information in JSON format"""
    output = await run_ssh_command("oarnodes -J")
    try:
        return json.loads(output)
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse JSON output: {str(e)}", "raw_output": output}


@mcp.tool()
async def list_clusters() -> List[str]:
    """List all unique cluster names (machine types)"""
    machines = await list_machines()
    clusters = set()
    
    for machine in machines:
        # Split by first '-' and take the part before it
        if '-' in machine:
            cluster_name = machine.split('-')[0]
            clusters.add(cluster_name)
    
    return sorted(list(clusters))


@mcp.tool()
async def delete_job(job_id: int) -> str:
    """Delete a job by its ID"""
    try:
        output = await run_ssh_command(f"oardel {job_id}")
        return f"Job {job_id} deletion requested: {output}"
    except ValueError as e:
        return f"Failed to delete job {job_id}: {str(e)}"


@mcp.tool()
async def extend_walltime(job_id: int, additional_time: str, force: bool = False) -> str:
    """
    Add more walltime to a job
    
    Args:
        job_id: The job ID to extend
        additional_time: Additional time in format hh:mm:ss (e.g., "1:30:00" for 1.5 hours)
        force: Whether to force the change to apply immediately
    """
    try:
        # Validate time format
        if not re.match(r'^\d{1,2}:\d{2}:\d{2}$', additional_time):
            return "Invalid time format. Use hh:mm:ss (e.g., '1:30:00')"
        
        command = f"oarwalltime {job_id} +{additional_time}"
        if force:
            command += " --force"
        
        output = await run_ssh_command(command)
        return f"Extended walltime for job {job_id}: {output}"
    except ValueError as e:
        return f"Failed to extend walltime for job {job_id}: {str(e)}"


@mcp.tool()
async def get_walltime_status(job_id: int) -> str:
    """
    Get the current walltime change status for a job
    
    Args:
        job_id: The job ID to check
    """
    try:
        output = await run_ssh_command(f"oarwalltime {job_id}")
        return f"Walltime status for job {job_id}: {output}"
    except ValueError as e:
        return f"Failed to get walltime status for job {job_id}: {str(e)}"


@mcp.tool()
async def create_job(
    clusters: Optional[List[str]] = None,
    nodes: int = 1,
    walltime: str = "1:00:00",
    command: str = "sleep 365d",
    name: Optional[str] = None,
    best_effort: bool = False
) -> str:
    """
    Create a new job on the cluster
    
    Args:
        clusters: List of cluster names to select from (e.g., ['alakazam', 'bulbasaur'])
        nodes: Number of nodes to request (default: 1)
        walltime: Walltime in hh:mm:ss format (default: "1:00:00")
        command: Command to execute (default: "sleep 365d")
        name: Optional job name
        best_effort: Whether to make this a best effort job (default: False)
    """
    try:
        # Validate walltime format
        if not re.match(r'^\d{1,2}:\d{2}:\d{2}$', walltime):
            return "Invalid walltime format. Use hh:mm:ss (e.g., '1:00:00')"
        
        # Build resource specification with cluster constraints
        if clusters:
            available_clusters = await list_clusters()
            invalid_clusters = [c for c in clusters if c not in available_clusters]
            if invalid_clusters:
                return f"Invalid clusters: {invalid_clusters}. Available: {available_clusters}"
            
            if len(clusters) == 1:
                cluster_part = f"{{cluster='{clusters[0]}'}}"
            else:
                cluster_constraint = " OR ".join([f"cluster='{c}'" for c in clusters])
                cluster_part = f"{{({cluster_constraint})}}"
            
            resource_string = f"{cluster_part}/nodes={nodes},walltime={walltime}"
        else:
            resource_string = f"nodes={nodes},walltime={walltime}"
        
        # Build oarsub command
        oarsub_args = ["oarsub", "-l", resource_string]
        
        # Add optional name
        if name:
            oarsub_args.extend(["-n", name])
        
        # Add best effort flag
        if best_effort:
            oarsub_args.extend(["-t", "besteffort"])
        
        # Add the command to execute
        oarsub_args.append(command)
        
        # Execute the command - need special handling for -l argument with cluster constraints
        if clusters:
            # Build command with proper quoting for resource specification
            cmd_parts = ["oarsub", "-l"]
            cmd_parts.append(f'"{resource_string}"')
            if name:
                cmd_parts.extend(["-n", name])
            if best_effort:
                cmd_parts.extend(["-t", "besteffort"])
            cmd_parts.append(f"'{command}'")
            full_command = " ".join(cmd_parts)
        else:
            full_command = " ".join(f"'{arg}'" if " " in arg else arg for arg in oarsub_args)
        
        output = await run_ssh_command(full_command)
        
        # Extract job ID from output
        job_id_match = re.search(r'OAR_JOB_ID=(\d+)', output)
        if job_id_match:
            job_id = job_id_match.group(1)
            return f"Job created successfully with ID: {job_id}\nOutput: {output}"
        else:
            return f"Job submission completed: {output}"
            
    except ValueError as e:
        return f"Failed to create job: {str(e)}"


@mcp.tool()
async def get_job_status(job_id: int) -> Dict[str, Any]:
    """Get the detailed status of a specific job in JSON format"""
    try:
        output = await run_ssh_command(f"oarstat -j {job_id} -J")
        return json.loads(output)
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse JSON output: {str(e)}", "raw_output": output}
    except ValueError as e:
        return {"error": f"Failed to get job status for {job_id}: {str(e)}"}


@mcp.tool()
async def list_all_jobs() -> Dict[str, Any]:
    """List all jobs in the cluster with detailed JSON information"""
    try:
        output = await run_ssh_command("oarstat -J")
        return json.loads(output)
    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse JSON output: {str(e)}", "raw_output": output}
    except ValueError as e:
        return {"error": f"Failed to list jobs: {str(e)}"}


@mcp.tool()
async def list_my_jobs() -> Dict[str, Any]:
    """List jobs for the current SSH user with detailed JSON information"""
    try:
        # First check if user has jobs with regular oarstat
        regular_output = await run_ssh_command("oarstat -u")
        if not regular_output.strip():
            return {"message": "No jobs found for current user", "jobs": {}}
        
        # If user has jobs, get JSON output
        output = await run_ssh_command("oarstat -u -J")
        return json.loads(output)
    except json.JSONDecodeError as e:
        # Fallback to regular output if JSON fails
        try:
            regular_output = await run_ssh_command("oarstat -u")
            return {"message": "Jobs for current user (text format due to JSON parsing error)", "output": regular_output}
        except ValueError:
            return {"error": f"Failed to parse JSON output and fallback failed: {str(e)}", "raw_output": output}
    except ValueError as e:
        return {"error": f"Failed to list jobs for current user: {str(e)}"}


@mcp.resource("cluster://config")
def get_cluster_config() -> str:
    """Get the current cluster configuration"""
    return f"""NOVA OAR Cluster Configuration:
- Cluster Hostname: {CLUSTER_HOSTNAME}
- Default Walltime: 1:00:00
- Default Nodes: 1
- Default Command: sleep 365d

Available OAR Commands:
- List machines: oarnodes -l
- List jobs: oarstat
- Create job: oarsub -l <resources> <command>
- Delete job: oardel <jobid>
- Extend walltime: oarwalltime <jobid> +<time>
"""


def main():
    """Entry point for the nova-oar-mcp command"""
    mcp.run()


if __name__ == "__main__":
    main()
