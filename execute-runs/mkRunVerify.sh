#!/bin/bash

# This file is part of the competition environment.
#
# SPDX-FileCopyrightText: 2011-2021 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# This is the main script to execute benchmarks; this execution phase has four steps:
# Step 1: Call execute-runcollection.sh to execute the tool (e.g., verification or test generation)
#         according to the given benchmark definition
# Step 2: Call execute-runcollection.sh to execute a number of result validators
#         (e.g., witness-based result validation or test-suite validation)
# Step 3: Call mkRunProcessLocal.sh to post-process the results
# Step 4: Call mkRunMailResults.sh to send results to participants

source contrib/configure.sh

NUMBER_JOBS_VALIDATORS=4
VERIFIER=$1;
BENCHMARKSCRIPT="../../benchexec/contrib/vcloud-benchmark.py";

if [[ $VERIFIER == "" ]]; then
  echo "Usage: $0 VERIFIER"
  exit
fi

echo "";
echo "($VERIFIER)  Run started";

DORUNVERIFICATION=${DORUNVERIFICATION:-"YES"};
DORUNVALIDATION=${DORUNVALIDATION:-"YES"};

if [[ "${DORUNVERIFICATION}" == "YES" ]]; then
  scripts/execute-runs/execute-runcollection.sh \
    "$BENCHMARKSCRIPT $OPTIONSVERIFY" "$VERIFIER" "$VERIFIER.xml" \
    "$WITNESSTARGET" "$WITNESSGLOBSUFFIX" "../../$RESULTSVERIFICATION/"
fi

pushd "$RESULTSVERIFICATION" || exit
RESULT_DIR=$(find . -maxdepth 1 -type d -name "$VERIFIER.????-??-??_??-??-??.files" | sort --reverse | sed -e "s#^\./##" | head -1)
if [ -e "$RESULT_DIR" ]; then
  echo "Results in $RESULT_DIR"
else
  echo "No result files found."
  #exit 1
fi
popd || exit

if [[ "${DORUNVALIDATION}" == "YES" ]]; then
  echo "";
  echo "Processing validation of $VERIFIER's results in $RESULT_DIR ...";
  VAL_COMMANDS=$(mktemp --suffix=-validation-runs.txt)
  for VALIDATORXMLTEMPLATE in $VALIDATORLIST; do
    VALIDATOR="${VALIDATORXMLTEMPLATE%-validate-*}"
    VAL="val_$VALIDATOR"
    echo "";
    echo "Running validation by $VALIDATOR ..."
    VALIDATORXML="${VALIDATORXMLTEMPLATE}-${VERIFIER}.xml";
    sed "s/LOGDIR/$RESULT_DIR/g" "$PATHPREFIX/$BENCHMARKSDIR/$VALIDATORXMLTEMPLATE.xml" > "$PATHPREFIX/$BENCHMARKSDIR/$VALIDATORXML"
    echo "";
    echo "Processing validation $VALIDATORXML ...";
    # Create a list of task-sets of the verifier, formatted such that it can be passed to BenchExec.
    RUNDEFS=$(xmlstarlet select --template --match '//*/tasks' \
	        --output '--tasks ' --value-of '@name' --nl "$BENCHMARKSDIR/$VERIFIER.xml" 2>/dev/null)
    if [[ "$RUNDEFS" =~ java ]]; then
      echo "No validation support for Java categories.";
      continue;
    fi
    COMMAND="$BENCHMARKSCRIPT $OPTIONSVALIDATE "$(echo $RUNDEFS)
    echo scripts/execute-runs/execute-runcollection.sh \
           \""$COMMAND"\" "$VAL" "$VALIDATORXML" \
           "$WITNESSTARGET" "$WITNESSGLOBSUFFIX" "../../$RESULTSVALIDATION/" \
           >> "$VAL_COMMANDS"
  done
  echo "All validation tasks created and ready to be executed.";
  echo "";
  cat "$VAL_COMMANDS" | parallel --linebuffer --jobs "$NUMBER_JOBS_VALIDATORS" {} {%} \|\& tee -a ./results-logs/"$VERIFIER"-{%}.log
  rm "$VAL_COMMANDS"
fi

date -Iseconds

# Process results
ionice -c 3 nice "$CONTRIB_DIR"/mkRunProcessLocal.sh "$VERIFIER";

# E-mail results
ionice -c 3 nice "$CONTRIB_DIR"/mkRunMailResults.sh "$VERIFIER" --really-send-email;

