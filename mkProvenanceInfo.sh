#!/bin/bash

# This file is part of the competition environment.
#
# SPDX-FileCopyrightText: 2011-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# @title Write provenance information to config file
# @description Prepare Phase: write info about competition and components used to file

VERIFIER=$1
COMPETITIONNAME=`scripts/parseInitConfig.py --get-comp benchmark-defs/category-structure.yml`
YEAR=`scripts/parseInitConfig.py --get-year benchmark-defs/category-structure.yml`
TARGETSERVER=`echo ${COMPETITIONNAME} | tr [:upper:] [:lower:]`
ARCHIVE="`pwd`/archives/${YEAR}/${VERIFIER}.zip"
GIT_REPOS="archives sv-benchmarks benchexec scripts"

if [ -z $VERIFIER ]; then
  echo "Error: No verifier specified."
  exit 1
fi

echo ""
echo "Provenance information:"
echo "Benchmark executed"
echo "for ${COMPETITIONNAME} ${YEAR}, https://${TARGETSERVER}.sosy-lab.org/${YEAR}/"
echo "by ${USER}@${HOSTNAME}"
echo "based on the components"
for repo in $GIT_REPOS; do
  (
  cd "$repo"
  echo "`git remote get-url origin`  `git describe --long --always`"
  )
done

echo "Archive: ${VERIFIER}.zip  SHA1: "`shasum ${ARCHIVE} | sed "s/\(.\{10\}\).*/\1/"`"..."
echo "on `date -Iminutes`"
echo ""
