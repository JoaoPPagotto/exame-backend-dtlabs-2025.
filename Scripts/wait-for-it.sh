#!/usr/bin/env bash

# wait-for-it.sh: A simple bash script to wait for a service to be available

# exit on error
set -e

# Default timeout is 30 seconds
TIMEOUT=30
WAIT_HOSTS="5432:5432"

# Function to print usage information
usage() {
  echo "Usage: wait-for-it.sh host:port [-t timeout] [-- command args]"
  exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    *:* ) WAIT_HOSTS="$WAIT_HOSTS $1";;
    -t ) TIMEOUT="$2"; shift;;
    -- ) shift; break;;
    * ) usage;;
  esac
  shift
done

# Wait for the hosts to be available
for host in $WAIT_HOSTS; do
  echo "Waiting for $host..."
  HOST=$(echo $host | cut -d ':' -f 1)
  PORT=$(echo $host | cut -d ':' -f 2)

  # Try to connect to the host until the timeout is reached
  for i in $(seq $TIMEOUT); do
    nc -z "$HOST" "$PORT" && break
    echo "$host not yet available, waiting..."
    sleep 1
  done
done

# Execute the command if provided
if [ "$#" -gt 0 ]; then
  exec "$@"
fi
