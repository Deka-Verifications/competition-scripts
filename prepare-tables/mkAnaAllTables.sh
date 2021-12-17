#!/bin/bash

source $(dirname "$0")/configure.sh
source $(dirname "$0")/mkAnaAllTables-Config.sh
HTMLOVERVIEW="overview.html";

COLUMNSSINGLE='
<column title="status"/>
<column title="score" displayTitle="raw score"/>
<column title="cputime"   numberOfDigits="2" displayTitle="cpu"/>
<column title="memory"  numberOfDigits="2" displayTitle="mem"    displayUnit="MB" sourceUnit="B"/>
<column title="cpuenergy" numberOfDigits="2" displayTitle="energy" displayUnit="J"  sourceUnit="J"/>
';
COLUMNSMETA='
<column title="status"/>
<column title="score" displayTitle="raw score"/>
<column title="cputime"   numberOfDigits="2" displayTitle="cpu"/>
<column title="memory"  numberOfDigits="2" displayTitle="mem"    displayUnit="MB" sourceUnit="B"/>
<column title="cpuenergy" numberOfDigits="2" displayTitle="energy" displayUnit="J"  sourceUnit="J"/>
';

cd ${PATHPREFIX}/${RESULTSVERIFICATION}

# Generate overview HTML page
echo "<html><body>" > ${HTMLOVERVIEW};


DOCREATESINGLECATEGORY="YES";

# Single Categories
if [[ "${DOCREATESINGLECATEGORY}" == "YES" ]]; then
  for CAT in ${CATEGORIES}; do
    if [[ ! "$CAT" =~ "-" ]]; then
      continue;
    fi
    OUTPUT_FILE=$CAT.xml
    echo "<?xml version='1.0' ?>" > $OUTPUT_FILE
    echo "<table>${COLUMNSSINGLE}" >> $OUTPUT_FILE
    for VERIFIER in ${VERIFIERS}; do
      FOUNDRESULTS=`find . -maxdepth 1 -name "${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${CAT}*.xml.bz2"`
      if [ -n "$FOUNDRESULTS" ]; then
          RESULT=`ls -t ${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${CAT}*.xml.bz2 2>/dev/null | head -1`;
          echo "<result filename='$RESULT'/>" >> $OUTPUT_FILE
      fi
    done
    echo "</table>" >> $OUTPUT_FILE
    echo "table-generator --no-diff --format html -x $OUTPUT_FILE"
    "$BENCHEXEC_PATH"/bin/table-generator --no-diff --format html -x $OUTPUT_FILE
    rm $OUTPUT_FILE
    echo "Removing score row from table ...";
    "$PATHPREFIX"/contrib/mkRunProcessLocal-RemoveScoreStats.py --insitu ${OUTPUT_FILE//.xml/.table.html};
    gzip -9 --force ${OUTPUT_FILE//.xml/.table.html};
    echo "<a href=\"${OUTPUT_FILE//.xml/.table.html}\">${OUTPUT_FILE//.xml/.table.html}</a> <br />" >> ${HTMLOVERVIEW};
  done
fi

# Unioned Categories
for LINE in "${VERIFIERSLIST[@]}"; do
  METACAT=`echo $LINE | cut -d ':' -f 1`;
  echo "Processing meta category $METACAT";
  VERIFIERS=`echo $LINE | cut -d ':' -f 2`;
  OUTPUT_FILE="META_${METACAT}.xml";
  echo "<?xml version='1.0' ?>" > $OUTPUT_FILE
  echo "<table>${COLUMNSMETA}" >> $OUTPUT_FILE
  for VERIFIER in $VERIFIERS; do
    echo "    $VERIFIER";
    echo "  <union>" >> $OUTPUT_FILE
    for CATLINE in "${CATEGORIESLIST[@]}"; do
      META=`echo $CATLINE | cut -d ':' -f 1`;
      if [[ $META != $METACAT ]]; then
        continue;
      fi
      CATS=`echo $CATLINE | cut -d ':' -f 2`;
      for CAT in $CATS; do
        if [[ ! "$CAT" =~ "-" ]]; then
          continue;
        fi
        echo "        $CAT";
        FOUNDRESULTS=`find . -maxdepth 1 -name "${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${CAT}*.xml.bz2"`
        if [ -n "$FOUNDRESULTS" ]; then
          RESULT=`ls -t ${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${CAT}*.xml.bz2 2>/dev/null | head -1`;
          echo "    <result filename='$RESULT'/>" >> $OUTPUT_FILE
        else
          echo "Result for ${VERIFIER} and ${COMPETITION}.${CAT} not found."
        fi
      done
      # Generate a table for meta category per verifier.
      OUT_META_VER=META_${METACAT}_${VERIFIER}.xml
      echo "<?xml version='1.0' ?>" > $OUT_META_VER
      echo "<table>${COLUMNSMETA}" >> $OUT_META_VER
      echo "  <union>" >> $OUT_META_VER
      for CAT in $CATS; do
        if [[ ! "$CAT" =~ "-" ]]; then
          continue;
        fi
        echo "           Meta-Category $META -- $CAT";
        FOUNDRESULTS=`find . -maxdepth 1 -name "${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${CAT}*.xml.bz2"`
        if [ -n "$FOUNDRESULTS" ]; then
          FILERESULT=`ls -t ${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_${CAT}*.xml.bz2 | head -1`;
          echo "    <result filename='$FILERESULT'/>"  >> $OUT_META_VER;
        fi
      done
      echo "  </union>" >> $OUT_META_VER;
      echo "</table>" >> ${OUT_META_VER};
      echo table-generator --no-diff --format html -x ${OUT_META_VER}
      "$BENCHEXEC_PATH"/bin/table-generator --no-diff --format html -x ${OUT_META_VER}
      rm $OUT_META_VER
      echo "Removing score row from table ...";
      "$PATHPREFIX"/contrib/mkRunProcessLocal-RemoveScoreStats.py --insitu ${OUT_META_VER//.xml/.table.html}
      gzip -9 --force ${OUT_META_VER//.xml/.table.html};
      echo "<a href=\"${OUT_META_VER//.xml/.table.html}\">${OUT_META_VER//.xml/.table.html}</a> <br />" >> ${HTMLOVERVIEW};
    done
    echo "  </union>" >> $OUTPUT_FILE
  done
  echo "</table>" >> $OUTPUT_FILE
  echo "table-generator --no-diff --format html -x $OUTPUT_FILE"
  "$BENCHEXEC_PATH"/bin/table-generator --no-diff --format html -x $OUTPUT_FILE
  rm $OUTPUT_FILE
  echo "Removing score row from table ...";
  "$PATHPREFIX"/contrib/mkRunProcessLocal-RemoveScoreStats.py --insitu ${OUTPUT_FILE//.xml/.table.html}
  gzip -9 --force ${OUTPUT_FILE//.xml/.table.html};
  echo "<a href=\"${OUTPUT_FILE//.xml/.table.html}\">${OUTPUT_FILE//.xml/.table.html}</a> <br />" >> ${HTMLOVERVIEW};
done

echo "</body></html>" >> ${HTMLOVERVIEW};

# Copy to web server
cd ${PATHPREFIX}
source $(dirname "$0")/mkRunWebCopy.sh

