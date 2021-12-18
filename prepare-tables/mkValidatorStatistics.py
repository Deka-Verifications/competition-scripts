#!/usr/bin/env python3

# Call using `PYTHONPATH=benchexec ./scripts/prepare-tables/mkValidatorStatistics.py`
from contrib.mergeBenchmarkSets import *
from collections import Counter
import os
import re
import datetime
import yaml
import argparse
import sys
import _logging as logging

VERIFIEDDIR = "./results-verified/"
VALIDATEDDIR = "./results-validated/"

import benchexec.result as Result
import benchexec.tablegenerator as tablegenerator


def getLatestVerifierXML(verifier, category):
    """
    example usage:
    print(getLatestVerifierXML("cpa-seq","ReachSafety"))
    """
    r = re.compile(
        verifier
        + "\.(.?.?.?.?-.?.?-.?.?_.?.?-.?.?-.?.?)\.results\.SV-COMP22_"
        + category.lower()
        + "\.xml\.bz2"
    )
    result = None
    date = None
    for filename in os.listdir(VERIFIEDDIR):
        m = r.match(filename)
        if m:
            newDate = datetime.datetime.strptime(m.group(1), "%Y-%m-%d_%H-%M-%S")
            if result and newDate < date:
                continue
            result = VERIFIEDDIR + filename
            date = newDate
    if result:
        return result


def getLatestWitnessXMLs(verifier, category):
    """
    example usage:
    for (k,v) in getLatestWitnessXMLs("cpa-seq","ReachSafety").items():
    print("%s\n%s" % (k,v))
    """
    rval = re.compile(
        "(.*)-"
        + verifier
        + "\.(.?.?.?.?-.?.?-.?.?_.?.?-.?.?-.?.?)\.results\.SV-COMP22_"
        + category.lower()
        + "\.xml\.bz2"
    )
    results = dict()
    dates = dict()
    for filename in os.listdir(VALIDATEDDIR):
        m = rval.match(filename)
        if m:
            date = datetime.datetime.strptime(m.group(2), "%Y-%m-%d_%H-%M-%S")
            if m.group(1) in results and date < dates[m.group(1)]:
                continue
            results[m.group(1)] = VALIDATEDDIR + filename
            dates[m.group(1)] = date
    return results


def xmlPathToValidatorName(s):
    """
    example usage:
    s = "/results-validated/uautomizer-validate-violation-witnesses-cpa-seq.2019-12-03_0856.results.sv-comp20_prop-reachsafety.xml.bz2"
    print(xmlPathToValidatorName(s))
    """
    if not xmlPathToValidatorName.r:
        xmlPathToValidatorName.r = re.compile(".*results-validated/(.*)-witnesses-.*")
    m = xmlPathToValidatorName.r.match(s)
    if m:
        return m.group(1)
    else:
        return None


xmlPathToValidatorName.r = re.compile(".*results-validated/(.*)-witnesses-.*")


def scanWitnessResults(verifier, category, property_, counter):
    resultFile = getLatestVerifierXML(verifier, property_)
    if not resultFile:
        if verifier in catdict["opt_out"] and any(
            category.lower() in entry.lower() for entry in catdict["opt_out"][verifier]
        ):
            logging.info("Verifier %s opted out of category %s", verifier, category)
        else:
            logging.warning("No result for %s in category %s", verifier, category)

        return
    logging.info("Scanning result file: %s", resultFile)
    witnessFiles = getLatestWitnessXMLs(verifier, property_).values()

    if not os.path.exists(resultFile) or not os.path.isfile(resultFile):
        logging.error(f"File {repr(resultFile)} does not exist")
        sys.exit(1)
    resultXML = tablegenerator.parse_results_file(resultFile)
    witnessSets = []
    for witnessFile in witnessFiles:
        if not os.path.exists(witnessFile) or not os.path.isfile(witnessFile):
            logging.error(f"File {repr(witnessFile)} does not exist")
            sys.exit(1)
        witnessXML = tablegenerator.parse_results_file(witnessFile)
        witnessSets.append(getWitnesses(witnessXML))

    # check for presence of validator results for every (verifier,category) in case category-structure.yml claims that the validator is validating the category
    for val in catdict["categories"][category]["validators"]:
        found = False
        for item in [
            xmlPathToValidatorName(witnessFile) for witnessFile in witnessFiles
        ]:
            if (
                ("%s-validate-%s")
                % ("-".join(val.split("-")[0:-1]), val.split("-")[-1])
            ) in item:
                found = True
        if not found:
            logging.warning(
                "Missing validation results with validator %s! (category:%s, verifier:%s)",
                val,
                category,
                verifier,
            )
        else:
            logging.info(
                f"Found validation results with validator {val}! (category:{category}, verifier:{verifier})"
            )

    for result in resultXML.findall("run"):
        run = result.get("name")
        try:
            status_from_verification = result.find('column[@title="status"]').get(
                "value"
            )
            category_from_verification = result.find('column[@title="category"]').get(
                "value"
            )
        except:
            status_from_verification = "not found"
            category_from_verification = "not found"
        statusWit, categoryWit = (None, None)
        d = dict()
        for (witnessSet, witnessFile) in zip(witnessSets, witnessFiles):
            witness = witnessSet.get(run, None)
            # copy data from witness
            if witness is not None and len(witness) > 0:
                counter[
                    category
                    + "-EXISTING_WITNESSES-"
                    + xmlPathToValidatorName(witnessFile)
                ] += 1
                # For verification
                statusWitNew, categoryWitNew = getWitnessResult(
                    witness, result
                )  # for this call we need the import from mergeBenchmarkSets.py
                d[witnessFile] = (statusWitNew, categoryWitNew)
                if not (
                    statusWitNew.startswith("witness invalid")
                    or statusWitNew.startswith("result invalid")
                ):
                    counter[
                        category
                        + "-VALID_WITNESSES-"
                        + xmlPathToValidatorName(witnessFile)
                    ] += 1
                # if (
                #    categoryWit is None
                #    or not categoryWit.startswith(Result.CATEGORY_CORRECT)
                #    or categoryWitNew == Result.CATEGORY_CORRECT
                #    or statusWitNew.startswith("witness invalid")
                # ):
                #    statusWit, categoryWit = (statusWitNew, categoryWitNew)
        for validator in d.keys():
            if d[validator][1] == Result.CATEGORY_CORRECT:
                unique = True
                joint = False
                for othervalidator in d.keys():
                    if (
                        othervalidator != validator
                        and d[othervalidator][1] == Result.CATEGORY_CORRECT
                    ):
                        unique = False
                        joint = True
                if unique:
                    counter[
                        category
                        + "-CONFIRMED_UNIQUE-"
                        + xmlPathToValidatorName(validator)
                    ] += 1
                if joint:
                    counter[
                        category
                        + "-CONFIRMED_JOINT-"
                        + xmlPathToValidatorName(validator)
                    ] += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--silent", help="output no debug information", action="store_true"
    )
    parser.add_argument(
        "--category-structure",
        required=True,
        dest="category_structure",
        help="Path to the category-structure.yml",
    )
    parser.add_argument(
        "--htmlfile",
        help="file in case the statistics shall be made available as HTML document",
    )
    args = parser.parse_args()
    if args.silent:
        logging.init(logging.ERROR, "mkValidatorStatistics")
    else:
        logging.init(logging.DEBUG, "mkValidatorStatistics")

    catdict = yaml.load(
        open(args.category_structure, "r").read(), Loader=yaml.FullLoader
    )

    # hack for inconsistency between main category name and filename of the xml:
    if "NoOverflows" in catdict["categories"]:
        catdict["categories"]["NoOverflow"] = catdict["categories"]["NoOverflows"]
        del catdict["categories"]["NoOverflows"]
        assert not "NoOverflows" in catdict["categories"]
        assert "NoOverflow" in catdict["categories"]

    # remove meta-categories for now, as they do not have their own xml file:
    for entry in (
        "FalsificationOverall",
        "JavaOverall",
        "SoftwareSystems",
        "Overall",
        "ConcurrencySafety",
    ):
        del catdict["categories"][entry]

    counter = Counter()
    for category in catdict["categories"].keys():
        # hack to get the string in the xml file names which is actually the property,
        # not the category
        properties = catdict["categories"][category]["properties"]
        assert isinstance(properties, str) or len(properties) <= 2
        if not isinstance(properties, str):
            if len(properties) == 2:
                assert category == "MemSafety"
            property_ = properties[0]
        else:
            property_ = properties
        verifiers = catdict["categories"][category]["verifiers"]
        for verifier in verifiers:
            scanWitnessResults(verifier, category, property_, counter)
    tablestart = """<!DOCTYPE html>
<html>
<head>
<title>Validator Statistics</title>
<link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.1.3/css/bootstrap.css">
<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.10.20/css/dataTables.bootstrap4.min.css">
<script type="text/javascript" language="javascript" src="https://code.jquery.com/jquery-3.3.1.js"></script>
<script type="text/javascript" language="javascript" src="https://cdn.datatables.net/1.10.20/js/jquery.dataTables.min.js"></script>
<script type="text/javascript" language="javascript" src="https://cdn.datatables.net/1.10.20/js/dataTables.bootstrap4.min.js"></script>
<script type="text/javascript" class="init">
$(document).ready(function() {
    // Setup - add a text input to each footer cell
    $('#basic thead tr').clone(true).appendTo( '#basic thead' );
    $('#basic thead tr:eq(1) th').each( function (i) {
        var title = $(this).text();
        $(this).html( '<input type="text" placeholder="Search '+title+'" />' );
 
        $( 'input', this ).on( 'keyup change', function () {
            if ( table.column(i).search() !== this.value ) {
                table
                    .column(i)
                    .search( this.value )
                    .draw();
            }
        } );
    } );
 
    var table = $('#basic').DataTable( {
        orderCellsTop: true,
        fixedHeader: true
    } );
} );
</script>
</head>
          
<body>
        <table id="basic" class="table table-striped table-bordered" cellspacing="0" width="100%">
        <thead>
        <tr>
          <th>Category
          </th>
          <th>Violation/Correctness
          </th>
          <th>Validator
          </th>
          <th>Criterion
          </th>
          <th>Count</th>
        </tr>
      </thead>
    <tbody>

"""
    tableend = """</tbody>
</table>
</body>
</html>
"""
    if not args.htmlfile:
        sys.exit(0)
    with open(args.htmlfile, "w") as f:
        f.write(tablestart)
        for (k, v) in counter.items():
            m = re.compile("([a-zA-Z]*)-([A-Z\_]*)-(.*)-validate-(.*)").match(k)
            if not m:
                logging.warning(f"No statistics found for {k}")
                continue
            category = m.group(1)
            criterion = m.group(2)
            verifier = m.group(3)
            result = m.group(4)
            f.write(
                "<tr> <td>%s</td> <td>%s</td> <td>%s</td> <td>%s</td> <td>%s</td> </tr>\n"
                % (category, result, verifier, criterion.lower(), v)
            )
        f.write(tableend)
