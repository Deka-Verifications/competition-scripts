#!/usr/bin/env python3

import argparse
import math
import re
import itertools
from pathlib import Path
import sys
from typing import Dict, Iterable, Optional, List, Sequence
import benchexec.tablegenerator as tablegenerator
import _logging as logging

from benchexec.tablegenerator import util


def is_time_column(column_name: str) -> bool:
    return re.fullmatch(r".*time", column_name) is not None


def _get_column_index(column_name: str, run_set_result) -> Optional[int]:
    """Get the index of the column with the given name in the given RunSetResult or RunResult."""
    columns = run_set_result.columns
    return next((columns.index(c) for c in columns if c.title == column_name), None)


def _get_column_values(
    column_name: str, run_set_result: tablegenerator.RunSetResult
) -> List[float]:
    column_index = _get_column_index(column_name, run_set_result)
    if column_index is None:
        return list()

    return [util.to_decimal(r.values[column_index]) for r in run_set_result.results]


def _load_run_results(
    result_files: Iterable[Path],
) -> Iterable[tablegenerator.RunSetResult]:
    files_as_str = (str(result_file) for result_file in result_files)
    arg_parser = tablegenerator.create_argument_parser()
    table_generator_options = arg_parser.parse_args([])
    return tablegenerator.load_results(files_as_str, table_generator_options)


def _get_time_column_values(sum_values: float) -> str:
    seconds = float(sum_values)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    time_str = []

    def to_time_str(value, unit):
        time_str.append(str(math.floor(value)) + unit)

    if days > 0:
        to_time_str(days, "d")
    if hours > 0:
        to_time_str(hours, "h")
    if minutes > 0:
        to_time_str(minutes, "min")
    if seconds > 0:
        to_time_str(seconds, "s")
    return ", ".join(time_str)


def _print_values(columns_and_values: Dict[str, List[float]]) -> None:
    value_count = len(next(iter(columns_and_values.items()), ("", []))[1])
    print("Runs:", value_count)
    for column, values in columns_and_values.items():
        sum_values = sum([v or 0 for v in values])
        if is_time_column(column):
            print_value = _get_time_column_values(sum_values)
        else:
            print_value = str(sum_values)
        print(column + ":", print_value)


def _snip_for_logging(lst, threshold=50):
    if len(lst) > threshold:
        half = int(threshold / 2)
        return str(lst[:half]) + "... snip ..." + str(lst[-half + 1 :])
    return str(lst)


def main(results_dirs: Sequence[Path], column_names: Sequence[str]) -> int:
    run_set_results = list()
    for results_dir in results_dirs:
        logging.debug("Considering directory %s", results_dir)
        results_files = [
            d
            for d in results_dir.glob("*.xml*")
            if re.match(r".+\.results\.[a-zA-Z0-9_\-]+\.xml(\.bz2)?", d.name)
        ]
        logging.debug(
            "Considering the following results files (%s): %s",
            len(results_files),
            _snip_for_logging(results_files),
        )
        run_set_results += _load_run_results(results_files)

    collected_values = {
        column: [v for r in run_set_results for v in _get_column_values(column, r)]
        for column in column_names
    }
    collected_values["file_count"] = [1] * len(run_set_results)

    _print_values(collected_values)
    return 0


if __name__ == "__main__":
    logging.init(logging.DEBUG, name="collect_aggregate_data")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--column-names",
        dest="column_names",
        default="cputime,walltime,cpuenergy",
        help="Columns to collect statistics for."
        + "We can only collect statistics for columns with float- or integer values."
        + "Columns should be given as a comma-separated-list.",
    )
    parser.add_argument("results_directory", nargs="+")

    args = parser.parse_args()
    args.column_names = [name.strip() for name in args.column_names.split(",")]
    args.results_directory = [Path(d) for d in args.results_directory]

    sys.exit(main(args.results_directory, args.column_names))
