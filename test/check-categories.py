#!/usr/bin/env python3
import argparse
import logging
from pathlib import Path
import sys
from typing import List, Iterable
import _util as util


def _base_categories(category_info: dict) -> Iterable[str]:
    meta_categories = set(category_info["categories"].keys())
    return _all_categories(category_info) - meta_categories


def _all_categories(category_info: dict) -> Iterable[str]:
    meta_categories = category_info["categories"]
    categories = set(meta_categories.keys())
    for info in meta_categories.values():
        # do not use util.get_category_name(c) on purpose, to distinguish same task sets for different properties
        categories |= {c for c in info["categories"]}
    return categories


def _check_info_consistency(category_info: dict) -> Iterable[str]:
    if not "categories_process_order" in category_info:
        yield "Missing 'categories_process_order'"
        return
    in_process_order = set(category_info["categories_process_order"])

    if not "categories_table_order" in category_info:
        yield "Missing 'categories_table_order'"
        return
    in_table_order = set(category_info["categories_table_order"])

    if len(in_process_order) > len(in_table_order):
        yield f"Categories listed in process order, but missing in table order: {in_process_order - in_table_order}"
    if len(in_process_order) < len(in_process_order):
        yield f"Categories listed in table order, but missing in process order: {in_table_order - in_process_order}"

    categories_used = _all_categories(category_info)
    if len(categories_used) > len(in_process_order | in_table_order):
        yield f"Categories (used in) meta categories, but missing in process and table order: {categories_used - (in_process_order | in_table_order)}"
    if len(categories_used) < len(in_process_order | in_table_order):
        yield f"Categories used in process or table order, but missing in meta categories: {(in_process_order | in_table_order) - categories_used}"


def check_categories(category_info: dict) -> Iterable[str]:
    errors = list()
    errors += _check_info_consistency(category_info)
    return errors


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--category-structure",
        default="benchmark-defs/category-structure.yml",
        required=False,
        help="category-structure.yml to use",
    )
    parser.add_argument(
        "--tasks-directory",
        dest="tasks_base_dir",
        default="sv-benchmarks",
        required=False,
        help="directory to benchmark tasks",
    )

    args = parser.parse_args(argv)

    args.category_structure = Path(args.category_structure)
    args.tasks_base_dir = Path(args.tasks_base_dir)
    missing_files = [f for f in [args.category_structure] if not f.exists()]
    if missing_files:
        raise ValueError(
            f"File(s) do not exist: {','.join([str(f) for f in missing_files])}"
        )
    return args


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    category_info = util.parse_yaml(args.category_structure)
    errors = check_categories(category_info)
    for msg in errors:
        util.error(msg)
    return 1 if errors else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=None)
    sys.exit(main())
