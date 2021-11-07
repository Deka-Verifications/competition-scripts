#!/bin/bash

# This file is part of the competition environment.
#
# SPDX-FileCopyrightText: 2011-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# This script gets the following parameters:
#   command (benchmark.py follows by its options, external users can pass benchexec without parameters here),
#   tool (matching name of benchmark definition XML file)
#   benchmark definition (XML file)
#   witness name
#   witness glob suffix
#   output directory
#   waiting time (optional)

BENCHEXEC_COMMAND=$1
TOOL=$2
BENCHMARK_DEFINITION_FILE=$3
WITNESS_TARGET=$4
WITNESS_GLOB_SUFFIX=$5
OUTPUT_DIR=$6
WAIT_TIME=$((($7 - 1) * 30 + 10));
SCRIPTS_DIR=$(realpath "$(dirname "$0")")
ROOT_DIR=$(realpath "$SCRIPTS_DIR/../..")

if [[ "$BENCHEXEC_COMMAND" == "" || "$TOOL" == "" || "$BENCHMARK_DEFINITION_FILE" == "" ||
      "$WITNESS_TARGET" == "" || "$WITNESS_GLOB_SUFFIX" == "" || "$OUTPUT_DIR" == "" ]]; then
  echo "Usage: $0 <command> <tool> <benchmark definition> <witness name> <witness glob suffix> <output directory>"
  exit 1
fi

if [[ ! -e "$ROOT_DIR/benchmark-defs/$BENCHMARK_DEFINITION_FILE" ]]; then
  echo "Benchmark definition $BENCHMARK_DEFINITION_FILE not found."
  exit 1
fi

if [[ $WAIT_TIME -gt 0 ]]; then
  echo "$TOOL with benchmark definition $BENCHMARK_DEFINITION_FILE waits $WAIT_TIME seconds first.";
  sleep $WAIT_TIME;
fi


TOOL_DIR=$(mktemp --directory --tmpdir="./bin/" "$TOOL-XXXXXXXXXX")

echo ""
echo "  Installing $TOOL in $TOOL_DIR"
"$SCRIPTS_DIR/mkInstall.sh" "$TOOL" "$TOOL_DIR"

echo ""
echo "  Executing $TOOL"

cd "$TOOL_DIR" || exit
if [[ ! -e $OUTPUT_DIR ]]; then
  echo "Output folder $OUTPUT_DIR does not exist."
  exit 1
fi
TMP_FILE=$(mktemp --suffix=-provenance.txt)
"$SCRIPTS_DIR/mkProvenanceInfo.sh" "$TOOL" > "$TMP_FILE"
$BENCHEXEC_COMMAND "../../benchmark-defs/$BENCHMARK_DEFINITION_FILE" -o "$OUTPUT_DIR" --description-file "$TMP_FILE"
rm "$TMP_FILE"
#rm -rf "$TOOL_DIR"

echo ""
echo "  Post-processing $TOOL"
cd "$OUTPUT_DIR" || exit
RESULT_DIR=$(ls -dt "${BENCHMARK_DEFINITION_FILE%.xml}".????-??-??_??-??-??.files | head -1)
if [ -e "$RESULT_DIR" ]; then
  ionice -c 3 nice "$SCRIPTS_DIR/initialize-store.sh" "$RESULT_DIR" "$WITNESS_TARGET" "$WITNESS_GLOB_SUFFIX"
fi

echo "  Execution done for $TOOL."
echo ""

