#!/bin/bash

source $(dirname "$0")/../configure.sh

yq -r '.verifiers [] | if ."jury-member".name != "Hors Concours" then ."jury-member".name else empty end' benchmark-defs/category-structure.yml \
  | while IFS=$'\n' read MEMBERNAME; do
  grep "$MEMBERNAME" "$ADDRESS_BOOK"
done | sort -u

