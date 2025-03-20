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

import json
import itertools
import logging
from logging.config import dictConfig
from pathlib import Path
import os.path
from typing import Any
import re
import sys

from lxml import etree
from jinja2 import Environment, FileSystemLoader, DebugUndefined
from jinja2.exceptions import TemplateNotFound


__version__ = "0.3.0"
__author__ = "Tom Schraitle"


# --- Variables
PYTHON_VERSION: str = f"{sys.version_info.major}.{sys.version_info.minor}"

#: Separator for multiple values
SEPARATOR = re.compile(r"[,; ]")

LOGGERNAME = "indexpages"
JINJALOGGERNAME = f"{LOGGERNAME}.jinja"
XPATHLOGGERNAME = f"{LOGGERNAME}.xpath"
#: The log file to use
LOGFILE = "/tmp/indexpages.log"
#: Map verbosity level (int) to log level
LOGLEVELS = {
    None: logging.WARNING,  # fallback
    0: logging.ERROR,
    1: logging.WARNING,
    2: logging.INFO,
    3: logging.DEBUG,
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

#: All languages supported by the documentation portal
ALL_LANGUAGES = frozenset(
    "de-de en-us es-es fr-fr ja-jp ko-kr pt-br zh-cn".split(" ")
)

# in order for all messages to be delegated.
logging.getLogger().setLevel(logging.NOTSET)

log = logging.getLogger(LOGGERNAME)
jinjalog = logging.getLogger(JINJALOGGERNAME)
xpathlog = logging.getLogger(XPATHLOGGERNAME)


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


class LangsAction(argparse.Action):
    LANG_PATTERN = re.compile(r"[a-z]{2}-[a-z]{2}")
    LANG_REGEX = re.compile(
        rf'^({LANG_PATTERN.pattern}{SEPARATOR.pattern})*'
        rf'{LANG_PATTERN.pattern}'
        rf'$'
    )

    def __call__(self, parser, namespace, values, option_string=None):
        cls = type(self)
        if values.lower() == "all":
            languages = ALL_LANGUAGES
        elif values.lower() == "all-en":
            languages = tuple(ALL_LANGUAGES - set(["en-us"]))
        elif cls.LANG_REGEX.match(values):
            languages = SEPARATOR.split(values)
        else:
            parser.error(
                "Wrong syntax in --langs. "
                "Each languages must to be in the format '[a-z]{2}-[a-z]{2}'. "
                "More than one language need to be separated by commas."
            )
        print(">>> languages:", languages)
        invalid_langs = set(languages) - set(ALL_LANGUAGES)
        if invalid_langs:
            parser.error(
                f"Invalid language(s): {', '.join(invalid_langs)!r} "
                f"(choose from {', '.join(sorted(ALL_LANGUAGES))})"
            )

        setattr(namespace, self.dest, languages)
        return


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
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase verbosity level",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=(
            f"{__file__}\n"
            f"version {__version__} written by {__author__} "
            f"Using Python {PYTHON_VERSION}"
        ),
        help="shows the version of the script",
    )
    parser.add_argument("-J", "--json-dir",
                        help="Directory with JSON files"
    )
    parser.add_argument("-S", "--stitch-file",
                        required=True,
                        help="XML stitch file to use"
    )
    parser.add_argument("-D", "--docserv-config-dir",
                        required=True,
                        help="Docserv configuration file to use"
    )

    #parser.add_argument("-t", "--targets",
    #                  help="Target server names")
    parser.add_argument("-p", "--products",
                        #required=True,
                        help="Products to process. Use comma, space, or semicolon for multiple products.")
    parser.add_argument("-d", "--docsets",
                        #required=True,
                        help="Docsets to process. Use comma, space, or semicolon for multiple docsets.")
    parser.add_argument("-l", "--langs",
                       default=["en-us"],
                       action=LangsAction,
                       help=("Languages to process (defaults to %(default)r). "
                             "Use comma or semicolon-separated list for multiple languages.\n"
                             f"Use 'all' to process all languages ({', '.join(sorted(ALL_LANGUAGES))}). "
                             f"Use 'all-en' to process all languages except 'en-us'."
                             )
                        )
    parser.add_argument("-c", "--lifecycle",
                        default=["supported"],
                        action=LifecycleAction,
                        help=("Lifecycle to process (defaults to %(default)r)")
                        )
    # Positional arguments
    parser.add_argument("-o", "--output-dir",
                        metavar="OUTPUT-DIR",
                        help="Output directory for the index pages"
    )
    args = parser.parse_args(args=cliargs)
    args.parser = parser

    # Setup main logging and the log level according to the "-v" option
    loglevel = LOGLEVELS.get(args.verbose, logging.DEBUG)
    DEFAULT_LOGGING_DICT["handlers"]["console"]["level"] = loglevel
    DEFAULT_LOGGING_DICT["loggers"][LOGGERNAME]["level"] = loglevel

    # Setup sub loggers
    if args.verbose > len(LOGLEVELS):
         DEFAULT_LOGGING_DICT["loggers"][JINJALOGGERNAME]["level"] = logging.DEBUG
    if args.verbose +1 > len(LOGLEVELS):
        DEFAULT_LOGGING_DICT["loggers"][XPATHLOGGERNAME]["level"] = logging.DEBUG

    dictConfig(DEFAULT_LOGGING_DICT)

    if args.lifecycle == ["all"]:
        args.lifecycle = []

    if args.products is None and args.docsets is not None:
        parser.error("If you specify a docset, you must also specify a product")

    # args.targets = [] if args.targets is None else SEPARATOR.split(args.targets)
    if args.products is not None:
        args.products = [] if args.products is None else SEPARATOR.split(args.products)
    if args.docsets is not None:
        args.docsets = [] if args.docsets is None else SEPARATOR.split(args.docsets)
    #if args.langs is not None:
    #    args.langs = [] if args.langs is None else SEPARATOR.split(args.langs)

    args.stitch_file = Path(args.stitch_file)
    if not args.stitch_file.exists():
        parser.error(f"XML stitch file {str(args.stitch_file)!r} does not exist")

    docservconfigdir = Path(args.docserv_config_dir).expanduser()
    if docservconfigdir.joinpath("config.d").exists():
        args.configddir = docservconfigdir.joinpath("config.d")
    else:
        parser.error(f"Directory {docservconfigdir} does not exist or is missing 'config.d' subdirectory")

    if docservconfigdir.joinpath("jinja-doc-suse-com").exists():
        args.jinjatemplatedir = docservconfigdir.joinpath("jinja-doc-suse-com")
    else:
        parser.error(f"Directory {docservconfigdir} does not exist or is missing 'jinja-doc-suse-com' subdirectory")

    if docservconfigdir.joinpath("json-portal-dsc").exists():
        args.jsondir = docservconfigdir.joinpath("json-portal-dsc")
    else:
        parser.error(f"Directory {docservconfigdir} does not exist or is missing 'json-portal-dsc' subdirectory")

    if docservconfigdir.joinpath("jinja-doc-suse-com", "i18n").exists():
        args.jinja_i18n_dir = docservconfigdir.joinpath("jinja-doc-suse-com", "i18n")
    else:
        parser.error(f"Directory {docservconfigdir} does not exist or is missing 'json-portal-dsc/i18n' subdirectory")

    if docservconfigdir.joinpath("jinja-doc-suse-com", "suseparts").exists():
        args.susepartsdir = docservconfigdir.joinpath("jinja-doc-suse-com", "suseparts")
    else:
        parser.error(f"Directory {docservconfigdir} does not exist or is missing 'json-portal-dsc/suseparts' subdirectory")

    return args


def jinja_path_exists(env, path: str) -> bool:
    """Check if a path exists"""
    for f in env.loader.searchpath:
        jinjalog.debug("Checking if path %r exists in template dir(%r): %s",
                  path,
                  f,
                  os.path.exists(os.path.join(f, path)))
    return any([ os.path.exists(os.path.join(f, path)) for f in env.loader.searchpath])


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


def list_all_products(tree: etree._Element|etree._ElementTree):
    """List all products

    :param tree: the XML tree from the stitched Docserv config
    :yield: a string with the product ID
    """
    # Replaces list-all-products.xsl
    for product in tree.iter("product"):
        productid = product.attrib.get("productid", None)
        if productid:
            yield productid


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

    log.debug("""Variables used:
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
        output = os.path.join(path, "index.html")

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


def main(cliargs=None):
    """Main function"""
    try:
        args = parsecli(cliargs)
        log.debug("=== Starting ===")
        env = init_jinja_template(args.jinjatemplatedir.absolute())
        log.debug("Arguments: %s", args)
        env = init_jinja_template(args.jinjatemplatedir)
        tree = etree.parse(args.stitch_file, etree.XMLParser())
        render(args, tree, env)
        log.debug("=== Finished ===")

    except json.JSONDecodeError as err:
        log.error("Error decoding JSON file %s\nAbort.", err)
        return 100

    except FileNotFoundError as err:
        log.error("File not found: %s.\nAbort", err)
        return 50

    except ValueError as e:
        log.error("Error: %s", e)
        return 20

    return 0


if __name__ == "__main__":
    sys.exit(main())