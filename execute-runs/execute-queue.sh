#!/bin/bash

set +e

while true; do
  # Update job queue.
  scripts/execute-runs/update-queue.sh

  # Process next job.
  JOB=$(ls -t queue/ | grep -v "\(^README.md$\|\.wait$\|\.running$\|\.finished$\)" | tail -1)
  if [[ "$JOB" == "" ]]; then
    echo ""
    echo "No jobs available. Build witness store if necessary."
    date -Iseconds
    sleep 600
    continue
  fi
  echo ""
  echo "Processing job: $JOB"
  mv "queue/$JOB" "queue/$JOB.running"
  sleep 10
  scripts/execute-runs/mkRunVerify.sh "$JOB" |& tee -a "./results-logs/$JOB.log"
  mv -f "queue/$JOB.running" "queue/$JOB.finished"
done

echo "All jobs finished."

