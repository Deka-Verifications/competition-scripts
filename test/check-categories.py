#!/usr/bin/env python3
import argparse
import logging
from pathlib import Path
import sys
from typing import Iterable
import itertools
import _util as util


def _base_categories(category_info: dict) -> Iterable[str]:
    meta_categories = set(category_info["categories"].keys())
    return _all_categories(category_info) - meta_categories


def _all_categories(category_info: dict) -> Iterable[str]:
    meta_categories = category_info["categories"]
    categories = set(meta_categories.keys())
    for info in meta_categories.values():
        # do not use util.get_category_name(c) on purpose, to distinguish same task sets for different properties
        categories |= set(info["categories"])
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


def _get_prop_name(property_file) -> str:
    if isinstance(property_file, Path):
        return property_file.name[: -len(".prp")]
    return _get_prop_name(Path(property_file))


def _is_category_empty(set_file: Path, prop: str) -> Iterable[str]:
    with open(set_file) as inp:
        globs = [
            line.strip()
            for line in inp.readlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    tasks = (t for g in globs for t in set_file.parent.glob(g))
    for t in tasks:
        task_yaml = util.parse_yaml(t)
        props = (_get_prop_name(p["property_file"]) for p in task_yaml["properties"])
        if prop in props:
            return False
    return True


def _check_categories_nonempty(category_info: dict, tasks_dir: Path) -> Iterable[str]:
    meta_categories = _all_categories(category_info) - _base_categories(category_info)
    for _, c in category_info["categories"].items():
        expected_props = c["properties"]
        if isinstance(expected_props, str):
            expected_props = [expected_props]
        expected_props = [
            p[: -len("_java")] if p.endswith("_java") else p for p in expected_props
        ]
        base_categories = set(c["categories"]) - meta_categories
        for b in base_categories:
            name = util.get_category_name(b)
            set_name = name + ".set"
            expected_sets = [tasks_dir / lang / set_name for lang in ("c", "java")]
            existing_set = next((s for s in expected_sets if s.exists()), None)
            if not existing_set:
                yield f"Set missing. Expected any of the following: {[str(s) for s in expected_sets]}"
                continue
            if all((_is_category_empty(existing_set, prop) for prop in expected_props)):
                yield f"No task for properties {expected_props} in category {b} (set file: {existing_set})"


def check_categories(category_info: dict, tasks_dir: Path) -> Iterable[str]:
    errors = _check_info_consistency(category_info)
    errors = itertools.chain(
        errors, _check_categories_nonempty(category_info, tasks_dir)
    )
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
    errors = check_categories(category_info, args.tasks_base_dir)
    for msg in errors:
        util.error(msg)
    return 1 if errors else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=None)
    sys.exit(main())
