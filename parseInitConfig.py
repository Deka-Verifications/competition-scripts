#!/usr/bin/env python3

# This file is part of the competition environment.
#
# SPDX-FileCopyrightText: 2011-2020 Dirk Beyer <https://www.sosy-lab.org>
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import sys
import yaml


def print_competition(config):
    print(config["competition"])


def year(config, abbrev=False) -> str:
    year = config["year"]
    if abbrev:
        return str(year)[-2:]
    return str(year)


def participant_table(config, yaml_key="verifiers") -> str:
    columns = {
        "id": lambda k, _: k,
        "name": lambda _, d: d.get("name", ""),
        "lang": lambda _, d: d.get("lang", ""),
        "url": lambda _, d: d.get("url", ""),
        "required-ubuntu-packages": lambda _, d: ",".join(
            d.get("required-ubuntu-packages", [])
        ),
        "jury-member-name": lambda _, d: d.get("jury-member", {}).get("name", ""),
        "jury-member-institution": lambda _, d: d.get("jury-member", {}).get(
            "institution", ""
        ),
        "jury-member-country": lambda _, d: d.get("jury-member", {}).get("country", ""),
        "jury-member-url": lambda _, d: d.get("jury-member", {}).get("url", ""),
    }
    table = ["\t".join(columns.keys())]
    for key, metadata in config[yaml_key].items():
        structured_data = [columns[c](key, metadata) for c in columns]
        metadata_as_tsv = "\t".join([e if e else "" for e in structured_data])
        table.append(metadata_as_tsv)
    return "\n".join(table)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("config_file", help="category-structure.yml to parse")
    parser.add_argument(
        "--get-comp", action="store_true", default=False, help="get competition"
    )
    parser.add_argument(
        "--get-year",
        action="store_true",
        default=False,
        help="get year in four digits (YYYY)",
    )
    parser.add_argument(
        "--get-year-abbrev",
        action="store_true",
        default=False,
        help="get year in two digits (YY)",
    )
    parser.add_argument(
        "--get-participant-table",
        action="store_true",
        default=False,
        help="get tab-separated table of participant metadata",
    )
    parser.add_argument(
        "--get-validator-table",
        action="store_true",
        default=False,
        help="get tab-separated table of validator metadata",
    )
    args = parser.parse_args(argv)

    if not any(
        (
            args.get_comp,
            args.get_year,
            args.get_year_abbrev,
            args.get_participant_table,
            args.get_validator_table,
        )
    ):
        print("Nothing to do", file=sys.stderr)
        return 1

    with open(args.config_file, encoding="UTF-8") as inp:
        config = yaml.safe_load(inp)

    if args.get_comp:
        print_competition(config)
    if args.get_year or args.get_year_abbrev:
        print(year(config, abbrev=args.get_year_abbrev))
    if args.get_participant_table:
        print(participant_table(config))
    if args.get_validator_table:
        print(participant_table(config, yaml_key="validators"))


if __name__ == "__main__":
    sys.exit(main())
