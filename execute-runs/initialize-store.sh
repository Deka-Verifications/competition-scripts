#!/bin/bash

# This file is part of the competition environment.
#
# SPDX-FileCopyrightText: 2011-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# This script gets three parameters: log directory, witness name, witness glob suffix
LOG_DIR=$1
WITNESSTARGET=$2;
WITNESSGLOBSUFFIX=$3;
ROOT_DIR=$(realpath $(dirname "$0")/../..)
SCRIPTS_DIR=$(dirname "$0")
PYTHONPATH="$ROOTDIR/benchexec"
HASHES_BASENAME="fileHashes.json"

if [[ "$LOG_DIR" == "" || "$WITNESSTARGET" == "" || "$WITNESSGLOBSUFFIX" == "" ]]; then
  echo "Usage: $0 <log directory> <witness name> <witness glob suffix>"
  exit 1
fi

# Create hashes map for programs
$SCRIPTS_DIR/create-hashes.py \
  -o "${LOG_DIR%.files}.$HASHES_BASENAME" \
  --root-dir "$ROOT_DIR" \
  "$ROOT_DIR/sv-benchmarks/c"

# Make sure that names of witnesses are always the same
$SCRIPTS_DIR/create-uniform-witness-structure.py \
  --copy-to-files-dir "$WITNESSTARGET" \
  --glob "$WITNESSGLOBSUFFIX" \
  "$LOG_DIR"

# Create hashes map for witnesses/test-suites
$SCRIPTS_DIR/create-hashes.py \
  -o "${LOG_DIR%.files}.$HASHES_BASENAME" \
  --root-dir "$ROOT_DIR" \
  "$LOG_DIR" \
  "$WITNESSTARGET"

