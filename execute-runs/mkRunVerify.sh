#!/bin/bash

# @title Run the Verification of Benchmarks
# @phase Run
# @description The main script to execute the benchmarks.
# It has 4 steps: Run verifier, run validator, processing results, and sending mails.
# Step 1:  At first installs the verifier using make,
#  then runs the benchmark from the benchmark definition using BenchExec, then initialzes the file store on the results director.
# Step 2: Same as Step 1 but for the chosen validators.
# Step 3: Process results using mkRunProcessLocal
# Step 4: Send mails using mkRunMailResults.
# TODO: I still don't understand the sourcing of "mkRunWitnessStore" after in the "ALL" case.

source $(dirname "$0")/configure.sh

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

pushd "$RESULTSVERIFICATION"
RESULT_DIR=`ls -dt ${VERIFIER}.????-??-??_??-??-??.files | head -1`
if [ -e "$RESULT_DIR" ]; then
  echo "Results in $RESULT_DIR"
else
  echo "No results found."
  exit 1
fi
popd

if [[ "${DORUNVALIDATION}" == "YES" ]]; then
  echo "";
  echo "Processing validation of $VERIFIER's results in $RESULT_DIR ...";
  VAL_COMMANDS=$(mktemp --suffix=-validation-runs.txt)
  for VALIDATORXMLTEMPLATE in $VALIDATORLIST; do
    VALIDATOR=${VALIDATORXMLTEMPLATE%-validate-*};
    VAL="val_$VALIDATOR"
    echo "";
    echo "Running validation by $VALIDATOR ..."
    VALIDATORXML="${VALIDATORXMLTEMPLATE}-${VERIFIER}.xml";
    sed "s/LOGDIR/${RESULT_DIR}/g" ${PATHPREFIX}/${BENCHMARKSDIR}/${VALIDATORXMLTEMPLATE}.xml > ${PATHPREFIX}/${BENCHMARKSDIR}/${VALIDATORXML}
    echo "";
    echo "Processing validation $VALIDATORXML ...";
    RUNDEFS=`grep "<rundefinition" ${BENCHMARKSDIR}/${VERIFIER}.xml \
             | grep -v "<!--" \
             | sed "s/<rundefinition name=\"\(.*\)\">/-r \1 /"`;
    if [[ "${RUNDEFS}" =~ java ]]; then
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
  cat "$VAL_COMMANDS" | parallel --linebuffer --jobs "$NUMBER_JOBS_VALIDATORS" {} {%} \|\& tee -a ./results-logs/$VERIFIER-{%}.log
  rm "$VAL_COMMANDS"
fi

date -Iseconds

# Process results
ionice -c 3 nice ${CONTRIB_DIR}/mkRunProcessLocal.sh $VERIFIER;

# E-mail results
ionice -c 3 nice ${CONTRIB_DIR}/mkRunMailResults.sh $VERIFIER --really-send-email;

