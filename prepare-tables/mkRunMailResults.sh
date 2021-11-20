#!/bin/bash

# Assemble links for the e-mails and send result e-mails
# Uses the file 'mkRunMailResults-MailText.txt' as template mail text.

source $(dirname "$0")/configure.sh

VERIFIER=$1;

LETTERTEXT=$(cat ${PATHPREFIX}/contrib/mkRunMailResults-MailText.txt);

if [[ $VERIFIER == "" ]]; then
  exit;
fi

    echo "Sending e-mail for $VERIFIER";
    if [[ ! -e ${PATHPREFIX}/${BENCHMARKSDIR}/${VERIFIER}.xml ]]; then
      echo "No benchmark defintion found for verfier $VERIFIER.";
      continue;
    fi

    cd ${PATHPREFIX}/${RESULTSVERIFICATION};
    TMP_FILE_LETTERTEXT=$(mktemp --suffix=-lettertext.txt)
    echo "${LETTERTEXT}

HTML tables:
`ls ${VERIFIER}.results.${COMPETITION}.All.table.html.gz \
                   | sort --reverse | sed -e "s#^\./##" -e "s/^\(.*\)\.gz$/https:\/\/${TARGETSERVER}.sosy-lab.org\/${YEAR}\/results\/results-verified\/\1/"`
`find . -maxdepth 1 -type f -name "${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}_*.xml.bz2.table.html.gz" \
                   | sort --reverse | sed -e "s#^\./##" -e "s/^\(.*\)\.gz$/https:\/\/${TARGETSERVER}.sosy-lab.org\/${YEAR}\/results\/results-verified\/\1/"`

XML data:
`find . -maxdepth 1 -type f -name "${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}*.xml.bz2" \
                   | sort --reverse | sed -e "s#^\./##" -e "s/^\(.*\)$/https:\/\/${TARGETSERVER}.sosy-lab.org\/${YEAR}\/results\/results-verified\/\1/"`

Log archives:
`find . -maxdepth 1 -type d -name "${VERIFIER}.????-??-??_??-??-??.logfiles" \
                   | sort --reverse | sed -e "s#^\./##" -e "s/^\(.*\)$/https:\/\/${TARGETSERVER}.sosy-lab.org\/${YEAR}\/results\/results-verified\/\1.zip/"`
" > "$TMP_FILE_LETTERTEXT";

    ERROR=""
    find . -maxdepth 1 -name "${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}*.xml.bz2" \
      | sort | while read FILE; do
      RESULT="$($CONTRIB_DIR/mkRunCheckResults.sh "$(basename "$FILE")")"
      ERROR="${ERROR}${RESULT}"
    done
    cd ${PATHPREFIX}/${RESULTSVALIDATION};
    find . -maxdepth 1 -name "*-validate-*witnesses-${VERIFIER}.????-??-??_??-??-??.results.${COMPETITION}*.xml.bz2" \
      | sort | while read FILE; do
      #if [[ ! "$FILE" =~ "BitVector" ]]; then
      #  continue
      #fi
      RESULT="$($CONTRIB_DIR/mkRunCheckResults.sh "$(basename "$FILE")")"
      #echo $RESULT
      ERROR="${ERROR}${RESULT}"
    done
    if [ ! -z "$ERROR" ]; then
      ERROR="\n!!! This execution run FAILED for technical reasons and the *results are invalid*.\n    Please contact the organizer.\n\n"$ERROR
    fi

    MEMBER=$(yq --raw-output ".verifiers.\"$VERIFIER\".\"jury-member\".name" "$PATHPREFIX"/benchmark-defs/category-structure.yml)
    VERIFIERNAME=$(yq --raw-output ".verifiers.\"$VERIFIER\".name" "$PATHPREFIX"/benchmark-defs/category-structure.yml)
    echo "Looking up e-mail address for $MEMBER."
    EMAILENTRY=$(grep "$MEMBER" "$ADDRESS_BOOK")
    EMAIL=${EMAILENTRY%>*}
    EMAIL=${EMAIL#*<}
    if [ -z "$EMAIL" ]; then
      ERROR="E-mail address not found for $MEMBER."
    fi
    CMD="cat"
    if [ "$2" == "--really-send-email" ]; then
      CMD="sendmail -f dirk.beyer@sosy-lab.org dirk.beyer@sosy-lab.org $EMAIL"
    fi
    echo "Sending mail to $EMAIL ... with $CMD"

    cat "$TMP_FILE_LETTERTEXT" \
    | sed -e "s/___NAME___/$MEMBER/g" \
          -e "s/___EMAIL___/$EMAIL/g" \
          -e "s#___VERIFIER___#$VERIFIERNAME#g" \
          -e "s/___VERIFIERXML___/$VERIFIER.xml/g" \
          -e "s/___ERROR___/$ERROR/g" \
          -e "s/___COMPETITIONNAME___/$COMPETITIONNAME/g" \
          -e "s/___YEAR___/$YEAR/g" \
          -e "s/___TARGETSERVER___/$TARGETSERVER/g" \
          -e "s/___LIMITSTEXT___/$LIMITSTEXT/g" \
          -e "s/___RESULTSLEVEL___/$RESULTSLEVEL/g" \
    | $CMD
    rm "$TMP_FILE_LETTERTEXT"

