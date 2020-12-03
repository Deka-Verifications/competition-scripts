#!/bin/bash

# This file is part of the competition environment.
#
# SPDX-FileCopyrightText: 2011-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

# @title Install Tool Archive
# @description Unzips and checks the structure of tool archive.

VERIFIER=$1;
YEAR=`scripts/parseInitConfig.py --get-year benchmark-defs/category-structure.yml`;
ARCHIVE="`pwd`/archives/${YEAR}/${VERIFIER}.zip";

if [ -z $VERIFIER ]; then
  echo "Error: No verifier specified.";
  exit 1;
fi

# Unzip
echo "Installing $ARCHIVE ...";
rm -rf ./bin/${VERIFIER};
mkdir -p ./bin/${VERIFIER};
cd ./bin/$VERIFIER;
unzip $ARCHIVE;
# Check structure
if [[ `find . -mindepth 1 -maxdepth 1 | wc -l` == 1 ]]; then
  echo "Info: One folder found in archive.";
  DIR="`find . -mindepth 1 -maxdepth 1`";
  mv "${DIR}" "${DIR}__COMP";
  mv "${DIR}__COMP"/* .
  rmdir "${DIR}__COMP"
else
  echo "Error: Archive does not contain exactly one folder.";
  exit 1;
fi

