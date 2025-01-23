#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "aiofiles",
#     "environs",
#     "jinja2",
#     "lxml",
# ]
# ///
#
# Prepare your environment:

# 1. Install uv from gh://astral/uv if you don't have Python 3.11
#    See more information at https://docs.astral.sh/uv/getting-started/installation/
# 2. Copy the file `.env.example` from the repo to `.env`.
#    If you are on Docserv, this should be fine. You need to adjust either DOCSERV_STITCHFILE or pass it with the option --docserv-stitch-file/-S

# To create index files for all products and docset:

#   $ uv run --python 3.11 bin/build-indexpages.py -o out/
#   [...]

#   You can also specify a higher Python version if you wish.

"""
Script to generate index and homepage pages for the documentation portal

Example output:

  en-us/
     index.html    <- homepage
     product1/
        docset1/
           index.html  <- index page

Requires Python >=3.11
"""

import argparse
import asyncio
import configparser
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cached_property
import time
import json
import itertools
import logging
import logging.handlers
# from logging.config import dictConfig
from pathlib import Path
from operator import attrgetter
import os
import tempfile
from typing import cast, Any, ClassVar, Iterator, Generator, Optional, Self, Sequence
import queue
import re
import shutil
import sys

import aiofiles
from environs import Env

from lxml import etree
from jinja2 import Environment, FileSystemLoader, DebugUndefined
from jinja2.exceptions import TemplateNotFound


__version__ = "0.3.2"
__author__ = "Tom Schraitle"


# --- Constants
DEFAULT_LIFECYCLES = frozenset(("supported", "beta"))
POSSIBLE_LIFECYCLES = frozenset((
    "supported",
    "beta",
    "unsupported",
    "unpublished",
))
DEFAULT_LANGS = ("en-us",)
#: All languages supported by the documentation portal
ALL_LANGUAGES = frozenset(
    "de-de en-us es-es fr-fr ja-jp ko-kr zh-cn".split()
)

PYTHON_VERSION: str = f"{sys.version_info.major}.{sys.version_info.minor}"

# --- Logging
LOGGERNAME = "indexpages"
JINJALOGGERNAME = f"{LOGGERNAME}.jinja"
XPATHLOGGERNAME = f"{LOGGERNAME}.xpath"
GITLOGGERNAME = f"{LOGGERNAME}.git"
#: The log file to use
LOGFILE = f"/tmp/{LOGGERNAME}.log"
#: How many log files to keep
KEEP_LOGS = 4
#: Map verbosity level (int) to log level
LOGLEVELS = {
    None: logging.WARNING,  # fallback
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
}

#: Logging details, see https://docs.python.org/3.11/library/logging.config.html
#
# in order for all messages to be delegated.
logging.getLogger().setLevel(logging.NOTSET)

log = logging.getLogger(LOGGERNAME)
jinjalog = logging.getLogger(JINJALOGGERNAME)
xpathlog = logging.getLogger(XPATHLOGGERNAME)
gitlog = logging.getLogger(GITLOGGERNAME)


# --- Regex for one or more languages, separated by comma:
#: Separator for multiple values
SEPARATOR = re.compile(r"[,; ]")

SINGLE_LANG_REGEX = r'[a-z]{2}-[a-z]{2}'

#: Regex for splitting a path into its components
PRODUCT_REGEX = r"(?P<product>[\w\d_-]+)"  # |\*
DOCSET_REGEX = r"(?P<docset>[\w\d\._-]+|\*)"  # |\*


# --- Handling of .env file
# Inside the parsecli() function we set the default values for the CLI arguments
env = Env()
env.read_env()


# --- Classes and functions
@dataclass
class Metadata:
    """
    A class to represent the metadata of a deliverable
    """
    title: str | None = field(default=None)
    subtitle: str = field(default="")
    #
    seo_title: str | None = field(default=None)
    seo_description: str = field(default="")
    seo_social_descr: str = field(default="")
    #
    dateModified: str = field(default="")
    tasks: list[str] = field(default_factory=list)
    series: str | None = field(default=None)
    rootid: str | None = field(default=None)
    #
    # description: str | None = field(default=None)
    products: list[dict] = field(default_factory=list)
    # docTypes: list[str] | None = field(default=None)
    # archives: list[str] | None = field(default=None)
    # category: str | None = field(default=None)
    #
    _match: ClassVar[re.Pattern] = re.compile(r"\[(.*?)\](.*)")

    def read(self, metafile: Path|str) -> Self:
        """
        Read the metadata from a file
        """
        lines = Path(metafile).open().readlines()
        for line in lines:
            if line.lstrip().startswith("#"):
                continue
            # key, value = line.split("=", 1)
            # key, value = key.strip(), value.strip()
            key, value = map(str.strip, line.split("=", 1))

            match key:
                case "category":
                    if value:
                        self.category = value
                case "title":
                    self.title = value
                case "subtitle":
                    if value:
                        self.subtitle = value
                case "seo-title":
                    if value:
                        self.seo_title = value
                case "seo-social-descr":
                    if value:
                        self.seo_social_descr = value
                case "seo-description":
                    if value:
                        self.seo_description = value
                case "date":
                    if value:
                        self.dateModified = value
                case "rootid":
                    if value:
                        self.rootid = value
                case "tasks":
                    self.tasks = [task.strip() for task in value.split(";")]
                case "productname":
                    if mtch := self._match.match(value):
                        self.products = [{"name": mtch.group(1), "url": mtch.group(2)}]
                case "series":
                    if value:
                        self.series = value

        return self


@dataclass
class Deliverable:
    """
    A class to represent a deliverable
    """
    _node: etree._Element = field(repr=False)
    _metafile: str|None = field(repr=False, default=None)
    _product_node: etree._Element|None = field(repr=False, default=None)
    _meta: Metadata | None = None

    @cached_property
    def productid(self) -> str:
        """Return the product ID"""
        # ancestor::product/@productid
        return list(self._node.iterancestors("product"))[0].attrib.get("productid")

    @cached_property
    def docsetid(self) -> str:
        """Return the docset ID"""
        # ancestor::docset/@setid
        return list(self._node.iterancestors("docset"))[0].attrib.get("setid")

    @cached_property
    def lang(self) -> str:
        """Returns the language and country code (e.g., 'en-us')"""
        # ../../builddocs/language/@lang
        return self._node.getparent().attrib.get("lang").strip()

    @cached_property
    def language(self) -> str:
        """Returns only the language (e.g., 'en')"""
        return re.split(r"[_-]", self.lang)[0]

    @cached_property
    def product_docset(self) -> str:
        """Returns product and docset
        """
        return f"{self.productid}/{self.docsetid}"

    @cached_property
    def pdlang(self) -> str:
        """Product, docset, and language"""
        return f"{self.product_docset}/{self.lang}"

    @cached_property
    def lang_is_default(self) -> bool:
        """Checks if the language is the default language"""
        # ../language/@default
        content = self._node.getparent().attrib.get("default").strip()
        map = {"1": True, "0": False,
               "on": True, "off": False,
               "true": True, "false": False}
        return map.get(content, False)

    @cached_property
    def docsuite(self) -> str:
        """Returns the product, docset, language and the DC filename"""
        return f"{self.pdlang}:{self.dcfile}"

    @cached_property
    def branch(self) -> str|None:
        """Returns the branch where to find the deliverable"""
        # preceding-sibling::branch
        node = self._node.getparent().find("branch")
        if node is not None:
            return node.text.strip()

    @cached_property
    def subdir(self) -> str:
        """Returns the subdirectory inside the repository"""
        # precding-sibling::subdir
        node = self._node.getparent().find("subdir")
        if node is not None:
            return node.text.strip()
        else:
            return ""

    @cached_property
    def git(self) -> str:
        """Returns the git repository"""
        # ../preceding-sibling::git/@remote
        node = self._node.getparent().getparent().find("git")
        if node is not None:
            return node.attrib.get("remote").strip()
        raise ValueError(f"No git remote found for {self.productid}/{self.docsetid}/{self.lang}/{self.dcfile}")

    @cached_property
    def dcfile(self) -> str:
        """Returns the DC filename"""
        # ./dc
        return self._node.find("dc", namespaces=None).text.strip()

    @cached_property
    def format(self) -> dict[str, bool]:
        """Returns the formats of the deliverable"""
        # ./format
        dc = self.dcfile
        # We need to look inside English deliverables for formats
        node = self._node.xpath(
            f"(format|../../language[@lang='en-us']/deliverable[dc[{dc!r} = .]]/format)[last()]"
        )
        if not node:
            raise ValueError(f"No format found for {self.productid}/{self.docsetid}/{self.lang}/{self.dcfile}")

        return {key: convert2bool(value) for key, value in node[0].attrib.items()}

    @cached_property
    def node(self) -> etree._Element:
        """Returns the node of the deliverable"""
        return self._node

    @cached_property
    def productname(self) -> str:
        """Returns the product name"""
        # anecstor::product/name
        return self.product_node.find("name", namespaces=None).text.strip()

    @cached_property
    def acronym(self) -> str:
        """Returns the product acronym"""
        # ancestor::product/acronym
        node = self.docset_node.find("acronym", namespaces=None)
        if node:
            return node
        return ""

    @cached_property
    def version(self) -> str:
        """Returns the version of the docset"""
        # ancestor::docset/version
        return (
            self._node.getparent()
            .getparent()
            .getparent()
            .getparent()
            .find("version")
            .text.strip()
        )

    @cached_property
    def lifecycle(self) -> str:
        """Returns the lifecycle of the docset"""
        # ancestor::docset/@lifecycle
        return self.docset_node.attrib.get("lifecycle")

    #--- Path properties
    @cached_property
    def relpath(self) -> str:
        """Returns the relative path of the deliverable"""
        return f"{self.lang}/{self.product_docset}"

    @cached_property
    def repo_path(self) -> Path:
        """Returns the "slug" path of the repository"""
        return Path(self.git.translate(
            str.maketrans({":": "_", "/": "_", "-": "_", ".": "_"})
        ))

    @cached_property
    def zip_path(self) -> str:
        """Returns the path to the ZIP file"""
        return (
            f"{self.lang}/{self.productid}/{self.docsetid}/"
            f"{self.productid}-{self.docsetid}-{self.lang}.zip"
        )

    def _base_format_path(self, fmt: str) -> str:
        """
        """
        path = "/"
        fallback_rootid = self.dcfile.lstrip("DC-")
        if self.meta is not None:
            rootid = self.meta.rootid
            if rootid is None:
                # Derive rootid from the DC file
                rootid = fallback_rootid
        else:
            rootid = fallback_rootid

        # Suppress English
        if self.lang != "en-us":
            path += f"{self.lang}/"

        path += f"{self.productid}/{self.docsetid}/{fmt}/{rootid}/"
        return path

    @cached_property
    def html_path(self) -> str:
        """
        Returns the path to the HTML directory
        """
        return self._base_format_path("html")

    @cached_property
    def singlehtml_path(self) -> str:
        """
        Returns the path to the single HTML directory
        """
        return self._base_format_path("single-html")

    @cached_property
    def pdf_path(self) -> str:
        """
        Returns the path to the PDF file
        """
        path = "/"
        draft = ""  # TODO
        name = self.dcfile.lstrip("DC-")
        if self.lang != "en-us":
            path += f"{self.lang}/"

        path += (
            f"{self.product_docset}/pdf/"
            f"{name}{draft}_{self.language}.pdf"
        )
        return path

    # --- Node handling
    @cached_property
    def product_node(self) -> etree._Element:
        """Returns the product node of the deliverable"""
        # There is always a <product> node
        return cast(
            etree._Element, self._node.getparent().getparent().getparent().getparent()
        )

    @cached_property
    def docset_node(self) -> etree._Element:
        """Returns the docset node of the deliverable"""
        # There is always a <docset> node
        return cast(etree._Element, self._node.getparent().getparent().getparent())

    @property
    def metafile(self) -> str|None:
        """Returns the metadata file"""
        return self._metafile

    @metafile.setter
    def metafile(self, value: str):
        """Sets the metadata file"""
        self._metafile = value

    @property
    def meta(self) -> Metadata|None:
        """Returns the metadata object of the deliverable"""
        return self._meta

    @meta.setter
    def meta(self, value: Metadata):
        """Sets the metadata content of the deliverable"""
        if not isinstance(value, Metadata):
            raise TypeError(f"Expected type Metadata, but got {type(value)}")
        self._meta = value

    def __hash__(self) -> int:
        return hash(self.docsuite)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(productid={self.productid!r}, "
            f"docsetid={self.docsetid!r}, "
            f"lang={self.lang!r}, "
            f"dcfile={self.dcfile!r})"
        )

    def to_dict(self) -> dict:
        """Return the deliverable as a JSON object"""
        raise NotImplementedError("Not yet implemented")


@contextmanager
def timer(method=time.perf_counter):
    """Measures the time (implemented as context manager)"""
    timer.elapsed_time = None
    start_time = method()
    try:
        yield timer
    finally:
        timer.elapsed_time = method() - start_time


class LifecycleAction(argparse.Action):
    CHOICES = set(("supported", "beta", "unsupported", "unpublished", "all"))
    seen = False

    def __call__(self, parser, namespace, values, option_string=None):
        if self.seen:
            parser.error(f"Option {option_string} can only be specified once. "
                         "Use a comma or semicolon to separate multiple values."
                         )
        self.seen = True
        lifecycles = set([l for l in SEPARATOR.split(values)])

        invalid_lifecycles = lifecycles - self.CHOICES
        if invalid_lifecycles:
            parser.error(f"Invalid lifecycle(s): {invalid_lifecycles}")

        lifecycles = list(lifecycles)
        if "all" in lifecycles:
            setattr(namespace, self.dest, ["all"])
        else:
            if not hasattr(namespace, self.dest):
                setattr(namespace, self.dest, [])
            setattr(namespace, self.dest, lifecycles)


class DocUnitAction(argparse.Action):
    """Parse action for a doc suite productid/docsetid[/lang]"""
    # TODO: Should we take into account lifecycle and the DC file?
    # Allows "sles", "sles/*", "sles/*/en-us", "sles/sle-15-sp3", etc.
    REGEX = re.compile(
        # Watch for the "^" if you use .finditer
        rf"^{PRODUCT_REGEX}(?:/{DOCSET_REGEX}"
        rf"(?:/(?P<lang>{SINGLE_LANG_REGEX}))?)?$"
    )

    def __call__(self, parser, namespace, values: str, option_string=None):
        includes = []
        # We can't use self.REGEX.finditer() here, because a '*' for a product
        # isn't recognized as a valid productid. So we need to split the values
        # and check each part separately.
        for docsuite in SEPARATOR.split(values):
            match = self.REGEX.match(docsuite)
            if not match:
                parser.error(
                    f"Invalid syntax in unit: {docsuite!r}. "
                    f"Use the format 'productid/docsetid[/lang]'"
                )

            lang = match.group("lang")
            if lang is not None and lang not in ALL_LANGUAGES:
                parser.error(
                    f"Invalid language: {lang!r} in {docsuite!r}. "
                    f"(choose from {', '.join(sorted(ALL_LANGUAGES))})"
                )

            includes.append(match.groupdict())

        # Should we check for duplicates? Or just silently ignore them?
        # Should we allow */*/* as a valid unit?

        #if len(includes) != len(set(includes)):
        #    parser.error("Each productid/docsetid unit can occur only once.")

        setattr(namespace, self.dest, includes)


def setup_logging(cliverbosity: int,
                  fmt: str = "[%(levelname)s] %(funcName)s: %(message)s"
):
    """
    Set up loggers and handlers programmatically.
    Adjust the log level of the `jinja_logger` and `xpath_logger` based on verbosity.
    """
    # Ensures that if args.verbose is greater than 2 (==DEBUG), it will be set to DEBUG
    verbosity = LOGLEVELS.get(min(cliverbosity, 2), logging.WARNING)
    jinja_level = LOGLEVELS.get(min(verbosity, len(LOGLEVELS) - 1), logging.INFO)
    xpath_level = LOGLEVELS.get(min(verbosity + 1, len(LOGLEVELS) - 1), logging.INFO)
    git_level = LOGLEVELS.get(min(verbosity + 1, len(LOGLEVELS) - 1), logging.INFO)

    # If verbosity exceeds LOGLEVELS, set additional levels. "-1" for the "None" level
    if verbosity > len(LOGLEVELS) - 1:
        jinja_level = logging.DEBUG
    if verbosity + 1 > len(LOGLEVELS) - 1:
        xpath_level = logging.DEBUG
    if verbosity + 2 > len(LOGLEVELS) - 1:
        git_level = logging.DEBUG

    # Set up a queue to handle logging
    log_queue = queue.Queue(-1)  # no limit on size

    # Create formatters
    standard_formatter = logging.Formatter(fmt)
    git_formatter = logging.Formatter("[%(levelname)s] [Git] - %(message)s")

    # Create handlers
    console_handler = logging.StreamHandler()
    console_handler.setLevel(verbosity)  # Will be updated later
    console_handler.setFormatter(standard_formatter)

    # Create a separate console handler for the git logger with a different formatter
    git_console_handler = logging.StreamHandler()
    git_console_handler.setLevel(git_level)
    git_console_handler.setFormatter(git_formatter)

    # Check if log exists and should therefore be rolled
    needRoll = Path(LOGFILE).exists()

    rotating_file_handler = logging.handlers.RotatingFileHandler(
        LOGFILE,
        backupCount=KEEP_LOGS,
    )
    rotating_file_handler.setLevel(logging.DEBUG)  # Capture all logs to the file
    rotating_file_handler.setFormatter(standard_formatter)

    # Create QueueHandler and QueueListener
    queue_handler = logging.handlers.QueueHandler(log_queue)
    listener = logging.handlers.QueueListener(
        log_queue,
        console_handler, # git_console_handler,
        rotating_file_handler,
        respect_handler_level=True,
    )

    # Start the listener
    listener.start()

    # Set up loggers
    app_logger = logging.getLogger(LOGGERNAME)
    app_logger.setLevel(verbosity)
    app_logger.addHandler(queue_handler)

    jinja_logger = logging.getLogger(JINJALOGGERNAME)
    jinja_logger.setLevel(jinja_level)
    jinja_logger.addHandler(queue_handler)

    xpath_logger = logging.getLogger(XPATHLOGGERNAME)
    xpath_logger.setLevel(xpath_level)
    xpath_logger.addHandler(queue_handler)

    git_logger = logging.getLogger(GITLOGGERNAME)
    git_logger.setLevel(git_level)
    # git_logger.addHandler(queue_handler)
    git_logger.addHandler(git_console_handler)

    # Optional: Disable propagation if needed
    # app_logger.propagate = False
    jinja_logger.propagate = False
    xpath_logger.propagate = False
    git_logger.propagate = False

    # Ensure the listener is stopped properly when the application ends
    import atexit
    atexit.register(listener.stop)

    # This is a stale log, so roll it
    if needRoll:
        # Roll over on application start
        rotating_file_handler.doRollover()


# --- Exceptions
class ConfigError(RuntimeError):
    """A configuration error"""


class GitError(RuntimeError):
    """A custom exception for Git errors"""


class ScriptBaseError(Exception):
    """Base class for all exceptions in this script"""


class DapsError(ScriptBaseError):
    """A custom exception for Daps errors"""


# --- Functions
def convert2bool(value: str | bool) -> bool:
    """Convert a string or bool into a boolean

    :param value: The value to convert to a boolean
        Valid values are: True, "yes", "true", "1", "on" for True and
        False, "no", "false", "0", "off" for False.
    :return: The boolean value
    :raises ValueError: If the value is not a valid boolean
    """
    map = {
        "yes": True,
        "true": True,
        "1": True,
        "on": True,
        "no": False,
        "false": False,
        "0": False,
        "off": False,
    }
    value = str(value).lower()
    if value in map:
        return map[value]

    raise ValueError(f"Invalid boolean value: {value}")


def read_ini_file(inifile: Path, target="doc-suse-com") -> dict[str, Optional[str]]:
    """
    Read an INI file and return its content as a dictionary

    :param inifile: The INI file to be read
    :param target: The target server to focus on
    :return: The configuration dictionary
    """
    config = configparser.ConfigParser()
    config.read(inifile)

    for section in config.sections():
        name = config.get(section, "name", fallback="")
        if name == target:
            log.debug("Found target %r in section %r", target, section)
            break
    else:
        raise ConfigError(f"Target {target!r} not found in INI file {inifile}")

    server = dict(config.items("server"))
    result = dict(config.items(section))
    result.update(repo_dir=server.get("repo_dir", None))
    result.update(temp_repo_dir=server.get("temp_repo_dir", None))

    log.debug("Read INI configuration file %r", str(inifile))
    return result


def is_dir_empty(directory: Path) -> bool:
    """
    Check if the specified directory is empty.

    :param directory: The path to the directory to check.
    :returns: True if the directory is empty, False otherwise.
    :raises ValueError: If the provided path is not a directory.
    """
    if not directory.is_dir():
        raise ValueError(f"The path {directory} is not a directory.")

    return not any(directory.iterdir())


def parsecli(cliargs=None):
    """Parse CLI with :class:`argparse.ArgumentParser` and return parsed result

    :param cliargs: Arguments to parse or None (=use sys.argv)
    :return: parsed CLI result
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Version %s written by %s " % (__version__, __author__),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose",
        action="count",
        default=0,
        help="increase verbosity level",
    )
    parser.add_argument("--version",
        action="version",
        version=(
            f"{__file__}\n"
            f"version {__version__} written by {__author__} "
            f"Using Python {PYTHON_VERSION}"
        ),
        help="shows the version of the script",
    )

    group_path = parser.add_argument_group("Docserv related configuration",
        description="Can also be set in the .env file"
    )
    group_path.add_argument("-D", "--docserv-config-dir",
        # required=True,
        default=env.path("DOCSERV_CONFIG_DIR", None),
        help=("Basic Docserv configuration directory "
              "(contains other directories like 'config.d', 'json-portal-dsc', etc.)"
              )
    )
    group_path.add_argument("-R", "--docserv-repo-base-dir",
        default=env.path("DOCSERV_REPO_BASE_DIR", None),
        help=("Base directory for the repositories "
              "(contains 'permanent-full' and 'temporary-branches' directories)")
    )
    group_path.add_argument("-C", "--docserv-cache-dir",
        default=env.path("DOCSERV_CACHE_DIR", None),
        help="Directory for the cache"
    )
    group_path.add_argument("-I", "--docserv-ini-config",
        default=env.path("DOCSERV_INI_CONFIG", None),
        help=("Path to the Docserv INI configuration file. "
              "Can be omitted, it will be searched in the config directory.")
    )
    group_path.add_argument("-J", "--docserv-json-dir",
        default=env.path("DOCSERV_JSON_DIR", None),
        help=(
            "Directory with JSON files. "
            "Can be omitted, it will be searched in the config directory."
        ),
    )
    group_path.add_argument("-M", "--docserv-daps-meta-dir",
        default=env.path("DOCSERV_DAPS_META_DIR", None),
        help="Directory to store 'daps metadata' output",
    )
    group_path.add_argument("-T", "--docserv-target",
        default=env.str("DOCSERV_TARGET", None),
        help="Target to use in the configuration file",
    )
    group_path.add_argument("-S", "--docserv-stitch-file",
        # required=True,
        default=env.path("DOCSERV_STITCHFILE"),
        help="XML stitch file to use",
    )

    group_build = parser.add_argument_group("Build options")
    group_build.add_argument("-pd", "--include-product-docset",
        default=[],
        action=DocUnitAction,
        help=(
            "Include only specific projects/docsets.\n"
            "Syntax: projectid1/docset1[/lang1][,projectid2/docset2[/lang2]]*"
        )
    )
    group_build.add_argument("-l", "--lifecycle",
                        default=["supported"],
                        action=LifecycleAction,
                        help=("Lifecycle to process (defaults to %(default)r)")
                        )
    group_build.add_argument("-o", "--output-dir",
                        metavar="OUTPUT-DIR",
                        required=True,
                        help="Output directory for the index pages"
    )
    args = parser.parse_args(args=cliargs)
    args.parser = parser

    # Handling of the CLI arguments
    if args.lifecycle == ["all"]:
        args.lifecycle = POSSIBLE_LIFECYCLES

    mappings = {
        "docserv_config_dir": "Missing Docserv configuration directory",
        "docserv_cache_dir": "Missing Docserv cache directory",
        # "docserv_ini_config": "Missing Docserv INI configuration file",
        # "docserv_json_dir": "Missing Docserv JSON directory",
        # "docserv_daps_meta_dir": "Missing Docserv DAPS metadata directory",
        "docserv_repo_base_dir": "Missing Docserv repository base directory",
        "docserv_target": "Missing Docserv target string",
        "docserv_stitch_file": "Missing Docserv stitch file",
    }

    # Test all required arguments if they are None (=not set)
    for key, message in mappings.items():
        if getattr(args, key) is None:
            parser.error(message)

    baseconfigdir = Path(args.docserv_config_dir).expanduser()
    docservconfigdir = baseconfigdir / "config.d"
    args.jinjatemplatedir = baseconfigdir / "jinja-doc-suse-com"
    args.jinja_i18n_dir = baseconfigdir.joinpath("jinja-doc-suse-com", "i18n")
    args.susepartsdir = baseconfigdir.joinpath("jinja-doc-suse-com", "suseparts")
    if args.docserv_ini_config is None:
        args.docserv_ini_config = baseconfigdir / "docserv.ini"

    if args.docserv_json_dir is None:
        args.docserv_json_dir = baseconfigdir / "json-portal-dsc"

    args.docserv_cache_dir = Path(args.docserv_cache_dir)
    if args.docserv_daps_meta_dir is None:
        # If not set, use the cache directory
        args.docserv_daps_meta_dir = args.docserv_cache_dir / "daps-meta"
    else:
        # Convert it to a Path object
        args.docserv_daps_meta_dir = Path(args.docserv_daps_meta_dir)

    # Initialize Jinja environment with None for later use:
    args.jinja_env = None

    for obj in (
        args.docserv_ini_config,
        args.docserv_json_dir,
        args.docserv_stitch_file,
        docservconfigdir,
        args.jinjatemplatedir,
        args.jinja_i18n_dir,
        args.susepartsdir,
        args.docserv_repo_base_dir,
    ):
        if not obj.exists():
            df = "File" if obj.is_dir() else "Dir"
            parser.error(f"{df} {obj} does not exist")

    # Convert the include_product_docset argument into a list of strings
    # that follows the syntax "productid/docsetid/lang".
    # It's the same as Deliverable.pdlang and makes comparison easier.
    args.pdlangs = []
    for item in args.include_product_docset:
        product, docset, lang = item["product"], item["docset"], item["lang"]
        if lang is None:
            # Fallback to the default language
            lang = "en-us"
        args.pdlangs.append(f"{product}/{docset}/{lang}")

    # Setup main logging and the log level according to the "-v" option
    setup_logging(args.verbose)

    # Create the file structure
    args.docserv_daps_meta_dir.mkdir(parents=True, exist_ok=True)

    return args


# --- Jinja filters
def jinja_path_exists(env: Environment, path: str) -> bool:
    """Check if a path exists

    :param env: The Jinja environment
    :param path: The path to check if it exists in template dir
    :returns: True, if the path exists, False otherwise
    """
    for f in env.loader.searchpath:
        jinjalog.debug("Checking if path %r exists in template dir(%r): %s",
                  path,
                  f,
                  Path(f).joinpath(path).exists()
        )
    return any([ Path(f).joinpath(path).exists() for f in env.loader.searchpath])


def jinja_current_dir() -> str:
    """Return the current directory

    :return: The current directory
    """
    jinjalog.debug("Current directory: %s", os.getcwd())
    return os.getcwd()


def init_jinja_template(path: str) -> Environment:
    """Initialize the Jinja templates

    :param path: The path to the Jinja templates
    :return: the Jinja environment, including our own filters
    """
    jinjalog.debug("Initializing Jinja2 templates from %s", path)
    env = Environment(loader=FileSystemLoader(path),
                      trim_blocks=True,
                      lstrip_blocks=True,
                      undefined=DebugUndefined,
                      extensions=['jinja2.ext.debug'],
                      enable_async=True,
                      )
    env.filters['file_exists'] = lambda p: jinja_path_exists(env, p)
    env.filters['current_dir'] = jinja_current_dir
    return env


# --- XML handling
def list_all_deliverables(tree: etree._Element|etree._ElementTree,
                          lifecycle: Sequence|None=None,
                          docsuites:Sequence|None=None,
                          ) -> Generator[etree._Element, None, None]:
    """Generator to list all deliverables from the stitched Docserv config

    :param tree: the XML tree from the stitched Docserv config
    :param lifecycle: The lifecycle(s) to taken care of
    :param docsuite: a list of "docsuite" identifiers
    :yield: a string with the product ID
    """
    xpath_lifecycle = ""
    if lifecycle is not None:
        xpath_lifecycle = " or ".join([f"@lifecycle='{l}'" for l in lifecycle])
        xpath_lifecycle = f"[{xpath_lifecycle}]"

    if docsuites is not None:
        log.debug("Filtering for docset %r", docsuites)
        for suite in docsuites:
            # Gradually build the XPath expression
            p, d, lang = suite["product"], suite["docset"], suite["lang"]
            xpath = (
                f"/*/product[@productid={p!r}]"
                f"/docset{xpath_lifecycle}"
            )
            if d not in (None, "*"):
                xpath += f"[@setid={d!r}]"

            xpath += "/builddocs/language"

            if lang is not None:
                xpath += f"[@lang={lang!r}]"

            xpath += "/deliverable"
            xpathlog.debug("XPath: %r", xpath)
            nodes = tree.xpath(xpath)
            if nodes:
                yield from nodes
            else:
                log.warning("No deliverables found for %r", suite)

    else:
        # TODO: do we need all languages? How to handle non-en-us languages?
        xpath = (
            f"/*/product/docset{xpath_lifecycle}"
            f"/builddocs/language[@lang='en-us']/deliverable"
        )
        xpathlog.debug("XPath: %r", xpath)
        yield from tree.xpath(xpath)


# --- JSON handling
def load_json_from_file(jsonfile: Path) -> dict:
    """
    Load a JSON file and return the content

    :param jsonfile: the file path to the JSON file to load
    :return: the loaded JSON context
    """
    with open(jsonfile) as fh:
        content = json.load(fh)
    return content


# --- Asynchronous functions
async def process_doc_unit(args: argparse.Namespace,
                           deliverable: Deliverable,
                           tmpdir: str | Path) -> tuple[int | None, Metadata]:
    """
    Process a single doc deliverable asynchronously.

    :param args: The command-line arguments.
    :param deliverable: The deliverable object containing metadata.
    :param tmpdir: The temporary directory path.

    :returns: The return code of the Daps command and the Metadata object,
              or None if unsuccessful.
    """
    tmpdir = Path(tmpdir)

    if not tmpdir.exists():
        raise FileNotFoundError(f"Directory {tmpdir} does not exist")

    if not (tmpdir /deliverable.dcfile).exists():
        raise FileNotFoundError(f"File {deliverable.dcfile} does not exist in {tmpdir}")

    # Create the nested structure for the metadata and store it in the deliverable
    # instance
    metadir = (args.docserv_daps_meta_dir
               / deliverable.lang / deliverable.productid / deliverable.docsetid
    )
    metadir.mkdir(parents=True, exist_ok=True)
    metafile = metadir / f"{deliverable.dcfile}.meta"
    deliverable.metafile = metafile

    command = f"daps -d {deliverable.dcfile} metadata --output {metafile}"
    gitlog.debug("Running Daps command %r in %s", command, tmpdir)
    process = await asyncio.create_subprocess_shell(
        command,
        cwd=tmpdir,
        # shell=True,
        env={"LANG": "C", "LC_ALL": "C", "PATH": os.environ["PATH"]},
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, stderr = await process.communicate()

    # We manually convert the bytes into strings:
    stdout = stdout if stdout is None else stdout.decode()
    stderr = stderr if stderr is None else stderr.decode()
    if process.returncode != 0:
        log.error("Daps problem for %r: %s", deliverable.docsuite, stderr)
        raise DapsError(
            f"Daps problem for {deliverable.docsuite}(exit = {process.returncode}): {stderr}"
        )

    gitlog.debug("Daps output: %s", stdout)
    meta = Metadata().read(metafile)

    return process.returncode, meta


##
async def run_command(
    command: str,
    *,
    stdout: int = asyncio.subprocess.PIPE,
    stderr: int = asyncio.subprocess.PIPE,
    env: dict|None = None,
) -> int:
    """
    Runs a command asynchronously, streams output to logging, and returns the return code.

    :param command: The shell command to run.
    :returns: The return code of the command.
    """
    if env is None:
        env = {"LANG": "C", "LC_ALL": "C", "PATH": os.environ["PATH"]}

    process = await asyncio.create_subprocess_shell(
        command,
        stdout=stdout,
        stderr=stderr,
        env=env,
    )

    async def log_stream(stream, level):
        """
        Asynchronously logs the output of a stream line by line.
        """
        async for line in stream:
            gitlog.log(level, line.strip())

    # Run both stdout and stderr logging concurrently
    stdout_task = asyncio.create_task(log_stream(process.stdout, logging.INFO))
    stderr_task = asyncio.create_task(log_stream(process.stderr, logging.ERROR))

    # Wait for the process to complete
    return_code = await process.wait()

    # Ensure all output is logged before returning
    await asyncio.gather(stdout_task, stderr_task)

    gitlog.info(f"Command {command!r} exited with return code {return_code}")
    return return_code

# We are only interested in one command at a time
sem = asyncio.Semaphore(1)

async def log_output(stream: asyncio.StreamReader, repo_name: str | None = None):
    """Log the stream line-by-line
    """
    async with sem:
        result = []
        while True:
            try:
                line = await stream.readuntil(b"\n")
                if line:
                    line = line.decode().strip()
                    result.append(line)
                    gitlog.debug(line)
            except asyncio.IncompleteReadError:
                break
        return "\n".join(result)


async def run_git(command: str, cwd: str|Path| None = None) -> tuple[int, str]:
    """
    Run a git command asynchronously in a specific directory

    :param command: The git command to run.
    :param cwd: The directory where the git command should be executed
    :returns: a tuple with the exit code and the result of the git command
    """
    command = f"git -c color.ui=never -c core.progress=1 {command}"
    gitlog.info("Running git command %r", command)
    process = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        env={
            "LANG": "C",
            "LC_ALL": "C",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PROGRESS_FORCE": "1",
        },
        # Setting this doesn't work; the command isn't called
        # text="True",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    output = await log_output(cast(asyncio.StreamReader, process.stdout))
    returncode = await process.wait()

    return returncode, output


async def update_git_repo(repo: str|Path|None) -> tuple[int|None, str]:
    """
    Update a Git repository asynchronously.

    :param repo: The repo URL or path.
    :returns: a tuple with the exit code or None and the result of the git command
    """
    gitlog.info(f"Updating {repo}")
    command = "fetch --progress --prune"
    result, output = await run_git(command, repo)
    if result:
        raise GitError(f"Error updating {repo}: {output}")

    return result, output


async def clone_git_repo(
    repo: str | Path,
    repopath: str | Path,
    branch: str | None = None,
    default_branch: str = "main",
) -> tuple[int | None, str]:
    """
    Clone a Git repository asynchronously.

    :param repo: The source repo URL or path.
    :param repopath: The target path to clone to.
    :param branch: The branch to clone
    :returns: a tuple with the exit code or None
    """
    command = "clone --progress --quiet "
    gitlog.info(f"Cloning {repo} => {repopath}")
    if branch:
        command += (
            # TODO:
            f"--single-branch --branch {branch} "
            f"--reference {str(repo)} {str(repo)} {str(repopath)} && "
            f"git -C {str(repopath)} checkout {branch}"
        )
    else:
        command += (
            f"--no-single-branch "
            f"--reference {str(repo)} "
            f"{str(repo)} {str(repopath)}"
        )

    result, output = await run_git(command)
    if result:
        raise GitError(f"Error cloning {repo} => {repopath}: {output}")

    return result, output


async def git_worker(
    source: str|Path,
    target: Path,
    branch: str | None = None
) -> tuple[int|None, str]:
    """
    Clone or update a Git repository asynchronously.

    :param source: The source repository URL or path.
    :param target: The target directory path where the repository will
                   be cloned or updated.
    :param branch: The branch to checkout. Defaults to None.
    :returns: A tuple containing the result code (or None) and a status message.
    """
    gitlog.info("Cloning %s => %s...", source, target)

    # We need to check if the target directory is empty
    # as tempdir creates already a directory with a random name
    if target.exists() and not is_dir_empty(target):
        result = await update_git_repo(target)
        gitlog.debug("Finished updating %s", source)
    else:
        result = await clone_git_repo(source, target, branch)
        gitlog.debug("Finished cloning %s", source)

    return result


def create_workdata(tree: etree._Element|etree._ElementTree,
                    #hometmpl: str,
                    #indextmpl: str
) -> dict:
    """
    Create the workdata dictionary for the products

    :param tree: The XML tree node
    :returns: the dictionary of workdata with render arguments
    """
    # Create directories for all products
    workdata = {}
    # Homepage
    workdata[""] = {
        # targetconfig['jinjacontext_home'],
        "meta": "homepage.json",
        # "template": hometmpl,
        "render_args": {},
    }

    for w in tree.xpath("/*/product/@productid"):
        # Handle product exceptions
        if w == "smart":
            jinjacontext = {
                "render_args": {"isSmartDocs": True},
                # "template": indextmpl,
            }
        elif w == "trd":
            jinjacontext = {
                "render_args": {"isTRD": True},
                # "template": indextmpl,
                "meta": "trd_metadata.json",
            }
        elif w == "sbp":
            jinjacontext = {
                "render_args": {"isSBP": True},
                # "template": indextmpl,
            }
        else:
            jinjacontext = {
                "render_args": {"isProduct": True},
                # "template": indextmpl,
            }

        workdata[w] = jinjacontext

    return workdata


async def render_and_write_html(
    tree: etree._Element|etree._ElementTree,
    taskresult: dict,
    args: argparse.Namespace,
):
    """
    Render the Jinja template and write the HTML output to a file.
    """
    env = args.jinja_env
    # products = deliverable.productid
    #requesteddocsets = args.docsets
    #requestedlangs = args.langs
    lifecycle = args.lifecycle
    outputdir = Path(args.output_dir)
    #
    # jsondir = args.jsondir
    jinja_i18n_dir = args.jinja_i18n_dir
    susepartsdir = args.susepartsdir
    indextmpl = env.get_template("index.html.jinja")
    hometmpl = env.get_template("home.html.jinja")
    searchtmpl = env.get_template("search.html.jinja")
    error404tmp = env.get_template("404.html.jinja")

    log.debug("Metafile: %s", deliverable.metafile)
    log.debug("Meta: %s", deliverable.meta)

    workdata = create_workdata(deliverable.node.getroottree(), hometmpl, indextmpl)
    # print(workdata)

    # async with aiofiles.open(output, "w") as fh:
    #     content = await template.render_async(
    #         data=context,
    #         # debug=True,
    #         translations=transdata,
    #         lang=lang.replace("_", "-"),
    #         **render_args,
    #     )
    #     await fh.write(content)


async def worker(deliverable: Deliverable, args: argparse.Namespace) -> dict[Deliverable, bool]:
    """
    Async worker that processes documentation units from the queue.

    :param deliverable: The deliverable object containing product, docset, branch, and language information.
    :param args: The command-line arguments namespace.

    :returns: A dictionary with the deliverable as the key and a boolean indicating success or failure as the value.

    :raises FileNotFoundError: If the specified documentation file is not found in the temporary directory.
    """
    productid, docsetid, branch, lang = (deliverable.productid,
                                   deliverable.docsetid,
                                   deliverable.branch,
                                   deliverable.lang
                                   )
    docsuite = deliverable.docsuite
    result = True

    log.info("Processing %s...", docsuite)
    try:
        # Get the branch
        # TODO: Is that check needed?
        if branch is None:
            log.warning("No branch found for %s/%s => default to 'main'",
                        productid, docsetid)
            branch = "main"

        tmpbasedir = Path(args.docserv_repo_base_dir).joinpath(
            "temporary-branches",
        )
        tmpbasedir.mkdir(parents=True, exist_ok=True)
        tmpdir = Path(tempfile.mkdtemp(
            dir=tmpbasedir,
            prefix=f"{productid}-{docsetid}-{lang}_")
        )
        repopath = Path(args.docserv_repo_base_dir).joinpath(
                        "permanent-full", deliverable.repo_path
        )

        # TODO: Check return value?
        await git_worker(repopath, tmpdir, branch)

        orig_tmpdir = tmpdir
        tmpdir = tmpdir / deliverable.subdir
        if not ( tmpdir / deliverable.dcfile).exists():
            raise FileNotFoundError(f"File {deliverable.dcfile} not found in {tmpdir}")

        _, meta = await process_doc_unit(args, deliverable, tmpdir)

        # Add the metadata to the deliverable object
        deliverable.meta = meta

        # TODO: Need to move it elsewhere
        # await render_and_write_html(deliverable, args)

        # Remove the temporary directory
        log.debug("Removing %s", orig_tmpdir)
        shutil.rmtree(orig_tmpdir)

    except FileNotFoundError as err:
        log.critical("Problem with %s: %s", docsuite, err)
        result = False

    return {deliverable: result}


async def checkout_maintenance_branches(repopath: Path) -> int:
    """
    Checkout all maintenance branches asynchronously

    :param repopath: The path to the local Git repo
    :returns: the exit code
    """
    # Get default branch:
    exitcode, origin = await run_git("remote show")
    if exitcode:
        raise GitError(f"No remote origin found in {repopath}")
    origin = origin.strip()
    gitlog.debug("Remote origin: %r", origin)

    exitcode, branches = await run_git(
        (
            "for-each-ref --format='%(refname:strip=3)' "
            f"refs/remotes/{origin}/maintenance/*"
        ),
        repopath,
    )
    if exitcode:
        raise GitError(f"No maintenance branches found in {repopath}")
    branches = branches.strip()

    for branch in branches.splitlines():
        exitcode, _ = await run_git(f"checkout {branch}", repopath)

    return exitcode


async def process_github_repos(tree: etree._Element|etree._ElementTree,
                               args: argparse.Namespace
) -> list[Deliverable]:
    """
    Process the cloning/updating of GitHub repositories asynchronously

    :param tree: The XML tree of the Docserv configuration
    :param args: The parsed CLI arguments
    :returns: a list of deliverables
    """
    deliverable_queue = []
    repo_urls = set()
    async with asyncio.TaskGroup() as tg:
        for deliverable in list_all_deliverables(
            tree, args.lifecycle, args.include_product_docset
        ):
            deli = Deliverable(deliverable)

            if deli.git is None:
                log.warning(
                    "No Git information found for %s/%s", deli.productid, deli.docsetid
                )
                continue

            deliverable_queue.append(deli)
            if deli.git in repo_urls:
                # Don't clone already existing repos
                continue
            repo_urls.add(deli.git)
            repopath = Path(args.docserv_repo_base_dir).joinpath(
                "permanent-full", deli.repo_path
            )
            tg.create_task(git_worker(deli.git, repopath), name="git_worker")
            # tg.create_task(checkout_maintenance_branches(repopath),
            # name="git-checkout")

    return deliverable_queue


async def process_retrieve_metadata(
    deliverables: list[Deliverable], args: argparse.Namespace
) -> list[asyncio.Task[Any]]:
    """
    Retrieve metadata from the DAPS command

    :param deliverables: a list of deliverables to run "daps metadata" against
    :param args: The parsed CLI argument
    :returns: a list of future asyncio.Task objects
    """
    log.info("Processing deliverables...")
    process_results = []
    async with asyncio.TaskGroup() as tg:
        for deliverable in deliverables:
            task = tg.create_task(worker(deliverable, args),
                                  name="worker")
            process_results.append(task)

    return process_results


async def create_archive():
    """
    Create ZIP archive (not implemented yet)
    """
    raise NotImplementedError("create_archive not implemented yet")


async def worker_collect_metadata(
    tree: etree._Element | etree._ElementTree,
    group: str,
    deliverables: list[Deliverable], # type: ignore
    args: argparse.Namespace,
):
    """
    Worker function to collect metadata

    :param tree: The XML tree from the stitched Docserv config
    :param group: The group of deliverables to process
    :param deliverables: The deliverables belonging to the same product,
                         docset, and  language to process
    :param args: The command-line arguments namespace
    """
    deliverables: list[Deliverable] = list(deliverables)
    product, docset, lang = group.split("/")
    log.debug("Found %d deliverables for %s", len(deliverables), group)

    json_base_cache_dir = args.docserv_cache_dir / "json"

    product_node = tree.xpath(f"/*/product[@productid={product!r}]")[0]
    docset_node = product_node.xpath(f"docset[@setid={docset!r}]")[0]

    # TODO: FutureWarning: The behavior of this method will change in future versions. Use specific 'len(elem)' or 'elem is not None' test instead.
    version = docset_node.find("listingversion") or docset_node.find("version")
    if version is None:
        version = "???"
    else:
        version = version.text

    result = {}
    resultdict = {
        "productname": product_node.find("name").text,
        "acronym": product_node.find("acronym").text,
        "version": version,
        "hide-productname": False,
        "lifecycle": docset_node.attrib.get("lifecycle"),
        "descriptions": [],
        "archives": [],
        "documents": [],
    }

    productid = deliverables[0].productid
    for desc in tree.xpath(f"/*/product[@productid={productid!r}]/desc"):
        lang = desc.get("lang", "en-us")
        is_default = convert2bool(desc.get("default", "0"))

        # Collect the content of <desc>, excluding <title>
        description_parts = []
        for element in desc.iterchildren():
            if element.tag != "title":
                description_parts.append(etree.tostring(element, encoding="unicode"))

        resultdict["descriptions"].append(
            {
                "lang": lang,
                "default": is_default,
                "description": "\n".join(description_parts),
            }
        )

    log.info("Processing group %s...", group)

    for deli in deliverables:
        log.info("Processing %s...", deli.docsuite)

        if deli.meta is None:
            log.error("No metadata found for %s", deli.docsuite)
            deli.meta = Metadata()

        formats = {}
        if deli.format.get("html", False):
            formats["html"] = deli.html_path
        if deli.format.get("pdf", False):
            formats["pdf"] = deli.pdf_path
        if deli.format.get("single-html", False):
            formats["single-html"] = deli.singlehtml_path

        document = {}
        document.setdefault("docs", []).append(
            {
            "lang": deli.lang,
            "default": deli.lang_is_default,
            "title": deli.meta.title,
            "subtitle": deli.meta.subtitle,
            "description": deli.meta.seo_description,
            "dcfile": deli.dcfile,
            "formats": formats,
            "dateModified": deli.meta.dateModified,
        }
        )
        document.setdefault("tasks", deli.meta.tasks)
        document.setdefault("products", deli.meta.products)
        document.setdefault("docTypes", [])
        document.setdefault("isGated", False)
        document.setdefault("rank", "")

        resultdict.setdefault("documents", []).append(document)

    # log.debug("Result for %s: %s", group, resultdict)

    try:
        json_cache_dir = json_base_cache_dir / deli.lang / deli.productid
        json_cache_dir.mkdir(parents=True, exist_ok=True)
        jsonfile = json_cache_dir / f"{deli.docsetid}.json"
        async with aiofiles.open(jsonfile, "w") as fh:
            await fh.write(json.dumps(resultdict, indent=2))
        log.debug("Wrote JSON file %s", jsonfile)
        result[deli.docsuite] = True
        result["productid"] = deli.productid
        result["lang"] = deli.lang
        result["pdlang"] = deli.pdlang
        result["relpath"] = deli.relpath
        result['json'] = resultdict

    except (IOError, TypeError) as err:
        log.fatal("Error writing JSON file %s: %s", jsonfile, err)
        result[deli.docsuite] = False
        result["productid"] = deli.productid
        result["lang"] = deli.lang
        result["pdlang"] = deli.pdlang
        result["relpath"] = deli.relpath
        result["json"] = None

    return result



async def process_collect_metadata(tree: etree._Element|etree._ElementTree,
                                   deliverables: list[Deliverable],
                                   args: argparse.Namespace
) -> list[asyncio.Task[Any]]:
    """Group all deliverables by their product ID, docset ID, and language
       and collect the metadata

    :param tree: the XML tree object from the Docserv configuration
    :param deliverables: a list of deliverables to group
    :param args: the parsed CLI object
    """
    # log.info("Collecting metadata...")
    process_results = []

    # We need to group all deliverables into the same product, docset, and language
    # combination.
    # Sort and group by pdlang
    async with asyncio.TaskGroup() as tg:
        for group, items in itertools.groupby(
            sorted(deliverables, key=attrgetter('pdlang')),
            key=attrgetter('pdlang')
        ):
            items = list(items)
            task = tg.create_task(worker_collect_metadata(tree,
                                                          group,
                                                          items,
                                                          args),
                                  name="worker_collect_metadata")
            process_results.append(task)

    return process_results


async def main(cliargs=None):
    """
    Main function to process deliverables and clone/update GitHub repositories.

    :param cliargs: Optional command line arguments. Defaults to None.

    :returns: Exit code indicating the result of the execution.
        0 - Success
        5 - SystemExit
        10 - Interrupted by user
        20 - ValueError
        50 - FileNotFoundError
        100 - JSONDecodeError
        200 - GitError

    :raises GitError: If there is an error related to Git operations.
    :raises json.JSONDecodeError: If there is an error decoding a JSON file.
    :raises FileNotFoundError: If a required file is not found.
    :raises ValueError: If there is a value error.
    :raises KeyboardInterrupt: If the process is interrupted by the user.
    :raises SystemExit: If the system exits unexpectedly.
    """
    process_results = []
    try:
        args = parsecli(cliargs)
        # allow the logger to start
        await asyncio.sleep(0)
        log.info("=== Starting ===")
        args.config = read_ini_file(args.docserv_ini_config)

        with timer() as t:
            log.debug("Arguments: %s", args)

            tree = etree.parse(args.docserv_stitch_file, etree.XMLParser())
            # Seems not to be very efficient as I have to iterate over the list
            # of deliverables twice:
            # first to get the Git URLs and then to process them.
            # Second iteration is done in the worker function.
            #
            # Step 1: Get the deliverables and the Git URLs
            deliverables = await process_github_repos(tree, args)

            # Add repo URLs to the repo queue
            # log.info("Cloning/updating GitHub repos...")
            args.jinja_env = init_jinja_template(args.jinjatemplatedir.absolute())

            # Step 2: Process the deliverables with "daps metadata"
            p = await process_retrieve_metadata(deliverables, args)
            process_results.extend(p)

            # Step 3: Collect metadata
            p = await process_collect_metadata(tree, deliverables, args)
            # process_results.extend(p)
            # process_output = [task.result() for task in p]
            # log.debug("Process output for metadata: %s", process_output)

            for task in p:
                result = task.result()
                await render_and_write_html(
                    tree,
                    result,
                    args,
                )

            # process_output = [task.result() for task in process_results]
            successes = 0
            failures = 0
            failed_tasks = []
            for task in process_results:
                x: dict[Deliverable, bool] = await task
                deli, result = x.popitem()
                if result:
                    successes += 1
                else:
                    failures += 1
                    failed_tasks.append(deli)

            log.info("=== Summary (%i tasks): %i successful, %i failed",
                     successes + failures,
                     successes, failures)

            for deli in failed_tasks:
                log.error("Failed deliverable: %s", deli.docsuite)

        log.info("Elapsed time: %0.3f seconds", t.elapsed_time)

    except GitError as e:
        log.critical(e)
        return 200

    except json.JSONDecodeError as err:
        log.error("Error decoding JSON file %s\nAbort.", err)
        return 100

    except FileNotFoundError as err:
        log.error("File not found: %s.\nAbort", err)
        return 50

    except ValueError as e:
        log.error(e)
        return 20

    except (KeyboardInterrupt): # , asyncio.CancelledError
        log.error("Interrupted by user")
        return 10

    except SystemExit:
        return 5

    finally:
        # log.info("Elapsed time: %0.3f seconds", t.elapsed_time)
        log.info("=== Finished ===")

    return 0


if __name__ == "__main__":
    # sys.exit(main())
    sys.exit(
        asyncio.run(main(),
                    # debug=True
                    )
    )
