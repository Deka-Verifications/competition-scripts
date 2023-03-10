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
# Step 4: Call mkRunWebCopy.sh to copy the results to the web server and backup drive
# Step 5: Call mkRunMailResults.sh to send results to participants

source "$(dirname "$0")"/../configure.sh

NUMBER_JOBS_VALIDATORS=4
VERIFIER=$1;
BENCHMARKSCRIPT="$(dirname "$0")/../../benchexec/contrib/vcloud-benchmark.py";

if [[ $VERIFIER == "" ]]; then
  echo "Usage: $0 VERIFIER"
  exit
fi

echo "";
echo "($VERIFIER)  Run started";

DORUNVERIFICATION=${DORUNVERIFICATION:-"YES"};
DORUNVALIDATION=${DORUNVALIDATION:-"YES"};

if [[ "$ACTIONS" =~ "PRODUCE_RESULTS" ]]; then
  # To limit benchmark to a single task-set, uncomment the next line.
  # OPTIONSVERIFY="$OPTIONSVERIFY --tasks ReachSafety-ControlFlow"
  "$SCRIPT_DIR"/execute-runs/execute-runcollection.sh \
	  "$BENCHMARKSCRIPT" "$(dirname "$0")/../../archives/$YEAR/$VERIFIER.zip" "$(dirname "$0")/../../benchmark-defs/$VERIFIER.xml" \
	  "$WITNESSTARGET" "$WITNESSGLOBSUFFIX" "$(dirname "$0")/../../$RESULTSVERIFICATION/" "$OPTIONSVERIFY"
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

if [[ "$ACTIONS" =~ "VALIDATE_RESULTS" ]]; then
  echo "";
  echo "Processing validation of $VERIFIER's results in $RESULT_DIR ...";
  VAL_COMMANDS=$(mktemp --suffix=-validation-runs.txt)
  for VALIDATORXMLTEMPLATE in $VALIDATORLIST; do
    VALIDATOR="${VALIDATORXMLTEMPLATE%-validate-*}"
    echo "";
    echo "Running validation by $VALIDATOR ..."
    VALIDATORXML="$(dirname "$0")/../../benchmark-defs/${VALIDATORXMLTEMPLATE}-${VERIFIER}.xml";
    sed "s/LOGDIR/$RESULT_DIR/g" "$PATHPREFIX/$BENCHMARKSDIR/$VALIDATORXMLTEMPLATE.xml" > "$VALIDATORXML"
    if [[ "$VALIDATOR" == "witnesslint"  &&  "$(yq -r ".verifiers.\"$VERIFIER\".\"jury-member\".name" benchmark-defs/category-structure.yml)" == "Hors Concours" ]]; then
      echo "Witness-linter call for hors-concours participation:"
      echo "Insert option into benchmark definition for witnesslint to not perform recent checks on hors-concours participants."
      VALIDATORBENCHDEF=$(cat "$VALIDATORXML")
      echo "$VALIDATORBENCHDEF" \
	| xmlstarlet edit --append '/benchmark/option[@name="--ignoreSelfLoops"]' --type elem -n 'option' --insert '/benchmark/option[not(@name)]' --type attr -n 'name' --value '--excludeRecentChecks' \
        > "$VALIDATORXML"
    fi
    echo "";
    echo "Processing validation $VALIDATORXML ...";
    # Create a list of task-sets of the verifier, formatted such that it can be passed to BenchExec.
    RUNDEFS=$(xmlstarlet select --template --match '//*/tasks' \
	        --output '--tasks ' --value-of '@name' --nl "$BENCHMARKSDIR/$VERIFIER.xml" 2>/dev/null)
    if [[ "$RUNDEFS" =~ java ]]; then
      echo "No validation support for Java categories.";
      continue;
    fi
    echo "$SCRIPT_DIR"/execute-runs/execute-runcollection.sh \
	    "$BENCHMARKSCRIPT" "$(dirname "$0")/../../archives/$YEAR/val_$VALIDATOR.zip" "$VALIDATORXML" \
	    "$WITNESSTARGET" "$WITNESSGLOBSUFFIX" "$(dirname "$0")/../../$RESULTSVALIDATION/" "$OPTIONSVALIDATE" $(echo $RUNDEFS) \
	    >> "$VAL_COMMANDS"
  done
  echo "All validation tasks created and ready to be executed.";
  echo "";
  cat "$VAL_COMMANDS" | parallel --linebuffer --jobs "$NUMBER_JOBS_VALIDATORS" {} \|\& tee -a ./results-logs/"$VERIFIER"-{%}.log
  rm "$VAL_COMMANDS"
fi

date -Iseconds

if [[ "$ACTIONS" =~ "PREPARE_RESULTS" ]]; then
  # Process results and create HTML tables
  ionice -c 3 nice "$SCRIPT_DIR"/prepare-tables/mkRunProcessLocal.sh "$VERIFIER";
fi

if [[ "$ACTIONS" =~ "PUBLISH_RESULTS" ]]; then
  # Copy results
  ionice -c 3 nice "$SCRIPT_DIR"/prepare-tables/mkRunWebCopy.sh "$VERIFIER"
fi

if [[ "$ACTIONS" =~ "SEND_RESULTS" ]]; then
  # E-mail results
  ionice -c 3 nice "$SCRIPT_DIR"/prepare-tables/mkRunMailResults.sh "$VERIFIER" --really-send-email;
fi

