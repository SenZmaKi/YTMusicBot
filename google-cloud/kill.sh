#!/usr/bin/env bash

# Find the PID of the process matching "ytmusicbot.discord"
pid=$(ps aux | grep "python3.12 -m ytmusicbot.discord" | grep -v "grep" | awk '{print $2}')

# Check if a PID was found
if [ -n "$pid" ]; then
    echo "Found process with PID: $pid. Terminating..."
    kill -15 "$pid"
    echo "Process terminated."
else
    echo "No matching process found."
fi
