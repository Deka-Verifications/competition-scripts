#!/bin/bash

FILES_TO_REMOVE=$(cat "$(dirname "$0")"/mkAnaRemoveResults.csv)

grep_pattern=$(echo ${FILES_TO_REMOVE[@]} | tr " " "|")

for dir in results-verified results-validated; do
  for i in "$dir"/*.xml.bz2; do 
    if bzgrep -q -E "$grep_pattern" "$i";
    then
      echo "Processing $i"
      input=$(bzcat "$i")
      for to_remove in ${FILES_TO_REMOVE[@]}; do
          escaped_pattern=$(echo $to_remove | sed 's/[]\/$*.^|[]/\\&/g')
          input=$(sed "/$escaped_pattern/,/<\/run>/d" <<< "$input")
      done
      echo "$input" | bzip2 -9 > "$i.tmp"
      mv "$i.tmp" "$i"
    fi
  done
done
