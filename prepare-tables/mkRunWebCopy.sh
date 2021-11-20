# Copy the results to web server and to backup drive

source $(dirname "$0")/configure.sh

VERIFIER=$1;
if [[ "$VERIFIER" == "" ]]; then
  echo "Usage: $0 VERIFIER"
  exit;
fi

cd "$PATHPREFIX"

#echo "Validator statistics ...";
#./contrib/mkValidatorStatistics.py --category-structure benchmark-defs/category-structure.yml --htmlfile ${PATHPREFIX}/${RESULTSVERIFICATION}/validatorStatistics.html
#gzip -9 --force ${PATHPREFIX}/${RESULTSVERIFICATION}/validatorStatistics.html

echo "Copy to web server ..."
echo "... $RESULTSVERIFICATION"
SOURCE="$PATHPREFIX/$RESULTSVERIFICATION/"
TARGET="www-comp.sosy.ifi.lmu.de:/srv/web/data/$TARGETDIR/$YEAR/results/$RESULTSVERIFICATION/"
if ! ls -dt "$RESULTSVERIFICATION/$VERIFIER".????-??-??_??-??-??.logfiles.zip &> /dev/null; then
  echo "No results for $VERIFIER."
  exit
fi
RESULT_DIR=$(ls -dt "$RESULTSVERIFICATION/$VERIFIER".????-??-??_??-??-??.logfiles.zip | head -1)
RESULT_DIR="${RESULT_DIR%.logfiles.zip}"
RESULT_DIR="${RESULT_DIR#*/}"
echo "Results: $RESULT_DIR"
rsync -axzq "$HTMLOVERVIEW" "$TARGET"
rsync -axzq "$RESULTSVERIFICATION/$VERIFIER.results.$COMPETITION.All.table.html.gz" "$TARGET"
rsync -axzq --dirs --no-recursive --include="$RESULT_DIR.*.html.gz" --exclude="*" "$SOURCE" "$TARGET"
rsync -axzq --dirs --no-recursive --include="$RESULT_DIR.*.xml.bz2" --exclude="*" "$SOURCE" "$TARGET"
rsync -axzq --dirs --no-recursive --include="$RESULT_DIR.*.zip"     --exclude="*" "$SOURCE" "$TARGET"
rsync -axzq --dirs --no-recursive --include="$RESULT_DIR.*.json"    --exclude="*" "$SOURCE" "$TARGET"

echo "... $RESULTSVALIDATION"
SOURCE="$PATHPREFIX/$RESULTSVALIDATION/"
TARGET="www-comp.sosy.ifi.lmu.de:/srv/web/data/$TARGETDIR/$YEAR/results/$RESULTSVALIDATION/"
for VALIDATION in $VALIDATORLIST; do
  if ! ls -dt1 "$RESULTSVALIDATION/${VALIDATION}-${VERIFIER}".????-??-??_??-??-??.logfiles.zip &> /dev/null; then
    echo "No results for ${VALIDATION}-${VERIFIER}."
    continue
  fi
  RESULT_DIR=$(ls -dt1 "$RESULTSVALIDATION/${VALIDATION}-${VERIFIER}".????-??-??_??-??-??.logfiles.zip | head -1)
  RESULT_DIR="${RESULT_DIR%.logfiles.zip}"
  RESULT_DIR="${RESULT_DIR#*/}"
  echo "Results: $RESULT_DIR"
  rsync -axzq --dirs --no-recursive --include="$RESULT_DIR.*.xml.bz2" --exclude="*" "$SOURCE" "$TARGET"
  rsync -axzq --dirs --no-recursive --include="$RESULT_DIR.*.zip"     --exclude="*" "$SOURCE" "$TARGET"
  rsync -axzq --dirs --no-recursive --include="$RESULT_DIR.*.json"    --exclude="*" "$SOURCE" "$TARGET"
done

echo "... backup to scratch"
rsync -a "www-comp:/srv/web/data/$TARGETDIR/$YEAR/" "/data/scratch/dbeyer/comp-data/$TARGETDIR/$YEAR/"
echo

