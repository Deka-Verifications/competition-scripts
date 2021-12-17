#!/bin/bash

# @title Competition Website: Participating Teams
# @phase Web
# @description creates the table of participating teams for the competition website. Data is fetched from the google sheets. 

source $(dirname "$0")/configure.sh

echo "<!-- This file is generated. Do not edit manually. -->
<?php require('../template.php'); pageHeader(); ?>

<h2>Reproducing ${COMPETITIONNAME} Results</h2>

<p>
A description on how we make the results of the competition reproducible
can be found in the 
<a href=\"https://www.sosy-lab.org/~dbeyer/Publications/2017-TACAS.Software_Verification_with_Validation_of_Results.pdf\">competition report</a>;
the components that are listed below in the table are described in Sect. 4 \"Reproducibility\".
</p>

<table>
  <tr style='font-weight: bold;'>
    <td>Tool</td>
    <td>Lang.</td>
    <td>Jury member</td>
    <td>Affiliation</td>
    <td>Archive</td>
    <td>Bechmark definition</td>
    <td>System description</td>
  </tr>
  <tr>
    <td style='font-size: 80%; font-weight: bold;'>
      Overview
    </td>
    <td style='font-size: 70%;'>

    </td>
    <td style='font-size: 70%;'>
      <a href='https://www.sosy-lab.org/~dbeyer/'>Dirk Beyer</a>
    </td>
    <td style='font-size: 70%;'>
      LMU Munich, Germany
    </td>
    <td style='font-size: 70%';>
 
    </td>
    <td style='font-size: 70%';>

    </td>
    <td>
      <!--<a href="https://www.sosy-lab.org/research/prs/2019-04-06_SV-COMP_Dirk.pdf">talk</a>-->
    </td>
  </tr>
";

wget --quiet --output-document=- $TABLEURL \
  | grep -v Timestamp  | sed 's/\t/^/g'\
  | while IFS='^' read TIMESTAMP EMAIL VERIFIERSHORT VERIFIERFULL URLVERIFIERPROJECT VERIFIERXML LANGUAGE MEMBER MEMBEREMAIL AFFIL URLMEMBER PUBLISH NEW URLPAPER PKG OPTOUT SECONDEMAIL LICENSE AUX PROCESS TESTB REST; do 
      if [[ "${VERIFIERXML}" =~ ^(chair_|val_|$) ]]; then
        continue;
      fi
      echo "  <tr>";
      VERIFIER=${VERIFIERXML//.xml/}
      VERIFIERARCHIVE=${VERIFIERXML//.xml/.zip}
      VERIFIER=${VERIFIER//[2]/two}
      VERIFIER=${VERIFIER//\-/}
      TOOLFUNC="${VERIFIER,,}${YEAR}";
      ARCHIVE=`echo "$URLVERIFIERARCHIVE" | sed "s/^.*\///" | sed "s/\?.*//"`;
      echo "    <td style='font-size: 80%; font-weight: bold;'>";
      if [ "$URLVERIFIERPROJECT" != "" ]; then
        echo "      <a href=\"$URLVERIFIERPROJECT\">$VERIFIERSHORT</a>";
      else
        echo "      $VERIFIERSHORT";
      fi
      echo "    </td>";
      echo "    <td style='font-size: 70%;'>";
      echo "      $LANGUAGE";
      echo "    </td>";
      echo "    <td style='font-size: 70%;'>";
      if [ "$URLMEMBER" != "" ]; then
        echo "      <a href='$URLMEMBER'>$MEMBER</a>";
      else
        echo "      $MEMBER";
      fi
      echo "    </td>";
      echo "    <td style='font-size: 70%;'>";
      echo "      $AFFIL";
      echo "    </td>";
      echo "    <td style='font-size: 70%';>";
      echo "      <!--$SHASUM-->";
      echo "      <a href='https://gitlab.com/sosy-lab/${TARGETSERVER}/archives-${YEAR}/raw/${TARGETSERVER/-/}${YEAR#??}/${YEAR}/${VERIFIERARCHIVE}'>Download</a>";
      echo "    </td>";
      echo "    <td style='font-size: 70%';>";
      echo "      <a href='https://gitlab.com/sosy-lab/${TARGETSERVER}/bench-defs/blob/${TARGETSERVER/-/}${YEAR#??}/benchmark-defs/$VERIFIERXML'>$VERIFIERXML</a>";
      echo "    </td>";
      echo "    <td>";
      echo "      ...";
      echo "    </td>";
      echo "  </tr>";
    done

echo "
</table>
<?php require('validators.php'); ?>
<?php pageFooter(); ?>
";
