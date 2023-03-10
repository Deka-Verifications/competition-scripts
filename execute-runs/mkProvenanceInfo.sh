#!/bin/bash

# This file is part of the competition environment.
#
# SPDX-FileCopyrightText: 2011-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# @title Write provenance information to config file
# @description Prepare Phase: write info about competition and components used to file

DIR=$(realpath "$(dirname "$0")")
TOOL_ARCHIVE=$1
COMPETITIONNAME=$(yq --raw-output '.competition' "$DIR/../../benchmark-defs/category-structure.yml")
YEAR=$(yq --raw-output '.year' "$DIR/../../benchmark-defs/category-structure.yml")
TARGETSERVER=$(echo "$COMPETITIONNAME" | tr "[:upper:]" "[:lower:]")
TAG_PREFIX_OPTION="--match $(echo "$COMPETITIONNAME" | tr "[:upper:]" "[:lower:]" | sed "s/-//")*"
GIT_REPOS="archives sv-benchmarks benchexec scripts ."

if [ -z "$TOOL_ARCHIVE" ]; then
  echo "Error: No verifier specified."
  exit 1
fi

if [[ ! -e "$TOOL_ARCHIVE" ]]; then
  echo "Tool archive $TOOL_ARCHIVE not found."
  exit 1
fi

echo ""
echo "Provenance information:"
echo "Benchmark executed"
echo "for $COMPETITIONNAME $YEAR, https://$TARGETSERVER.sosy-lab.org/$YEAR/"
echo "by $USER@$HOSTNAME"
echo "on $(date -Iminutes)"
echo "based on the components"
for repo in $GIT_REPOS; do
  (
  cd "$DIR/../../$repo" || exit
  if [ "$repo" == "benchexec" ]; then
    TAG_PREFIX_OPTION=""
  fi
  echo "$(git remote get-url origin)  git-describe: $(git describe --long --always $TAG_PREFIX_OPTION)"
  )
done

echo "Archive: $(basename "$TOOL_ARCHIVE")  DATE: $(date -Iminutes --date=@"$(stat --format=%Y "$TOOL_ARCHIVE")")  SHA1: $(shasum "$TOOL_ARCHIVE" | sed "s/\(.\{10\}\).*/\1/")..."
echo ""
