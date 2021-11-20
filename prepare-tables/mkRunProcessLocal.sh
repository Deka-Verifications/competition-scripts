#!/bin/bash

# @title Locally Process the Run Results
# @phase Run (Or Post Process)
# @description Creates the the nice HTML tables from the run results.
# First it collects the results xmls and merges them, and then calls BenchExec's table generator on it.
# Then it creates an HTML summarty page.
# It removes scores from the html, merge jsons, create files, replaces links to the files, compresses the html files.
# Finally, it calls mkRunWebCopy to copy the files to the server.

source $(dirname "$0")/configure.sh

NUMBERJOBS=6;
#NUMBERJOBS=1;
VERIFIER=$1;
if [[ $VERIFIER == "" ]]; then
  echo "Usage: $0 VERIFIER"
  exit;
fi

cd ${PATHPREFIX};
echo "================================================================================================";
date -Iseconds
echo "";
echo "Processing $VERIFIER";

if [[ "$COMPETITIONNAME" == "SV-COMP" ]]; then
  TABLETEMPLATE="./contrib/tableDefinition-single-svcomp.xml";
elif [[ "$COMPETITIONNAME" == "Test-Comp" ]]; then
  TABLETEMPLATE="./contrib/tableDefinition-single-testcomp.xml";
else
  echo "Unhandled competition name $COMPETITIONNAME"
  exit 1;
fi
HTMLFILESTOREPLACE="todoWitness-${VERIFIER}.txt";
rm -f $HTMLFILESTOREPLACE;
CATEGORIES=`grep "\.set" ${BENCHMARKSDIR}/${VERIFIER}.xml | grep "includesfile" | sed "s/.*\/\(.*\)\.set.*/\1/" | sort -u`
#CATEGORIES="ReachSafety-BitVectors";
for PROP in $PROPERTIES; do
 echo "";
 echo "  Property $PROP";
 for CAT in $CATEGORIES; do
  echo "";
  echo "  Category $CAT";
  FOUNDRESULTS=`find ${RESULTSVERIFICATION} -maxdepth 1 -name "${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${PROP}.${CAT}.xml.bz2"`
  if [ -n "$FOUNDRESULTS" ]; then
    FILEVERIFICATION=`ls -t ${RESULTSVERIFICATION}/${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${PROP}.${CAT}.xml.bz2 | head -1`;
    if bzcat "$FILEVERIFICATION" | xmlstarlet sel -t --if '/result/run' --output good --nl 2>/dev/null | grep -q "good"; then
      echo "      $FILEVERIFICATION";
    else
      echo "Empty results file found for this property and category ($PROP, $CAT).";
      continue;
    fi
  else
    echo "No results found for this property and category ($PROP, $CAT).";
    continue;
  fi
  VALIDATIONFILES="tableFiles_${VERIFIER}.txt";
  rm -f ${VALIDATIONFILES};
  touch ${VALIDATIONFILES};
  for VALIDATION in $VALIDATORLIST; do
    VALIDATOR=${VALIDATION%-validate-*};
    VAL="val_$VALIDATOR"
    FOUNDRESULTS=`find ${RESULTSVALIDATION} -maxdepth 1 -name "${VALIDATION}-${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${PROP}.${CAT}.xml.bz2"`
    if [ -n "$FOUNDRESULTS" ]; then
      FILEVALIDATIONCURR=`ls -t ${RESULTSVALIDATION}/${VALIDATION}-${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${PROP}.${CAT}.xml.bz2 | head -1`;
      # TODO  check invariant: validation run is newer than the verification run,
      #       otherwise hard fail (see https://gitlab.com/sosy-lab/sv-comp/archives-2021/-/issues/37)
      #       Example date string extraction: mkRunQueueFill.sh
      echo "      $FILEVALIDATIONCURR";
      if [ -e "$FILEVALIDATIONCURR" ]; then
        echo "$FILEVALIDATIONCURR " >> ${VALIDATIONFILES};
      fi
    fi
  done
  if [[ "${PROP}" =~ "java"  ||  "${PROP}" =~ "no-data-race" ]]; then
    echo "    We do not yet overwrite the result status for NoDataRace and Java categories.";
  else
    echo "    Merging";
    OPTIONS="";
    if [[ "$COMPETITION" =~ "SV-COMP" && `echo $CAT | egrep "(-Arrays|-Floats|-Heap|MemSafety|NoDataRace|ConcurrencySafety-|Termination-|-Java)" | wc -l` > 0 ]]; then
      OPTIONS="--no-overwrite-status-true";
    fi
    nice python3 benchexec/contrib/mergeBenchmarkSets.py $FILEVERIFICATION `cat $VALIDATIONFILES` $OPTIONS;
  fi
  FILERESULT=`ls -t ${RESULTSVERIFICATION}/${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${PROP}.${CAT}*.xml.bz2 | head -1`;
  RUNDEFNAME=`echo $FILERESULT | sed "s/.*\.results\.\(${COMPETITION}_${PROP}\)\.${CAT}.*/\1/"`
  echo "    Run-definition name: $RUNDEFNAME";
  TABLEDEF="tableDefinition-single-$VERIFIER-${CAT}.xml";
  cat ${TABLETEMPLATE} | grep -v "</table>" | grep -v "<column" > ${TABLEDEF};
  echo '  <result filename="'$FILERESULT'">'  >> ${TABLEDEF};
  cat ${TABLETEMPLATE} | grep '\<column' | grep -v '_covered' | grep -v 'branches_plot' \
      | sed -e "s/___RUNDEFNAME___/${RUNDEFNAME}/" >> ${TABLEDEF};
  echo '  </result>' >> ${TABLEDEF};
  for FILEVALIDATION in `cat $VALIDATIONFILES`; do
    echo '  <result filename="'$FILEVALIDATION'">' >> ${TABLEDEF};
    cat ${TABLETEMPLATE} | grep "<column" | grep -v "score" \
        | sed -e "s/___RUNDEFNAME___/${RUNDEFNAME}/" >> ${TABLEDEF};
    echo '  </result>' >> ${TABLEDEF};
  done
  echo '</table>' >> ${TABLEDEF};
  "$BENCHEXEC_PATH"/bin/table-generator -o ./${RESULTSVERIFICATION} --no-diff --format html \
                                         --name ${FILERESULT//*\//} \
                                         -x ${TABLEDEF} \
                                         |& grep -v "\(No result for task\)\|\(A variable was not replaced in\)";
  rm ${VALIDATIONFILES};
  rm ${TABLEDEF};
  echo "Removing score row from table ...";
  "$PATHPREFIX"/contrib/mkRunProcessLocal-RemoveScoreStats.py --insitu ${FILERESULT}.table.html
  # Remember to replace the links in the tables
  echo "${FILERESULT}.table.html" >> ${HTMLFILESTOREPLACE};
  date -Iseconds;
 done # for category
done # for properties
echo "";

echo "Generating overall table ...";
TABLEDEFALL="tableDefinition-single-$VERIFIER-All.xml";
cat ${TABLETEMPLATE} | grep -v "</table>" | grep -v "<column" > ${TABLEDEFALL};

echo "<!-- Verifier $VERIFIER -->" >> $TABLEDEFALL
echo "<union title=\"$VERIFIER ...\">" >> $TABLEDEFALL
cat ${TABLETEMPLATE} | grep '\<column' | grep -v '_covered' \
    | grep -v "___RUNDEFNAME___" >> ${TABLEDEFALL};
for PROP in $PROPERTIES; do
 echo "";
 echo "  Property $PROP";
 for CAT in $CATEGORIES; do
  echo "  Category $CAT";
  FOUNDRESULTS=`find ${RESULTSVERIFICATION} -maxdepth 1 -name "${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${PROP}.${CAT}*.xml.bz2"`
  if [ -n "$FOUNDRESULTS" ]; then
    FILERESULT=`ls -t ${RESULTSVERIFICATION}/${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${PROP}.${CAT}*.xml.bz2 | head -1`;
    if [ -e "$FILERESULT" ]; then
      if bzcat "$FILERESULT" | xmlstarlet sel -t --if '/result/run' --output good --nl 2>/dev/null | grep -q "good"; then
        echo "      $FILERESULT";
        echo '    <result filename="'$FILERESULT'"/>'  >> $TABLEDEFALL;
      else
        echo "Empty results file found for this property and category ($PROP, $CAT).";
      fi
    fi
  else
    echo "No verification results found for verifier $VERIFIER, property $PROP, and category $CAT";
  fi
 done
done
echo "</union>" >> $TABLEDEFALL;

for VALIDATION in $VALIDATORLIST; do
  VALIDATOR=${VALIDATION%-validate-*};
  VAL="val_$VALIDATOR"
  echo "Processing $VALIDATION ...";
  echo "<!-- Validator $VALIDATION -->" >> $TABLEDEFALL
  echo "<union title=\"$VALIDATION ...\">" >> $TABLEDEFALL
  cat ${TABLETEMPLATE} | grep "<column" | grep -v "score" \
      | grep -v "___RUNDEFNAME___" >> ${TABLEDEFALL};
  for PROP in $PROPERTIES; do
    echo "";
    echo "  Property $PROP";
    for CAT in $CATEGORIES; do
      echo "    Category $CAT";
      FOUNDRESULTS=`find ${RESULTSVALIDATION} -maxdepth 1 -name "${VALIDATION}-${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${PROP}.${CAT}.xml.bz2"`
      if [ -n "$FOUNDRESULTS" ]; then
        FILEVALIDATION=`ls -t ${RESULTSVALIDATION}/${VALIDATION}-${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${PROP}.${CAT}.xml.bz2 | head -1`;
        if [ -n "$FILEVALIDATION" ]; then
          if bzcat "$FILEVALIDATION" | xmlstarlet sel -t --if '/result/run' --output good --nl 2>/dev/null | grep -q "good"; then
            echo "   <result filename='$FILEVALIDATION'/>" >> $TABLEDEFALL;
          else
            echo "Validation: Empty results file found for this property and category ($PROP, $CAT).";
          fi
        fi
      fi
    done
  done
  echo "</union>" >> $TABLEDEFALL
done
echo "</table>" >> $TABLEDEFALL
OUTFILE="${VERIFIER}.results.${COMPETITION}.All";
"$BENCHEXEC_PATH"/bin/table-generator -o ./${RESULTSVERIFICATION} --no-diff --format html \
                                       --name ${OUTFILE} \
                                       -x ${TABLEDEFALL} \
                                       |& grep -v "\(No result for task\)\|\(A variable was not replaced in\)";
rm ${TABLEDEFALL};
echo "Removing score row from table ...";
"$PATHPREFIX"/contrib/mkRunProcessLocal-RemoveScoreStats.py --insitu ${RESULTSVERIFICATION}/${OUTFILE}.table.html
# Remember to replace the links in the tables
echo "${RESULTSVERIFICATION}/${OUTFILE}.table.html" >> ${HTMLFILESTOREPLACE};
date -Iseconds;

# We need a unique name because of concurrency - use a temporary file.
ALL_HASHES=$(mktemp --suffix=-comp.json)
# For verification results
WITNESS_VERIFIER_HASHES=`ls -dt ${RESULTSVERIFICATION}/${VERIFIER}.????-??-??_??-??-??.$HASHES_BASENAME | head -1`;
echo "Merging hashes maps (${WITNESS_VERIFIER_HASHES}) ..."
nice "$PATHPREFIX"/contrib/mkRunProcessLocal-MergeJsons.py \
    --output "$ALL_HASHES" \
    "$WITNESS_VERIFIER_HASHES"
date -Iseconds;
# For validation results
for VALIDATION in $VALIDATORLIST; do
  VALIDATOR=${VALIDATION%-validate-*};
  VAL="val_$VALIDATOR"
  echo "Processing $VALIDATION ...";
  FOUNDRESULTS=`find ${RESULTSVALIDATION} -maxdepth 1 -name ${VALIDATION}-${VERIFIER}.????-??-??_??-??-??.$HASHES_BASENAME`
  if [ -n "$FOUNDRESULTS" ]; then
    WITNESS_VALIDATOR_HASHES=`ls -dt ${RESULTSVALIDATION}/${VALIDATION}-${VERIFIER}.????-??-??_??-??-??.$HASHES_BASENAME | head -1`;
    echo "Merging hashes maps (${WITNESS_VALIDATOR_HASHES}) ..."
    nice "$PATHPREFIX"/contrib/mkRunProcessLocal-MergeJsons.py \
        --output "$ALL_HASHES" \
        "$ALL_HASHES" "$WITNESS_VALIDATOR_HASHES"
    date -Iseconds;
  fi
done
echo "Creating file store ..."
nice "$PATHPREFIX"/contrib/mkRunProcessLocal-CreateFileStore.py \
    --output "$HASHDIR_BASENAME" \
    --root-dir "$PATHPREFIX" \
    "$ALL_HASHES"
date -Iseconds;


echo "Replacing witness links ..."
contrib/mkRunProcessLocal-ReplaceLinks.py --no-plots $(cat "$HTMLFILESTOREPLACE") --hashmap "$ALL_HASHES" --file-store-url-prefix "${FILE_STORE_URL_PREFIX}"
date -Iseconds;

echo "Compressing HTML tables ...";
for FILE in `cat ${HTMLFILESTOREPLACE}`; do
  gzip -9 --force $FILE;
done
date -Iseconds;
rm ${HTMLFILESTOREPLACE};
rm ${ALL_HASHES};


echo "Generating list of HTML pages ...";
echo "<html><body>" > ${HTMLOVERVIEW};
# Run according to category structure.
for VERIFIERCURR in $(yq --raw-output '.verifiers | keys []' benchmark-defs/category-structure.yml); do
      VERIFIERXML="${VERIFIERCURR}.xml";
      echo Processing $VERIFIERCURR starting at `date --rfc-3339=seconds`;
      cd ${PATHPREFIX};
      if [ ! -e ${BENCHMARKSDIR}/${VERIFIERXML} ]; then
        echo "File ${BENCHMARKSDIR}/${VERIFIERXML} not found."
        continue
      fi
      CATEGORIES=`grep "\.set" ${BENCHMARKSDIR}/${VERIFIERXML} | sed "s/.*\/\(.*\)\.set.*/\1/"`
      echo "<h3>$VERIFIERCURR</h3>" >> ${HTMLOVERVIEW};
      cd ${PATHPREFIX}/${RESULTSVERIFICATION};
      FOUNDRESULTS=`find . -maxdepth 1 -name "${VERIFIERCURR}.results.${COMPETITION}.All.table.html.gz"`
      if [ -n "$FOUNDRESULTS" ]; then
        LINK=`ls -t ${VERIFIERCURR}.results.${COMPETITION}.All.table.html.gz | head -1`;
        if [ -e "$LINK" ]; then
          echo "<a href=\"${LINK%\.gz}#/table\">${LINK%\.gz}</a>" >> ${HTMLOVERVIEW};
          echo "<br/>" >> ${HTMLOVERVIEW};
        fi
      fi
      for PROP in $PROPERTIES; do
       echo "";
       echo "  Property $PROP";
       for i in $CATEGORIES; do
        FOUNDRESULTS=`find . -maxdepth 1 -name "${VERIFIERCURR}.????-??-??_??-??-??.results.${COMPETITION}_${PROP}.$i*.html.gz"`
        if [ -n "$FOUNDRESULTS" ]; then
          LINK=`ls -t ${VERIFIERCURR}.????-??-??_??-??-??.results.${COMPETITION}_${PROP}.$i*.html.gz | head -1`;
          if [ -e "$LINK" ]; then
            echo "<a href=\"${LINK%\.gz}#/table\">${LINK%\.gz}</a>" >> ${HTMLOVERVIEW};
            echo "<br/>" >> ${HTMLOVERVIEW};
	  fi
	fi
       done # for category
      done # for property
    done # while verifier
echo "</body></html>" >> ${HTMLOVERVIEW};




