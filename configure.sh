# Configuration of variables to initialize the competition environment

set -eao pipefail

CONTRIB_DIR=$(realpath "contrib");
SCRIPT_DIR=$(realpath "scripts");
export BENCHMARKSDIR="benchmark-defs";

YEAR=$(yq --raw-output '.year' ${BENCHMARKSDIR}/category-structure.yml)
COMPETITIONNAME=$(yq --raw-output '.competition' ${BENCHMARKSDIR}/category-structure.yml)
COMPETITION=${COMPETITIONNAME}${YEAR#??}  # use two last digits of year, only
TARGETSERVER=`echo ${COMPETITIONNAME} | tr A-Z a-z`
export FILE_STORE_URL_PREFIX="https://${TARGETSERVER}.sosy-lab.org/${YEAR}/results/"

export PATHPREFIX=$(realpath .)
TARGETDIR=${COMPETITIONNAME}
export RESULTSVERIFICATION="results-verified";
export RESULTSVALIDATION="results-validated";
export HTMLOVERVIEW="$PATHPREFIX/${RESULTSVERIFICATION}/iZeCa0gaey.html";
export BINDIR="bin";
export PYTHONPATH="${PATHPREFIX}/benchexec";
export BENCHEXEC_PATH="${PATHPREFIX}/benchexec";

ADDRESS_BOOK=~/.competition-address-book.txt
USER_CONFIG=~/.competition-configure.sh
if [ -e "$USER_CONFIG" ]; then
  source "$USER_CONFIG"
fi

export HASHES_BASENAME="fileHashes.json";
export HASHDIR_BASENAME="fileByHash";

export PROPERTIES=$(yq -r '.properties []' benchmark-defs/category-structure.yml)
VALIDATORLIST=$(yq -r '.validators | keys []' benchmark-defs/category-structure.yml);
#VALIDATORLIST="symbiotic-witch-validate-violation-witnesses";

RESULTSLEVEL="Final";
if [[ -n "$LIMIT_CORES" && -n "$LIMIT_MEMORY" && -n "$LIMIT_TIME" ]]; then
  LIMITSTEXT="\nLimits: The current pre-run results are limited to $LIMIT_TIME s of CPU time, $LIMIT_CORES cores, and $LIMIT_MEMORY GB.\n"
  LIMITS="$LIMITS --limitCores $LIMIT_CORES"
  LIMITS="$LIMITS --memorylimit ${LIMIT_MEMORY}GB"
  LIMITS="$LIMITS --timelimit $LIMIT_TIME";
  RESULTSLEVEL="Pre-run";
fi

if [[ "${COMPETITIONNAME}" == "SV-COMP" ]]; then
  VALIDATIONKIND="witnesses";

  WITNESSTARGET="witness.graphml";
  WITNESSGLOBSUFFIX=".graphml";

elif [[ "${COMPETITIONNAME}" == "Test-Comp" ]]; then
  VALIDATIONKIND="test-suites";

  WITNESSTARGET="test-suite.zip";
  WITNESSGLOBSUFFIX=".zip";

  TESTCOMPOPTION="--zipResultFiles";

  LIMITSVALIDATION="--timelimit 300";
  TARGETDIR=`echo ${COMPETITIONNAME} | tr A-Z a-z`

else
  echo "Unhandled competition $COMPETITIONNAME" ; false
fi

BENCHEXECOPTIONS="--read-only-dir / --hidden-dir /home --overlay-dir . --vcloudAdditionalFiles . --maxLogfileSize 2MB --vcloudClientHeap 4000 --cgroupAccess ${TESTCOMPOPTION}";
if [ -e /data ]; then
  # If scratch folder 'data' exists, make it read-only to avoid benchexec errors
  # on container creation
  BENCHEXECOPTIONS="${BENCHEXECOPTIONS} --read-only-dir /data"
fi
export OPTIONSVERIFY="${BENCHEXECOPTIONS} ${LIMITS} --vcloudPriority IDLE";
export OPTIONSVALIDATE="${BENCHEXECOPTIONS} ${LIMITSVALIDATION} --vcloudPriority LOW";


