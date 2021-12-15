#!/bin/bash

# Copy the results to web server and to backup drive

source $(dirname "$0")/../configure.sh

VERIFIER=$1;
if [[ "$VERIFIER" == "" ]]; then
  echo "Usage: $0 VERIFIER"
  exit;
fi

cd "$PATHPREFIX"

#echo "Validator statistics ...";
#./contrib/mkValidatorStatistics.py --category-structure benchmark-defs/category-structure.yml --htmlfile ${PATHPREFIX}/${RESULTSVERIFICATION}/validatorStatistics.html
#gzip -9 --force ${PATHPREFIX}/${RESULTSVERIFICATION}/validatorStatistics.html

echo "Copy results for $VERIFIER to web server ..."
echo "... $RESULTSVERIFICATION"
SOURCE="$PATHPREFIX/$RESULTSVERIFICATION/"
TARGET="www-comp.sosy.ifi.lmu.de:/srv/web/data/$TARGETDIR/$YEAR/results/$RESULTSVERIFICATION/"
RESULT_ID=$(find "$RESULTSVERIFICATION" -maxdepth 1 -type f -name "$VERIFIER.????-??-??_??-??-??.results.*txt" | sort --reverse | sed -e "s#^.*/##" -e "s/\.results\..*txt$//" | head -1)
if [[ "$RESULT_ID" == "" ]]; then
  echo "    No results (txt) found for $VERIFIER."
  echo
  exit
fi
echo "Results: $RESULT_ID"
rsync -axzq "$HTMLOVERVIEW" "$TARGET"
rsync -axzq "$RESULTSVERIFICATION/$VERIFIER.results.$COMPETITION.All.table.html.gz" "$TARGET"
rsync -axzq --dirs --no-recursive --include="$RESULT_ID.*.html.gz" --exclude="*" "$SOURCE" "$TARGET"
rsync -axzq --dirs --no-recursive --include="$RESULT_ID.*.xml.bz2" --exclude="*" "$SOURCE" "$TARGET"
rsync -axzq --dirs --no-recursive --include="$RESULT_ID.*.zip"     --exclude="*" "$SOURCE" "$TARGET"
rsync -axzq --dirs --no-recursive --include="$RESULT_ID.*.txt"     --exclude="*" "$SOURCE" "$TARGET"
rsync -axzq --dirs --no-recursive --include="$RESULT_ID.*.json"    --exclude="*" "$SOURCE" "$TARGET"

echo "... $RESULTSVALIDATION"
SOURCE="$PATHPREFIX/$RESULTSVALIDATION/"
TARGET="www-comp.sosy.ifi.lmu.de:/srv/web/data/$TARGETDIR/$YEAR/results/$RESULTSVALIDATION/"
for VALIDATION in $VALIDATORLIST; do
  RESULT_ID=$(find "$RESULTSVALIDATION" -maxdepth 1 -type f -name "$VALIDATION-$VERIFIER.????-??-??_??-??-??.results.*txt" | sort --reverse | sed -e "s#^.*/##" -e "s/\.results\..*txt$//" | head -1)
  if [[ "$RESULT_ID" == "" ]]; then
    echo "    No results (txt) found for $VALIDATION-$VERIFIER."
    continue
  fi
  echo "Results: $RESULT_ID"
  rsync -axzq --dirs --no-recursive --include="$RESULT_ID.*.xml.bz2" --exclude="*" "$SOURCE" "$TARGET"
  rsync -axzq --dirs --no-recursive --include="$RESULT_ID.*.zip"     --exclude="*" "$SOURCE" "$TARGET"
  rsync -axzq --dirs --no-recursive --include="$RESULT_ID.*.txt"     --exclude="*" "$SOURCE" "$TARGET"
  rsync -axzq --dirs --no-recursive --include="$RESULT_ID.*.json"    --exclude="*" "$SOURCE" "$TARGET"
done

echo "... backup to scratch"
rsync -a "www-comp:/srv/web/data/$TARGETDIR/$YEAR/" "/data/scratch/dbeyer/comp-data/$TARGETDIR/$YEAR/"
echo

