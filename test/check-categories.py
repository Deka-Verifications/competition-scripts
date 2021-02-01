#!/usr/bin/env python3
import argparse
from collections import namedtuple, defaultdict
import logging
from pathlib import Path
import sys
from typing import Iterable, Optional
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

    for opt in ("opt_in", "opt_out"):
        if opt not in category_info or not category_info[opt]:
            continue  # no opt_in or opt_out in category info
        for category in {
            c for categories in category_info[opt].values() for c in categories
        }:
            if category not in categories_used:
                yield f"Category used in {opt}, but missing in meta categories: {category}"


def _get_prop_name(property_file) -> str:
    if isinstance(property_file, Path):
        return property_file.name[: -len(".prp")]
    return _get_prop_name(Path(property_file))


def get_setfile_tasks(set_file: Path) -> Iterable[Path]:
    with open(set_file) as inp:
        globs = [
            line.strip()
            for line in inp.readlines()
            if line.strip() and not line.strip().startswith("#")
        ]
    return (t for g in globs for t in set_file.parent.glob(g))


def get_properties_of_task(task_file: Path) -> Iterable[str]:
    task_yaml = util.parse_yaml(task_file)
    properties = task_yaml["properties"]
    if not isinstance(properties, list):
        properties = [properties]
    return (_get_prop_name(p["property_file"]) for p in properties)


def _is_category_empty(set_file: Path, prop: str) -> Iterable[str]:
    for t in get_setfile_tasks(set_file):
        if prop in get_properties_of_task(t):
            return False
    return True


def get_set_for_category(set_name: str, tasks_dir: Path) -> Optional[Path]:
    expected_sets = [tasks_dir / lang / set_name for lang in ("c", "java")]
    return next((s for s in expected_sets if s.exists()), None)


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
            existing_set = get_set_for_category(set_name, tasks_dir)
            if not existing_set:
                yield f"Set missing for {set_name}"
                continue
            if all((_is_category_empty(existing_set, prop) for prop in expected_props)):
                yield f"No task for properties {expected_props} in category {b} (set file: {existing_set})"


def _check_category_participants(
    category_info: dict, participants: Iterable[str]
) -> Iterable[str]:
    participants = set(participants)
    for name, c in category_info["categories"].items():
        not_participating = set(c["verifiers"]) - participants
        if not_participating:
            yield f"Verifiers listed in category {name}, but not participating: {not_participating}"


def check_categories(
    category_info: dict, tasks_dir: Path, participants: Iterable[str]
) -> Iterable[str]:
    errors = _check_info_consistency(category_info)
    errors = itertools.chain(
        errors, _check_categories_nonempty(category_info, tasks_dir)
    )
    errors = itertools.chain(
        errors, _check_category_participants(category_info, participants)
    )
    return errors


def check_all_tasks_used(tasks_dir: Path, category_info: dict) -> Iterable[str]:
    used_directories = defaultdict(set)
    for info in category_info["categories"].values():
        properties = info["properties"]
        if not isinstance(properties, list):
            properties = [properties]

        PropAndCat = namedtuple("PropAndCat", ["property", "category"])
        # by checking that there's a '.' in the category name,
        # we only check base categories and ignore other meta categories
        # that are used as sub-categories of the current meta category.
        used_categories = [
            PropAndCat(*c.split(".")) for c in info["categories"] if "." in c
        ]

        for prop in properties:
            used_set_files = [
                get_set_for_category(c.category + ".set", tasks_dir)
                for c in used_categories
                if c.property == prop
            ]
            assert (
                None not in used_set_files
            )  # should be ensured by previous _check_categories_nonempty
            used_directories[prop] |= {
                t.parent
                for set_file in used_set_files
                for t in get_setfile_tasks(set_file)
            }

    all_set_files = tasks_dir.glob("**/*.set")
    logging.debug("Used directories per property: %s", used_directories)
    for prop, used_dirs in used_directories.items():
        covered_directories = used_dirs.copy()
        tasks = (t for set_file in all_set_files for t in get_setfile_tasks(set_file))
        for t in tasks:
            task_parent_dir = t.parent
            if task_parent_dir in covered_directories:
                continue
            if prop in get_properties_of_task(t):
                covered_directories.add(task_parent_dir)
                yield f"For property {prop}, the following directory is not used: {task_parent_dir}"


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
    participants = category_info["verifiers"]
    errors = check_categories(category_info, args.tasks_base_dir, participants)
    errors = itertools.chain(
        errors, check_all_tasks_used(args.tasks_base_dir, category_info)
    )
    success = True
    for msg in errors:
        success = False
        util.error(msg)
    return 0 if success else 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=None)
    sys.exit(main())
