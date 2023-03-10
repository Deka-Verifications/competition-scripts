#!/bin/bash

# This file is part of the competition environment.
#
# SPDX-FileCopyrightText: 2011-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# This script gets the following parameters:
#   benchmarking script (I use `benchmark.py` here, to execute the benchmark of VerifierCloud, others can pass benchexec here)
#   tool archive (archive to run the benchmark with`)
#   benchmark definition (XML file)
#   witness name
#   witness glob suffix
#   output directory
#   the rest are parameters for the benchmarking script (optional) and will be passed to it directly

BENCHEXEC_SCRIPT=$1
TOOL_ARCHIVE=$2
BENCHMARK_DEFINITION_FILE=$3
WITNESS_TARGET=$4
WITNESS_GLOB_SUFFIX=$5
OUTPUT_DIR=$6
shift 6
BENCHEXEC_OPTIONS="$*"

SCRIPTS_DIR=$(realpath "$(dirname "$0")")

if [[ "$BENCHEXEC_SCRIPT" == "" || "$TOOL_ARCHIVE" == "" || "$BENCHMARK_DEFINITION_FILE" == "" ||
      "$WITNESS_TARGET" == "" || "$WITNESS_GLOB_SUFFIX" == "" || "$OUTPUT_DIR" == "" ]]; then
  echo "Usage: $0 <command> <tool> <benchmark definition> <witness name> <witness glob suffix> <output directory>"
  exit 1
fi

if [[ -e "$TOOL_ARCHIVE" ]]; then
  TOOL="$(basename "${TOOL_ARCHIVE%.zip}")"
else
  echo "Tool archive $TOOL_ARCHIVE not found."
  exit 1
fi

TOOL_DIR=$(mktemp --directory --tmpdir="./bin/" "$TOOL-XXXXXXXXXX")

if [[ -e "$BENCHEXEC_SCRIPT" ]]; then
  BENCHEXEC_SCRIPT="$(realpath --relative-to="$TOOL_DIR" "$BENCHEXEC_SCRIPT")"
else
  echo "Benchmark script $BENCHEXEC_SCRIPT not found."
  exit 1
fi

if [[ -e "$BENCHMARK_DEFINITION_FILE" ]]; then
  BENCHMARK_DEFINITION_FILE="$(realpath --relative-to="$TOOL_DIR" "$BENCHMARK_DEFINITION_FILE")"
else
  echo "Benchmark definition $BENCHMARK_DEFINITION_FILE not found."
  exit 1
fi

if [[ -e "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="$(realpath --relative-to="$TOOL_DIR" "$OUTPUT_DIR")"
else
  echo "Output directory $OUTPUT_DIR not found."
  exit 1
fi

echo "$TOOL with benchmark definition $(basename "$BENCHMARK_DEFINITION_FILE") waits 10 seconds first.";
sleep 10;


echo ""
echo "  Installing $TOOL in $TOOL_DIR"
"$SCRIPTS_DIR/mkInstall.sh" "$TOOL_ARCHIVE" "$TOOL_DIR"

echo ""
echo "  Executing $TOOL"

TMP_FILE=$(mktemp --suffix=-provenance.txt)
"$SCRIPTS_DIR/mkProvenanceInfo.sh" "$TOOL_ARCHIVE" > "$TMP_FILE"

cd "$TOOL_DIR" || exit
if [[ ! -e $OUTPUT_DIR ]]; then
  echo "Output folder $OUTPUT_DIR does not exist."
  exit 1
fi
$BENCHEXEC_SCRIPT $BENCHEXEC_OPTIONS "$BENCHMARK_DEFINITION_FILE" -o "$OUTPUT_DIR" --description-file "$TMP_FILE"
rm "$TMP_FILE"
#rm -rf "$TOOL_DIR"

echo ""
echo "  Initialize fileHashes for $TOOL"
cd "$OUTPUT_DIR" || exit
RESULT_ID=$(find . -maxdepth 1 -type f -name "$(basename "${BENCHMARK_DEFINITION_FILE%.xml}").????-??-??_??-??-??.results.*txt" | sort --reverse | sed -e "s#^\./##" -e "s/\.results\..*txt$//" | head -1)
RESULT_LOGS="$RESULT_ID.logfiles.zip"
RESULT_FILES="$RESULT_ID.files"
if [[ "$RESULT_ID" == "" ]]; then
  echo "    No results (txt) found."
elif [ -e "$RESULT_LOGS" ]; then
  if [ -e "$RESULT_FILES" ]; then
    echo "    Initialize fileHashes with verification tasks and result files in $RESULT_FILES."
  else
    echo "    No result files (witnesses) found but results (logs) found ($RESULT_LOGS); initialize fileHashes only with verification tasks."
    mkdir "$RESULT_FILES"
  fi
  ionice -c 3 nice "$SCRIPTS_DIR/initialize-store.sh" "$RESULT_FILES" "$WITNESS_TARGET" "$WITNESS_GLOB_SUFFIX"
else
  echo "    No results (logs) exist for $RESULT_ID."
fi

echo "  Execution done for $TOOL."
echo ""

