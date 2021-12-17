#!/bin/bash

# Generate PHP code for the competition web site to print tool names with links to the project web site.

echo "<?php
";

source scripts/configure.sh

yq --raw-output ".verifiers | to_entries [] \
    | [.key, .value.name, .value.url, .value.\"jury-member\".name, .value.\"jury-member\".institution, .value.\"jury-member\".country, .value.\"jury-member\".url] \
    | join(\"\t\")" \
    benchmark-defs/category-structure.yml \
  | sort \
  | while IFS=';' read TOOL TOOLNAME TOOLURL MEMBERNAME MEMBERINST MEMBERCOUNTRY MEMBERURL; do
  TOOLFUNC=${TOOL//[2]/two}
  TOOLFUNC=${TOOLFUNC//\-/}
  echo "function ${TOOLFUNC,,}${YEAR}() {";
  if [ -n "$TOOLURL" ]; then
    echo "  echo '<a href=\"$TOOLURL\">$TOOLNAME</a>';";
  else
    echo "  echo '$TOOLNAME';";
  fi
  echo "}";
  echo "";
done

echo "
?>";
