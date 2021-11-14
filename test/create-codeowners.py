#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys
import _util as util
from collections import defaultdict


def parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-directory",
        default=".",
        help="base directory to use for CODEOWNERS file",
    )
    parser.add_argument(
        "category_structure",
        help="category-structure.yml to use",
    )
    args = parser.parse_args(argv)

    args.category_structure = Path(args.category_structure)
    args.base_directory = Path(args.base_directory)
    missing_files = [
        f for f in [args.category_structure, args.base_directory] if not f.exists()
    ]
    if missing_files:
        raise ValueError(
            f"File(s) do not exist: {','.join([str(f) for f in missing_files])}"
        )
    return args


def _tool_to_gitlab_handle(category_info):
    tool_to_handles = defaultdict(set)
    for tool, metadata in category_info["verifiers"].items():
        gitlab_handle = metadata["jury-member"]["gitlab"]
        archive = util.get_archive_name_for_verifier(tool)
        tool_to_handles[archive].add(gitlab_handle)
    for tool, metadata in category_info["validators"].items():
        gitlab_handle = metadata["jury-member"]["gitlab"]
        archive = util.get_archive_name_for_validator(tool)
        tool_to_handles[archive].add(gitlab_handle)
    return tool_to_handles.items()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    category_info = util.parse_yaml(args.category_structure)
    print("[Participants]")
    for archive, gitlab_handles in _tool_to_gitlab_handle(category_info):
        gitlab_handles = " ".join(f"@{handle}" for handle in gitlab_handles)
        relevant_files = [
            f.relative_to(args.base_directory)
            for f in args.base_directory.glob(f"**/{archive}")
        ]
        assert relevant_files, f"No files found for {args.base_directory}/**/{archive}"
        for f in relevant_files:
            print(f"{f} {gitlab_handles}")


if __name__ == "__main__":
    sys.exit(main())
