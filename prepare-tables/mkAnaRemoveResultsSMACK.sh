#!/bin/bash

# be careful not to add a comma in the array!
CATEGORIES_TO_CLEAN=(
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-memsafety.MemSafety-Arrays.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-memsafety.MemSafety-Heap.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-memsafety.Systems_BusyBox_MemSafety.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-nooverflow.NoOverflows-BitVectors.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-nooverflow.NoOverflows-Other.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-nooverflow.Systems_BusyBox_NoOverflows.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-reachsafety.ConcurrencySafety-Main.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-reachsafety.ReachSafety-Arrays.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-reachsafety.ReachSafety-BitVectors.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-reachsafety.ReachSafety-ControlFlow.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-reachsafety.ReachSafety-ECA.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-reachsafety.ReachSafety-Heap.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-reachsafety.ReachSafety-Loops.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-reachsafety.ReachSafety-Recursive.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-reachsafety.Systems_DeviceDriversLinux64_ReachSafety.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-termination.Termination-MainControlFlow.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-termination.Termination-MainHeap.xml.bz2"
    "results-verified/smack.2018-12-07_1913.results.sv-comp19_prop-termination.Termination-Other.xml.bz2"
)

for i in ${CATEGORIES_TO_CLEAN[@]}; do 
  echo "Processing $i"
  input=$(bzcat "$i")
  input=$(sed "s/<column hidden=\"true\" title=\"category\" value=\".*\"\/>/<column hidden=\"true\" title=\"category\" value=\"missing\"\/>/" <<< "$input")
  input=$(sed "s/<column title=\"status\" value=\".*\"\/>/<column title=\"status\" value=\"disqualified\"\/>/" <<< "$input")
  echo "$input" | bzip2 -9 > "$i.tmp.bz2"
  mv "$i.tmp.bz2" "$i"
done
