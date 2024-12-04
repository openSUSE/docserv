#!/usr/bin/env python3
"""
Script to generate index and homepage pages for the documentation portal

For example:

  en-us/
     index.html    <- homepage
     product1/
        docset1/
           index.html  <- index page

"""

import argparse
import asyncio
import configparser
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import StrEnum
import time
import json
import itertools
import logging
import logging.handlers
# from logging.config import dictConfig
from pathlib import Path
import os
from typing import Any, Dict, Optional, Sequence
import queue
import re
import shlex
import sys

import aiofiles
from environs import Env

from lxml import etree
from jinja2 import Environment, FileSystemLoader, DebugUndefined
from jinja2.exceptions import TemplateNotFound


__version__ = "0.3.1"
__author__ = "Tom Schraitle"

# --- Constants
DEFAULT_LIFECYCLES = ("supported", "beta")
POSSIBLE_LIFECYCLES = (
    "supported",
    "beta",
    "unsupported",
    "unpublished",
)
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
#: The log file to use
LOGFILE = "/tmp/indexpages.log"
#: How many log files to keep
KEEP_LOGS = 4
#: Map verbosity level (int) to log level
LOGLEVELS = {
    None: logging.WARNING,  # fallback
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
}

#: The dictionary, passed to :class:`logging.config.dictConfig`,
#: is used to setup your logging formatters, handlers, and loggers
#: For details, see https://docs.python.org/3.4/library/logging.config.html#configuration-dictionary-schema
DEFAULT_LOGGING_DICT = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {
        "standard": {"format": "[%(levelname)s] %(funcName)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "NOTSET",  # will be set later
            "formatter": "standard",
            "class": "logging.StreamHandler",
        },
        "file": {
            "level": "DEBUG",  # we want all in the log file
            "formatter": "standard",
            "class": "logging.FileHandler",
            "filename": LOGFILE,
            "mode": "w",
        },
    },
    "loggers": {
        LOGGERNAME: {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            # 'propagate': True
        },
        JINJALOGGERNAME: {
            "handlers": ["console", "file"],
            "level": "INFO",
            # 'propagate': True
        },
        XPATHLOGGERNAME: {
            "handlers": ["console", "file"],
            "level": "INFO",
            # 'propagate': True
        },
        "": {
            "level": "NOTSET",
        },
    },
}

# in order for all messages to be delegated.
logging.getLogger().setLevel(logging.NOTSET)

log = logging.getLogger(LOGGERNAME)
jinjalog = logging.getLogger(JINJALOGGERNAME)
xpathlog = logging.getLogger(XPATHLOGGERNAME)


# --- Regex for one or more languages, separated by comma:
#: Separator for multiple values
SEPARATOR = re.compile(r"[,; ]")

SINGLE_LANG_REGEX = r'[a-z]{2}-[a-z]{2}'

#: Regex for splitting a path into its components
PRODUCT_REGEX = r"(?P<product>[\w\d_-]+)"  # |\*
DOCSET_REGEX = r"(?P<docset>[\w\d\._-]+)"  # |\*


# --- Handling of .env file
# Inside the parsecli() function we set the default values for the CLI arguments
env = Env()
env.read_env()


# --- Classes and functions
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
    REGEX = re.compile(
        # Watch for the "^" if you use .finditer
        rf"^{PRODUCT_REGEX}/{DOCSET_REGEX}"
        rf"(?:/(?P<lang>{SINGLE_LANG_REGEX}))?"
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

    # If verbosity exceeds LOGLEVELS, set additional levels. "-1" for the "None" level
    if verbosity > len(LOGLEVELS) - 1:
        jinja_level = logging.DEBUG
    if verbosity + 1 > len(LOGLEVELS) - 1:
        xpath_level = logging.DEBUG

    # Set up a queue to handle logging
    log_queue = queue.Queue(-1)  # no limit on size

    # Create formatters
    standard_formatter = logging.Formatter(fmt)

    # Create handlers
    console_handler = logging.StreamHandler()
    console_handler.setLevel(verbosity)  # Will be updated later
    console_handler.setFormatter(standard_formatter)

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
        console_handler, rotating_file_handler,
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

    # Optional: Disable propagation if needed
    # app_logger.propagate = False
    jinja_logger.propagate = False
    xpath_logger.propagate = False

    # Ensure the listener is stopped properly when the application ends
    def stop_listener():
        listener.stop()

    import atexit
    atexit.register(stop_listener)

    # This is a stale log, so roll it
    if needRoll:
        # Roll over on application start
        rotating_file_handler.doRollover()


async def run_command(command: str) -> int:
    """
    Runs a command asynchronously, streams output to logging, and returns the return code.

    Args:
        command: The shell command to run.

    Returns:
        The return code of the command.
    """
    process = await asyncio.create_subprocess_shell(
        shlex.quote(command),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    async def log_stream(stream, level):
        """
        Asynchronously logs the output of a stream line by line.
        """
        async for line in stream:
            log.log(level, line.strip())

    # Run both stdout and stderr logging concurrently
    stdout_task = asyncio.create_task(log_stream(process.stdout, logging.INFO))
    stderr_task = asyncio.create_task(log_stream(process.stderr, logging.ERROR))

    # Wait for the process to complete
    return_code = await process.wait()

    # Ensure all output is logged before returning
    await asyncio.gather(stdout_task, stderr_task)

    log.info(f"Command {command!r} exited with return code {return_code}")
    return return_code


async def run_git(command: str, cwd: Path|None = None) -> int|None:
    """
    Run a git command asynchronously in a specific directory

    Args:
        command: The git command to run.
        cwd: The directory where the git command should be
    """
    log.info("Running git command %r in %r", command, cwd)
    process = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        env={"LANG": "C", "LC_ALL": "C"},
        # Setting this doesn't work; the command isn't called
        # text="True",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    # We manually convert the bytes into strings:
    stdout = stdout if stdout is None else stdout.decode()
    stderr = stderr if stderr is None else stderr.decode()
    log.debug(
        "Results of git clone: %s %s => %i",
        stdout,
        stderr,
        process.returncode,
    )
    if process.returncode != 0:
        log.error(stderr)
    # log.debug(stdout)
    return process.returncode


def read_ini_file(inifile: Path, target="doc-suse-com") -> dict[str, Optional[str]]:
    """
    Read an INI file and return its content as a dictionary
    """
    config = configparser.ConfigParser()
    config.read(inifile)

    for section in config.sections():
        name = config.get(section, "name", fallback="")
        if name == target:
            log.debug("Found target %r in section %r", target, section)
            break
    else:
        raise RuntimeError(f"Target {target!r} not found in INI file {inifile}")

    server = dict(config.items("server"))
    result = dict(config.items(section))
    result.update(repo_dir=server.get("repo_dir", None))
    result.update(temp_repo_dir=server.get("temp_repo_dir", None))

    log.debug("Read INI configuration file %r", str(inifile))
    return result


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

    # Setup main logging and the log level according to the "-v" option
    setup_logging(args.verbose)

    return args


def jinja_path_exists(env, path: str) -> bool:
    """Check if a path exists"""
    for f in env.loader.searchpath:
        jinjalog.debug("Checking if path %r exists in template dir(%r): %s",
                  path,
                  f,
                  Path(f).joinpath(path).exists()
        )
    return any([ Path(f).joinpath(path).exists() for f in env.loader.searchpath])


def jinja_current_dir() -> str:
    """Return the current directory"""
    jinjalog.debug("Current directory: %s", os.getcwd())
    return os.getcwd()


def init_jinja_template(path: str) -> Environment:
    """Initialize the Jinja templates"""
    jinjalog.debug("Initializing Jinja2 templates from %s", path)
    env = Environment(loader=FileSystemLoader(path),
                      trim_blocks=True,
                      lstrip_blocks=True,
                      undefined=DebugUndefined,
                      extensions=['jinja2.ext.debug']
                      )
    env.filters['file_exists'] = lambda p: jinja_path_exists(env, p)
    env.filters['current_dir'] = jinja_current_dir
    return env


def list_all_products(tree: etree._Element|etree._ElementTree,
                      lifecycle: Sequence|None=None,
                      docsuite=None,
                      ):
    """List all products

    :param tree: the XML tree from the stitched Docserv config
    :param docsuite: a list of
    :yield: a string with the product ID
    """
    if docsuite is not None:
        log.debug("Filtering for docset %r", docsuite)
        for suite in docsuite:
            p, d, l = suite["product"], suite["docset"], suite["lang"]
            xpath = (
                f"/*/product[@productid={p!r}]/docset[@setid={d!r}]"
            )
            if l is not None:
                xpath += f"[builddocs/language/@lang={l!r}]"
            xpathlog.debug("XPath: %r", xpath)
            node = tree.xpath(xpath)
            if node:
                yield node[0]

            # -------
            # p = suite["product"]
            # xpath = f"/*/product[@productid={p!r}]"
            # xpathlog.debug("XPath: %r", xpath)
            # if tree.xpath(xpath):
            #     yield p

    else:
        # Replaces list-all-products.xsl
        # for product in tree.iter("product"):
        #     productid = product.attrib.get("productid", None)
        #     if productid:
        #         yield productid
        for docset in tree.iter("docset"):
            if docset.attrib.get("lifecycle") in lifecycle:
                yield docset



def get_docsets_from_product(tree, productid, lifecycle):
    """
    Get all docsets from a product
    """
    xpath = f"./product[@productid={productid!r}]/"
    if lifecycle:
        lc=" or ".join([f"@lifecycle={lc!r}" for lc in lifecycle])
        xpath += f"docset[{lc}]"
    else:
        xpath += f"docset"
    log.debug("XPath: %s", xpath)
    yield from tree.xpath(xpath)


def get_translations(tree: etree._Element|etree._ElementTree,
                     product: str,
                     docset: str|None,
                     lifecycle) -> list[str]:
    """
    Get all translations for a specific product/docset

    :param tree: the XML tree of the stitched Docserv config
    :param product: the product ID
    :param docset: the docset ID
    :return: a list of all translations
    """
    # xpath = f"./builddocs/language/@lang | ./external/link/language/@lang"
    xpath = f"/*/product[@productid={product!r}]/docset"
    if docset:
        xpath += f"[@setid={docset!r}]"
    if lifecycle:
        lc=" or ".join([f"@lifecycle={lc!r}" for lc in lifecycle])
        xpath += f"[{lc}]"

    # xpath += f"{docsetxpath}"
    docset = tree.xpath(xpath)
    xpathlog.debug("XPath: %s => %i", xpath, len(docset))
    if not docset:
        log.error("No docset found for product=%r docset=%r with lifecylce=%s",
                  product, docset, lifecycle)
        return []

    xpath = f"./builddocs/language/@lang | ./external/link/language/@lang"
    xpathlog.debug("XPath: %s", xpath)
    return list(set(docset[0].xpath(xpath)))


def iter_product_docset_lang(tree, products, requested_docsets, lifecycle):
    """
    Iterate over all products, docsets, and languages
    """
    for product in products:
        for docsetelement in get_docsets_from_product(tree, product, lifecycle):
            docset = docsetelement.attrib.get("setid")
            if requested_docsets and docset not in requested_docsets:
                log.debug("Skipping docset %r", docset)
                continue
            #for lang in get_translations(tree, product, docset, lifecycle):
            yield product, docset


def load_json_from_file(jsonfile: Path) -> dict:
    """
    Load a JSON file and return the content
    """
    with open(jsonfile) as fh:
        content = json.load(fh)
    return content


def render(args, tree, env):
    """
    Render the index pages
    """
    products = args.products
    requesteddocsets = args.docsets
    requestedlangs = args.langs
    lifecycle = args.lifecycle
    outputdir = Path(args.output_dir)
    #
    jsondir = args.jsondir
    jinja_i18n_dir = args.jinja_i18n_dir
    susepartsdir = args.susepartsdir
    indextmpl = env.get_template("index.html.jinja")
    hometmpl = env.get_template("home.html.jinja")
    searchtmpl = env.get_template("search.html.jinja")
    error404tmp = env.get_template("404.html.jinja")

    log.info("""Variables used:
         products: %s
 requesteddocsets: %s
        lifecycle: %s
   requestedlangs: %s
        outputdir: %s
          jsondir: %s
   jinja_i18n_dir: %s
     susepartsdir: %s
""",
products, requesteddocsets, lifecycle, requestedlangs, outputdir, jsondir, jinja_i18n_dir, susepartsdir
    )

    # Create output directory:
    outputdir.mkdir(parents=True, exist_ok=True)

    # Create directories for all products
    workdata = {}
    # Homepage
    workdata[""] = {
            # targetconfig['jinjacontext_home'],
            "meta": "homepage.json",
            "template": hometmpl,
            "render_args": {},
        }

    for w in list_all_products(tree):
        # Handle product exceptions
        if w == "smart":
            jinjacontext = {
                "render_args": {"isSmartDocs": True},
                "template": indextmpl,
                }
        elif w == "trd":
            jinjacontext = {
                "render_args": {"isTRD": True},
                "template": indextmpl,
                "meta": "trd_metadata.json"
                }
        elif w == "sbp":
            jinjacontext = {
                "render_args": {"isSBP": True},
                "template": indextmpl,
                }
        else:
            jinjacontext = {
                "render_args": {"isProduct": True},
                "template": indextmpl,
                }

        workdata[w] = jinjacontext

    # If we don't have defined any products, use all products
    if not products:
        products = [p for p in workdata.keys() if p]

    for (product, docset), lang in itertools.product(
        iter_product_docset_lang(tree, products, requesteddocsets, lifecycle),
        requestedlangs
    ):
        log.debug("Processing product=%r for docset=%r lang=%r",
                    product, docset, lang)
        path = outputdir / lang / product / docset
        transfile = jinja_i18n_dir / f"{lang.replace('-', '_')}.json"
        jsonfile = jsondir / product / f"{docset}.json"
        template = workdata[product]["template"]
        args = workdata[product]["render_args"]

        if susepartsdir.joinpath(f"head_{lang}.html").exists():
            log.debug("Found head file for lang=%r", lang)
        else:
            log.warning("Head file for lang=%r not found", lang)

        # Load translation file
        try:
            # TODO: It is loaded multiple times. Certainly there are
            # better ways to do this.
            transdata = load_json_from_file(transfile)
            log.debug("Successfully loaded translation file %r", transfile)
        except FileNotFoundError as err:
            transfile = jinja_i18n_dir / "en_us.json"
            transdata = load_json_from_file(transfile)
            log.info("Fallback to English for lang=%r", lang)

        try:
            context = load_json_from_file(jsonfile)
            log.debug("Successfully loaded JSON context %r", jsonfile)
        except FileNotFoundError as err:
            log.error("Error loading JSON file %s. Continue with next product/docset", err)
            continue

        # Create the output directory
        os.makedirs(path, exist_ok=True)
        output = Path(path) / "index.html"

        with open(output, "w") as fh:
            content = template.render(data=context,
                                        # debug=True,
                                        translations=transdata,
                                        lang=lang.replace("_", "-"),
                                        **args)
            fh.write(content)
        log.debug("Wrote %s with args=%s", output, args)


    # Load the homepage.json as context
    homepagejsonfile = jsondir / "homepage.json"
    with open(homepagejsonfile) as fh:
        homepagecontext = json.load(fh)
    log.debug("Successfully loaded JSON context %r", homepagejsonfile)


    for product, lang in itertools.product(products, requestedlangs):
        transfile = jinja_i18n_dir / f"{lang.replace('-', '_')}.json"
        try:
            transdata = load_json_from_file(transfile)
        except FileNotFoundError:
            # Use English as fallback if the translation cannot be found:
            log.warning("Translation file for %s not found. Using English as fallback", lang)
            transdata = load_json_from_file(jinja_i18n_dir / "en_us.json")

        firstleveldata = {
            "index.html": {
                "template": hometmpl,
                "render_args": {},
            },
            "search.html": {
                "template": searchtmpl,
                "render_args": {},
            },
        }

        for data, part in itertools.product(firstleveldata.keys(), ("", lang)):
            output = outputdir / part
            output.mkdir(parents=True, exist_ok=True)
            output = output / data
            log.debug("Trying to write to %s", str(output))
            template = firstleveldata[data]["template"]
            render_args = firstleveldata[data]["render_args"]
            with open(output, "w") as fh:
                content = template.render(
                    data=homepagecontext,
                    translations=transdata,
                    lang=lang,
                    **render_args
                )
                fh.write(content)
                log.debug("Wrote %s", output)

    output = outputdir / "404.html"
    with output.open("w") as fh:
        content = error404tmp.render(lang="en-us")
        fh.write(content)
        log.debug("Wrote %s", output)

    return


async def render_and_write_html(jinja_env, result, job_name, output_dir):
    template = jinja_env.get_template('index.html')
    output_html = template.render(result=result)

    output_path = Path(output_dir) / f"{job_name.strip()}.html"

    async with aiofiles.open(output_path, 'w') as f:
        await f.write(output_html)


def _main(cliargs=None):
    """Main function"""
    try:
        args = parsecli(cliargs)
        with timer() as t:
            log.info("=== Starting ===")
            log.debug("Arguments: %s", args)

            env = init_jinja_template(args.jinjatemplatedir.absolute())
            tree = etree.parse(args.docserv_stitch_file, etree.XMLParser())
            render(args, tree, env)

    except json.JSONDecodeError as err:
        log.error("Error decoding JSON file %s\nAbort.", err)
        return 100

    except FileNotFoundError as err:
        log.error("File not found: %s.\nAbort", err)
        return 50

    except ValueError as e:
        log.error("Error: %s", e)
        return 20

    except KeyboardInterrupt:
        log.error("Interrupted by user")
        return 10

    finally:
        log.info("Elapsed time: %0.3f seconds", t.elapsed_time)
        log.info("=== Finished ===")
        # log.info("Elapsed time: %0.4f seconds", Timer.tim

    return 0


async def process_doc_unit(doc_unit: Dict[str, str]) -> None:
    """
    Process a single doc unit asynchronously.
    """
    # product, release, language = doc_unit["product"], doc_unit["release"], doc_unit["language"]
    log.info(f"Processing %s", doc_unit)
    await asyncio.sleep(1)  # Simulate async work
    log.info(f"Completed %s", doc_unit)


async def update_git_repo(repo: str|Path) -> None:
    """
    Update a Git repository asynchronously.

    :param repo: The repo URL or path.
    """
    log.info(f"Updating {repo}")
    command = f"git -C {str(repo)} -c core.progress=1 pull -vr"
    result = await run_git(command)
    if result:
        raise RuntimeError(f"Error updating {repo}")


async def clone_git_repo(repo: str|Path,
                         repopath: str|Path,
                         branch:str|None=None) -> None:
    """
    Clone a Git repository asynchronously.

    :param repo: The repo URL or path.
    :param repopath: where to store the cloned repository.
    :param branch: The branch to clone
    """
    log.info(f"Cloning {repo} to {repopath}")
    if branch:
        command = (
            f"git -c core.progress=1 clone --branch {branch} "
            f"{str(repo)} {str(repopath)}"
        )
    else:
        command = f"git -c core.progress=1 clone {str(repo)} {str(repopath)}"

    # result = await run_command(command)
    result = await run_git(command)
    if result:
        raise RuntimeError(f"Error cloning {repo} to {repopath}")


async def worker(args: argparse.Namespace, queue: asyncio.Queue) -> None:
    """
    Async worker that processes doc units from the queue.
    """
    while not queue.empty():
        # Get a doc unit from the queue
        doc_unit = await queue.get()
        repo, productid, docset = doc_unit
        docsetid = docset.attrib.get("setid")

        log.info(f"Processing {productid}/{docsetid}...")
        try:
            path = repo.translate(
                str.maketrans({":": "_", "/": "_", "-": "_", ".": "_"})
            )
            repopath = Path(args.docserv_repo_base_dir).joinpath(
                "permanent-full", path
            )
            if not repopath.exists():
                await clone_git_repo(repo, repopath)
            else:
                # update the repo
                await update_git_repo(repopath)

            # Get the branch
            # TODO: Check if this is correct?
            branch = docset.find("builddocs/language/branch")
            if branch is None:
                log.error("No branch found for %s/%s", productid, )
                # Remove the job from the queue
                queue.task_done()
                continue

            tmpbasedir = Path(args.docserv_repo_base_dir).joinpath(
                "temporary-branches",
            )
            tmpbasedir.mkdir(parents=True, exist_ok=True)
            tmpdir = tempfile.mkdtemp(dir=tmpbasedir,
                                      prefix=f"{productid}-{docsetid}_")
            await clone_git_repo(repopath, tmpdir, branch.text.strip())

            await process_doc_unit(doc_unit)

            # Remove the temporary directory
            # shutil.rmtree(tmpdir)
        finally:
            queue.task_done()  # Notify queue that task is complete


async def main(cliargs=None):
    """
    Main function
    """
    try:
        num_workers = 4
        args = parsecli(cliargs)
        # allow the logger to start
        await asyncio.sleep(0)
        log.info("=== Starting ===")
        que = asyncio.Queue()
        args.config = read_ini_file(args.docserv_ini_config)

        with timer() as t:
            log.debug("Arguments: %s", args)

            tree = etree.parse(args.docserv_stitch_file, etree.XMLParser())
            for docset in list_all_products(tree,
                                            args.lifecycle,
                                            args.include_product_docset):
                product = docset.getparent().attrib.get("productid")
                docsetid = docset.attrib.get("setid")
                git = docset.find("builddocs/git")
                if git is None:
                    log.warning("No Git information found for %s/%s", product, docsetid)
                    continue

                log.info("Adding %s/%s to the queue", product, docsetid)
                await que.put((git.attrib.get("remote"), product, docset) )

            # Create worker tasks
            tasks = [asyncio.create_task(worker(args, que))
                     for _ in range(num_workers)]

            # Wait until all items in the queue are processed:
            await que.join()

            #render(args, tree, env)

        log.info("Elapsed time: %0.3f seconds", t.elapsed_time)

    except RuntimeError as e:
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

    except (KeyboardInterrupt, asyncio.CancelledError):
        log.error("Interrupted by user")
        return 10

    finally:
        # Cancel all workers
        for task in tasks:
            task.cancel()
        # Wait for workers to complete their shutdown
        await asyncio.gather(*tasks, return_exceptions=True)
        # log.info("Elapsed time: %0.3f seconds", t.elapsed_time)
        log.info("=== Finished ===")

    return 0


if __name__ == "__main__":
    # sys.exit(main())
    sys.exit(asyncio.run(main()))