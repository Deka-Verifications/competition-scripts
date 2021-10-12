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


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("config_file", help="config.yml to parse")
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
    args = parser.parse_args(argv)

    if not any((args.get_comp, args.get_year, args.get_year_abbrev)):
        print("Nothing to do", file=sys.stderr)
        return 1

    with open(args.config_file, encoding="UTF-8") as inp:
        config = yaml.safe_load(inp)

    if args.get_comp:
        print_competition(config)
    if args.get_year or args.get_year_abbrev:
        print(year(config, abbrev=args.get_year_abbrev))


if __name__ == "__main__":
    sys.exit(main())
