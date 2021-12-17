#!/bin/bash

# Generate committee-listing web page for the competition web site.

source scripts/configure.sh

# Print list of jury members:
# yq -r '.verifiers [] | if ."jury-member".name != "Hors Concours" then ."jury-member".name else empty end' benchmark-defs/category-structure.yml

echo "<!-- This is generated. Do not change manually. -->";
yq --raw-output ".verifiers | to_entries [] \
    | [.key, .value.name, .value.url, .value.\"jury-member\".name, .value.\"jury-member\".institution, .value.\"jury-member\".country, .value.\"jury-member\".url] \
    | join(\";\")" \
    benchmark-defs/category-structure.yml \
  | sort \
  | while IFS=';' read TOOL TOOLNAME TOOLURL MEMBERNAME MEMBERINST MEMBERCOUNTRY MEMBERURL; do
  if [[ "$MEMBERNAME" == "Hors Concours" ]]; then
    continue
  fi
  TOOLFUNC=${TOOL//[2]/two}
  TOOLFUNC=${TOOLFUNC//\-/}
  if [[ ! "$MEMBERNAME" =~ "Team" ]]; then
    echo "  <li>";
    if [[ -n "$MEMBERURL" ]]; then
      echo "    <a href=\"$MEMBERURL\">$MEMBERNAME</a>";
    else
      echo "    $MEMBERNAME ";
    fi
    echo "      (representing <?php ${TOOLFUNC,,}${YEAR}() ?>), $MEMBERINST, $MEMBERCOUNTRY";
    echo "  </li>";
  fi
done
