#!/bin/bash

DEF_FILE=$1
SCRIPT_DIR=$(realpath "$(dirname "$0")")

if [ -z "$DEF_FILE" ]; then
    echo "Usage: $0 <benchmark_def>"
    exit 1
fi

$SCRIPT_DIR/execute-runcollection.sh \
    benchexec/bin/benchexec \
    archives/2022/cpachecker.zip \
    $DEF_FILE \
    witness.graphml \
    .graphml \
    results-verified/ \
    --read-only-dir / --read-only-dir /home --overlay-dir ./ \
    --timelimit 600 \
    --memorylimit 1GB \
    --numOfThreads 8 \
    --limitCores 1 \






