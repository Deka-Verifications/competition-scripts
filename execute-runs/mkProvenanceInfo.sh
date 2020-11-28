#!/bin/bash

# This file is part of the competition environment.
#
# SPDX-FileCopyrightText: 2011-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# @title Write provenance information to config file
# @description Prepare Phase: write info about competition and components used to file

DIR=$(dirname "$0")
VERIFIER=$1
COMPETITIONNAME=$($DIR/parseInitConfig.py --get-comp $DIR/../benchmark-defs/category-structure.yml)
YEAR=$($DIR/parseInitConfig.py --get-year $DIR/../benchmark-defs/category-structure.yml)
TARGETSERVER=$(echo $COMPETITIONNAME | tr [:upper:] [:lower:])
ARCHIVE="$DIR/../archives/$YEAR/$VERIFIER.zip"
GIT_REPOS="archives sv-benchmarks benchexec scripts"

if [ -z $VERIFIER ]; then
  echo "Error: No verifier specified."
  exit 1
fi

echo ""
echo "Provenance information:"
echo "Benchmark executed"
echo "for $COMPETITIONNAME $YEAR, https://$TARGETSERVER.sosy-lab.org/$YEAR/"
echo "by $USER@$HOSTNAME"
echo "on `date -Iminutes`"
echo "based on the components"
for repo in $GIT_REPOS; do
  (
  cd "$DIR/../$repo"
  echo "`git remote get-url origin`  `git describe --long --always`"
  )
done

echo "Archive: $VERIFIER.zip  DATE: "$(date -Iminutes --date=@$(stat --format=%Y $ARCHIVE))"  SHA1: "`shasum $ARCHIVE | sed "s/\(.\{10\}\).*/\1/"`"..."
echo ""
