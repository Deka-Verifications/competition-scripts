import logging
import yaml
from pathlib import Path

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


def _add_color(description, value, color=COLOR_VALUE, sep=": "):
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
    msg = _add_color(label, str(msg), color=COLOR_WARNING)
    if cause:
        logging.exception(msg)
    else:
        logging.error(msg)


def info(msg, label="INFO"):
    msg = str(msg)
    if label:
        msg = _add_color(label, msg)
    logging.info(msg)


def parse_yaml(yaml_file):
    with open(yaml_file) as inp:
        return yaml.safe_load(inp)


def verifiers_in_category(category_info, category):
    categories = category_info["categories"]
    if category not in categories:
        return []
    return [v + ".xml" for v in categories[category]["verifiers"]]


def unused_verifiers(category_info):
    if "not_participating" not in category_info:
        return []
    return category_info["not_participating"]


def get_category_name(set_file) -> str:
    if isinstance(set_file, Path):
        return get_category_name(set_file.name)
    name = set_file
    if name.endswith(".set"):
        name = name[: -len(".set")]
    if "." in name:
        name = ".".join(name.split(".")[1:])
    return name
