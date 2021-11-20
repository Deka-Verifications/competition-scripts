import fnmatch

from math import floor, log10
import os
import yaml
import logging
import zipfile

JSON_INDENT = 4

_BLACKLIST = (
    "__CLOUD__created_files.txt",
    "RunResult-*.zip",
    "*.log.data",
    "*.log.stdError",
    "fileHashes.json",
)
"""List of files that are not hashed. May include wildcard '*' and brackets '[', ']'"""


def is_on_blacklist(filename):
    return any(fnmatch.fnmatch(os.path.basename(filename), b) for b in _BLACKLIST)


def get_file_number_in_zip(zipped_file) -> int:
    """Return the list of files in this zip"""
    try:
        with zipfile.ZipFile(zipped_file) as inp_zip:
            return len(
                [
                    x
                    for x in inp_zip.namelist()
                    if x.endswith(".xml") and not x.endswith("metadata.xml")
                ]
            )
    except FileNotFoundError as e:
        # print('Error: Zip file does not exist.')
        return 0


def round_to_sig_numbers(x: float, n: int) -> float:
    if x == 0:
        return 0
    return round(x, -int(floor(log10(abs(x)))) + (n - 1))


def parse_yaml(yaml_file):
    try:
        with open(yaml_file) as inp:
            return yaml.safe_load(inp)
    except yaml.scanner.ScannerError as e:
        logging.error("Exception while scanning %s", yaml_file)
        raise e
