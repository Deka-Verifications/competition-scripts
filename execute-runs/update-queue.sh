#!/bin/bash

echo "----------------------------------------------"
echo "Pulling new archives."
pushd archives || exit
git pull --rebase
popd || exit

echo ""
echo "Add new jobs to the queue."
YEAR=$(yq --raw-output '.year' benchmark-defs/category-structure.yml)
for VERIFIER in archives/"$YEAR"/*.zip; do
  JOB=$(basename "${VERIFIER%.zip}")
  if [[ "$JOB" =~ "val_" ]]; then
    continue
  fi
  echo ""
  echo "Considering $JOB"
  RUNS=$(find results-verified/ -maxdepth 1 -name "$JOB.*.logfiles.zip")
  if [[ $RUNS != "" ]]; then
    # Look up the most recent run result.
    RESULT=$(ls -t $RUNS | head -1)
    RESULT_TIME=${RESULT##*$JOB.}
    RESULT_TIME=${RESULT_TIME%.logfiles.zip}
    ARCHIVE_TIME=$(date "+%Y-%m-%d_%H-%M-%S" --reference="$VERIFIER")
    echo "Time stamp of run-result: $RESULT_TIME"
    echo "Time stamp of archive:    $ARCHIVE_TIME"
    if [[ "$ARCHIVE_TIME" < "$RESULT_TIME" ]]; then
      echo "Job was already processed."
      continue
    fi
  fi
  # Add job only if it was not already considered before.
  if [[ -e "queue/$JOB"  ||  -e "queue/$JOB.wait"  ||  -e "queue/$JOB.running"  ||  -e "queue/$JOB.finished" ]] ; then
    echo "Not scheduled $JOB"
    continue
  fi
  echo "Scheduling $JOB"
  touch --reference="$VERIFIER" "queue/$JOB"
done
