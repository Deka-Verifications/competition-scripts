#! /usr/bin/python3

import sys

if sys.version_info < (3,):
    sys.exit("benchexec.test_tool_info needs Python 3 to run.")

import argparse
import inspect
import os
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
import logging
from benchexec import model, test_tool_info
from benchexec.tools.template import BaseTool2
from subprocess import call
from types import SimpleNamespace
from urllib.request import urlopen, Request, HTTPError

sys.dont_write_bytecode = True  # prevent creation of .pyc files

EXIT_ON_FIRST_ERROR = False  # or collect all errors?


VALIDATOR_SUFFIXES = ["-validate-test-suites"]
BENCHMARK_DEF_TEMPLATE = (
    "https://gitlab.com/sosy-lab/test-comp/bench-defs/raw/master/benchmark-defs/%s.xml"
)
DEF_MISSING_ERROR = "file '%s' not available. Please rename the archive to match an existing benchmark definition, or add a new benchmark definition at 'https://gitlab.com/sosy-lab/test-comp/bench-defs'."


errorFound = False

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


# define some constants for zipfiles,
# needed to get the interesting bits from zipped objects, for further details take a look at
# https://unix.stackexchange.com/questions/14705/the-zip-formats-external-file-attribute/14727#14727
S_IFIFO = 0o010000  # named pipe (fifo)
S_IFCHR = 0o020000  # character special
S_IFDIR = 0o040000  # directory
S_IFBLK = 0o060000  # block special
S_IFREG = 0o100000  # regular
S_IFLNK = 0o120000  # symbolic link
S_IFSOCK = 0o140000  # socket


def toBool(attr, flag):
    """returns whether a flag is set or not"""
    return (attr & (flag << 16)) == (flag << 16)


def getAttributes(infoObject):
    return {
        "named pipe": toBool(infoObject.external_attr, S_IFIFO),
        "special char": toBool(infoObject.external_attr, S_IFCHR),
        "directory": toBool(infoObject.external_attr, S_IFDIR),
        "block special": toBool(infoObject.external_attr, S_IFBLK),
        "regular": toBool(infoObject.external_attr, S_IFREG),
        "symbolic link": toBool(infoObject.external_attr, S_IFLNK),
        "socket": toBool(infoObject.external_attr, S_IFSOCK),
    }


def error(arg, cause=None, label="    ERROR"):
    msg = addColor(label, arg, color=COLOR_WARNING)
    if cause:
        logging.exception(msg)
    else:
        logging.error(msg)
    global errorFound
    errorFound = True
    if EXIT_ON_FIRST_ERROR:
        sys.exit(1)


def info(msg, label="INFO"):
    full_msg = addColor(label, msg)
    logging.info(full_msg)


def checkZipfile(zipfilename):
    assert os.path.isfile(zipfilename)
    try:
        zipcontent = zipfile.ZipFile(zipfilename)
    except zipfile.BadZipfile as e:
        error("zipfile is invalid", cause=e)
        return
    namelist = zipcontent.namelist()
    if not namelist:
        error("zipfile is empty")
        return

    # check whether there is a single root directory for all files.
    rootDirectory = namelist[0].split("/")[0] + "/"
    for name in namelist:
        if not name.startswith(rootDirectory):
            error("file '{}' is not located under a common root directory".format(name))

    # check whether there is a license.
    pattern = re.compile(rootDirectory + "(Licen(s|c)e|LICEN(S|C)E).*")
    if not any(pattern.match(name) for name in namelist):
        error("no license file found")

    # check whether there are unwanted files
    pattern = re.compile(
        ".*(\/\.git\/|\/\.svn\/|\/\.hg\/|\/CVS\/|\/__MACOSX|\/\.aptrelease).*"
    )
    for name in namelist:
        if pattern.match(name):
            error("file '{}' should not be part of the zipfile".format(name))

    # check whether all symlinks point to valid targets
    directories = set(os.path.dirname(f) for f in namelist)
    for infoObject in zipcontent.infolist():
        attr = getAttributes(infoObject)
        if attr["symbolic link"]:
            relativTarget = bytes.decode(zipcontent.open(infoObject).read())
            target = os.path.normpath(
                os.path.join(os.path.dirname(infoObject.filename), relativTarget)
            )
            if not target in directories and not target in namelist:
                error(
                    "symbolic link '{}' points to invalid target '{}'".format(
                        infoObject.filename, target
                    )
                )

    return rootDirectory


def _get_validator_names(toolname):
    return [toolname[4:] + suffix for suffix in VALIDATOR_SUFFIXES]


def _get_potential_definition_names(toolname):
    toolIsValidator = toolname.startswith("val_")
    if toolIsValidator:
        return _get_validator_names(toolname)
    return [toolname]


def checkBenchmarkFile(zipfilename):
    # check that a benchmark definition exists for this tool in the official repository
    toolname = os.path.basename(zipfilename)[:-4]  # remove ending ".zip"
    for toolname in _get_potential_definition_names(toolname):
        benchmark_url = _getBenchmarkUrl(toolname)
        (urlAvailable, request) = _requestBenchmarkDef(benchmark_url)
        if urlAvailable:
            break
    else:
        error(DEF_MISSING_ERROR % benchmark_url)
        return None
    content = request.read()
    benchmarkDefinition = ET.fromstring(content)
    tool = benchmarkDefinition.get("tool")
    return tool


def _requestBenchmarkDef(benchmark_url):
    try:
        r = Request(benchmark_url, headers={"User-Agent": "Mozilla/5.0"})
        request = urlopen(r)
        urlAvailable = request.getcode() == 200
        return (urlAvailable, request)
    except HTTPError:
        return (False, None)


def _getBenchmarkUrl(toolname):
    return BENCHMARK_DEF_TEMPLATE % toolname


def checkToolInfoModule(zipfilename, root_directory, toolname, config):
    with tempfile.TemporaryDirectory(prefix="comp_check_") as tmpdir:
        # lets use the real unzip, because Python may not handle symlinks
        call(["unzip", "-q", "-d", tmpdir, zipfilename])

        toolDir = os.path.join(tmpdir, root_directory)
        try:
            os.chdir(toolDir)
            _checkToolInfoModule(toolname, config)
        finally:
            os.chdir(os.environ["PWD"])


def _checkToolInfoModule(toolname, config):
    try:
        # nice colorful dump, but we would need to parse it
        # test_tool_info.print_tool_info(toolname)

        _, tool = model.load_tool_info(toolname, config)
    except (Exception, SystemExit) as e:
        error(f"loading tool-info for {toolname} failed", cause=e)
        return

    try:
        reported_name = tool.name()
        if not reported_name:
            error("tool '%s' has no name" % toolname)
    except Exception as e:
        error(f"querying tool-name failed for {toolname}", cause=e)
        reported_name = ""
    if not reported_name:
        reported_name = ""

    try:
        # if not inspect.getdoc(tool):
        #     error("tool %s has no documentation" % toolname)
        exe = tool.executable(BaseTool2.ToolLocator(use_path=True, use_current=True))
        if not exe:
            error("tool '%s' has no executable" % toolname)
        if not os.path.isfile(exe) or not os.access(exe, os.X_OK):
            error("tool '%s' with file %s is not executable" % (toolname, exe))
    except Exception as e:
        error(f"querying tool executable failed for {toolname}", cause=e)

    try:
        version = tool.version(exe)
        if not version:
            error("tool '%s' has no version number" % toolname)
        if "\n" in version:
            error(
                "tool '%s' has an invalid version number (newline in version)"
                % toolname
            )
        if len(version) > 100:  # long versions look ugly in tables
            error("tool '%s' has a very long version number" % toolname)
        if version.startswith(reported_name):
            error(
                "tool '%s' is part of its own version number '%s'" % (toolname, version)
            )
    except Exception as e:
        error(f"querying tool version failed for {toolname}", cause=e)
        version = ""
    if not version:
        version = ""

    try:
        programFiles = list(tool.program_files(exe))
        if not programFiles:
            error("tool '%s' has no program files" % toolname)
    except Exception as e:
        error(f"querying program files failed for {toolname}", cause=e)

    label, displayed_name = "     --> ", reported_name + " " + version
    if exe and version:
        info(displayed_name, label=label)
    else:
        error(displayed_name, label=label)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format=None)
    parser = argparse.ArgumentParser()
    parser.add_argument("archive_dir", help="Directory with archive files to check")
    directory = parser.parse_args().archive_dir
    if not os.path.isdir(directory):
        error("directory '{}' not found".format(directory))
        sys.exit(1 if errorFound else 0)

    # dummy config. this script is meant to be executed by the CI,
    # so no need to run it in an extra container:
    config = SimpleNamespace()
    config.container = False

    # check each file in the directory
    for filename in sorted(os.listdir(directory)):
        fullname = os.path.join(directory, filename)
        info(filename, label="CHECKING")
        if not os.path.isfile(fullname):
            error("unexpected file or directory '{}'".format(fullname))
        elif filename.endswith(".zip"):
            rootDirectory = checkZipfile(fullname)
            toolname = checkBenchmarkFile(fullname)
            if toolname:
                checkToolInfoModule(fullname, rootDirectory, toolname, config)
        elif not filename == "README.md":
            error("unexpected file or directory '{}'".format(fullname))

    sys.exit(1 if errorFound else 0)
