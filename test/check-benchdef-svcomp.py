#!/usr/bin/env python3
import argparse
import sys
import logging
from pathlib import Path
from urllib import request
from lxml import etree
import yaml

BENCHDEF_SUFFIX = ".xml"
ALLOWLIST_TASK_SETS = [
    # only properties not used in SV-COMP
    "DefinedBehavior-TerminCrafted",
    # only properties not used in SV-COMP
    "DefinedBehavior-Arrays",
    # only properties not used in SV-COMP
    "NoDataRace-Main",
    # only properties not used in SV-COMP
    "SoftwareSystems-SQLite-MemSafety",
    # unused
    "Unused_Juliet",
]

COLOR_RED = "\033[31;1m"
COLOR_GREEN = "\033[32;1m"
COLOR_ORANGE = "\033[33;1m"
COLOR_MAGENTA = "\033[35;1m"

COLOR_DEFAULT = "\033[m"
COLOR_DESCRIPTION = COLOR_MAGENTA
COLOR_VALUE = COLOR_GREEN
COLOR_WARNING = COLOR_RED

# if not sys.stdout.isatty():
#    COLOR_DEFAULT = ''
#    COLOR_DESCRIPTION = ''
#    COLOR_VALUE = ''
#    COLOR_WARNING = ''


def addColor(description, value, color=COLOR_VALUE, sep=": "):
    return "".join(
        (
            COLOR_DESCRIPTION,
            description,
            COLOR_DEFAULT,
            sep,
            color,
            value,
            COLOR_DEFAULT,
        )
    )


def error(msg, cause=None, label="    ERROR"):
    msg = addColor(label, str(msg), color=COLOR_WARNING)
    if cause:
        logging.exception(msg)
    else:
        logging.error(msg)
    global errorFound


def info(msg, label="INFO"):
    msg = str(msg)
    if label:
        msg = addColor(label, msg)
    logging.info(msg)


class DTDResolver(etree.Resolver):
    def __init__(self):
        self.cache = dict()

    def resolve(self, url, d_id, context):
        if url.startswith("http"):
            if url in self.cache:
                dtd_content = self.cache[url]
            else:
                dtd_content = self._download(url)
                self.cache[url] = dtd_content
            return self.resolve_string(dtd_content, context)
        return super().resolve(url, d_id, context)

    def _download(self, url):
        with request.urlopen(url) as inp:
            dtd_content = inp.read()
        return dtd_content


PARSER = etree.XMLParser(dtd_validation=True)
"""XML parser used in unit tests."""
PARSER.resolvers.add(DTDResolver())


def _check_valid(xml_file: Path):
    """Tries to parse the given xml file and returns any produced exceptions."""
    try:
        etree.parse(str(xml_file), PARSER)
        return []
    except (etree.ParseError, etree.XMLSyntaxError) as e:
        return ["Failed parsing xml: " + str(e)]


def _get_tasks(xml_file):
    xml_root = etree.parse(str(xml_file))
    return list(xml_root.iter(tag="tasks"))


def _check_task_defs_match_set(xml_file: Path, /, tasks_dir: Path):
    """Checks that each task element in the given xml_file fulfills certain criteria.

    The criteria are the following:
    1. each task element has an attribute 'name'
    2. each task element contains exactly one includesfile element
    3. the includesfile element references a `.set`-file in the sv-benchmarks directory
    4. the referenced `.set`-file matches the name of the task element
    """
    errors = []
    for task_tag in _get_tasks(xml_file):
        name = task_tag.get("name")
        if not name:
            errors.append(
                "Task tag is missing name in line {}".format(task_tag.sourceline)
            )

        includes = task_tag.findall("includesfile")
        if len(includes) != 1:
            errors.append(
                "Expected exactly one <includesfile> tag for tasks {}".format(name)
            )
        else:
            include = includes[0]
            included_set = Path(include.text)
            benchmark_dir = (xml_file.parent / included_set.parent).resolve()
            expected_dir = tasks_dir.resolve()
            if expected_dir.exists() and benchmark_dir != expected_dir:
                errors.append(
                    "Expected benchmark directory to be {} for tasks {} (was {})".format(
                        expected_dir, name, benchmark_dir
                    )
                )
            set_file = included_set.name
            if not set_file.endswith(".set"):
                errors.append("Set name does not end on '.set': {}".format(set_file))

            set_name = ".".join(set_file.split(".")[:-1])
            if not set_name == name:
                errors.append(
                    "Set name not consistent with tasks name: {} vs. {}".format(
                        set_name, name
                    )
                )
        if task_tag.findall("option"):
            errors.append("task {} contains <option> tag.".format(name))

    return errors


def _get_base_categories_participating(
    verifier, category_info, exclude_opt_outs=False
) -> set:
    if category_info["opt_out"] and verifier in category_info["opt_out"]:
        opt_outs = set(category_info["opt_out"][verifier])
    else:
        opt_outs = set()
    if category_info["opt_in"] and verifier in category_info["opt_in"]:
        opt_ins = set(category_info["opt_in"][verifier])
    else:
        opt_ins = set()

    meta_categories = category_info["categories"]
    categories_participating = set()
    for category, info in meta_categories.items():
        if exclude_opt_outs and category in opt_outs:
            continue
        participants = info["verifiers"]
        if verifier in participants:
            categories_participating |= set(info["categories"])

    categories_participating = categories_participating - set(meta_categories.keys())
    if exclude_opt_outs:
        categories_participating -= opt_outs
    categories_participating |= opt_ins
    return categories_participating


def _get_verifier_name(bench_def: Path) -> str:
    return bench_def.name[: -len(".xml")]


def _get_category_name(set_file) -> str:
    if isinstance(set_file, Path):
        return set_file.name[: -len(".set")]
    return set_file[: -len(".set")]


def _check_all_sets_used(
    bench_def: Path, category_info, /, tasks_directory: Path, exceptions: list = []
):
    tasks_defined = _get_tasks(bench_def)
    sets_included = {
        Path(include.text).name
        for t in tasks_defined
        for include in t.findall("includesfile")
    }
    categories_included = {_get_category_name(setfile) for setfile in sets_included}
    categories_expected = _get_base_categories_participating(
        _get_verifier_name(bench_def), category_info
    )

    if not categories_expected:
        return [f"No entry in category info"]

    if len(categories_included) > len(categories_expected):
        return [
            f"More sets used than expected: {categories_included - categories_expected}"
        ]
    missing_categories = categories_expected - categories_included - set(exceptions)

    if missing_categories:
        return [f"Missing includes for following sets: {missing_categories}"]
    return list()


def _perform_checks(xml: Path, category_info, tasks_dir: Path):
    info(str(xml), label="CHECKING")
    xml_errors = _check_valid(xml)
    if xml_errors:
        return xml_errors
    errors = _check_task_defs_match_set(xml, tasks_dir=tasks_dir)
    if tasks_dir.exists() and not "validate" in xml.name:
        errors += _check_all_sets_used(
            xml,
            category_info,
            tasks_directory=tasks_dir,
            exceptions=ALLOWLIST_TASK_SETS,
        )
    return errors


def _check_bench_def(xml: Path, category_info, /, tasks_dir: Path):
    """Checks the given xml benchmark definition for conformance."""
    errors = _perform_checks(xml, category_info, tasks_dir)
    if errors:
        error(xml)
        for msg in errors:
            error(msg)
    return not errors


def parse_yaml(yaml_file):
    with open(yaml_file) as inp:
        return yaml.safe_load(inp)


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
    parser.add_argument(
        "benchmark_definition",
        nargs="+",
        help="benchmark-definition XML files to check",
    )

    args = parser.parse_args(argv)

    args.category_structure = Path(args.category_structure)
    args.tasks_base_dir = Path(args.tasks_base_dir)
    args.benchmark_definition = [
        Path(bench_def) for bench_def in args.benchmark_definition
    ]

    missing_files = [
        f
        for f in args.benchmark_definition + [args.category_structure]
        if not f.exists()
    ]
    if missing_files:
        raise ValueError(
            f"File(s) do not exist: {','.join([str(f) for f in missing_files])}"
        )
    return args


def _verifiers_in_category(category_info, category):
    categories = category_info["categories"]
    if category not in categories:
        return []
    return [v + BENCHDEF_SUFFIX for v in categories[category]["verifiers"]]


def _unused_verifiers(category_info):
    if "not_participating" not in category_info:
        return []
    return category_info["not_participating"]


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    category_info = parse_yaml(args.category_structure)
    java_verifiers = _verifiers_in_category(category_info, "JavaOverall")
    unmaintained = _unused_verifiers(category_info)
    success = True
    if not args.tasks_base_dir or not args.tasks_base_dir.exists():
        info(
            f"Tasks directory doesn't exist. Will skip some checks. (Directory: {str(args.tasks_base_dir)})"
        )
    for bench_def in args.benchmark_definition:
        if _get_verifier_name(bench_def) in unmaintained:
            info(f"{bench_def}", label="SKIP")
            continue
        if bench_def.is_dir():
            info(str(bench_def) + " (is directory)", label="SKIP")
            continue
        if bench_def.name in java_verifiers:
            tasks_directory = args.tasks_base_dir / "java"
        else:
            tasks_directory = args.tasks_base_dir / "c"

        success &= _check_bench_def(bench_def, category_info, tasks_dir=tasks_directory)

    return 0 if success else 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=None)
    sys.exit(main())
