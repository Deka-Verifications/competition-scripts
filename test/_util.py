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
    try:
        with open(yaml_file) as inp:
            return yaml.safe_load(inp)
    except yaml.scanner.ScannerError as e:
        logging.error("Exception while scanning %s", yaml_file)
        raise e


def get_archive_name_for_validator(validator_identifier):
    return f"val_{validator_identifier.rsplit('-validate-')[0]}.zip"


def get_archive_name_for_verifier(verifier_identifier):
    return f"{verifier_identifier}.zip"


def verifiers_in_category(category_info, category):
    categories = category_info["categories"]
    selected = categories.get(category, {})
    return [v + ".xml" for v in selected.get("verifiers", [])]


def validators_in_category(category_info, category):
    categories = category_info["categories"]
    selected = categories.get(category, {})
    validators = []
    # Construction of the bench-def.xml is according to this pattern,
    # based on how category-structure.yml names validators:
    # 1. toolname-violation -> toolname-validate-violation-witnesses.xml
    # 2. toolname-correctness -> toolname-validate-correctness-witnesses.xml
    # 3. toolname only -> toolname-validate-witnesses.xml
    for validator in selected.get("validators", []):
        try:
            tool_name, validation_type = validator.rsplit("-")
            validators.append(f"{tool_name}-validate-{validation_type}-witnesses.xml")
        except ValueError:
            tool_name = validator
            validators.append(f"{tool_name}-validate-witnesses.xml")
    return validators


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
