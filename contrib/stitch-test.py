#!/usr/bin/env python3
# This is a replacement of the docserv-stitch command and their check
# shell scripts.
#
#

import argparse
import aiofiles
import asyncio
from functools import wraps
import hashlib
from itertools import groupby
from pathlib import Path
import shlex
import sys
import time

from lxml import etree

## Variables
JOBS=25
DATE=""  # $(date +"%Y-%m-%d")
TMPOUTFILE="docserv-stitch-${DATE}.xml"
# xmllint='xmllint'
# jing='jing'
# starlet='xmlstarlet'
# stacksize=${stacksize:-"-Xss4096K"}

SCHEMA_FILE="validate-product-config/product-config-schema.rnc"
CHECKS_DIR="validate-product-config/checks"
REFERENCES_STYLESHEET="validate-product-config/global-check-ref-list.xsl"
SIMPLIFY_STYLESHEET="simplify-product-config/simplify.xsl"

VALID_LANGUAGES = frozenset([
        'ar-ar', 'cs-cz', 'de-de', 'en-us', 'es-es', 'fr-fr',
        'hu-hu', 'it-it', 'ja-jp', 'ko-kr', 'nl-nl', 'pl-pl',
        'pt-br', 'ru-ru', 'sv-se', 'zh-cn', 'zh-tw'
    ])


# Exception classes used by this module.
class SubprocessError(Exception): pass


# Stolen from subprocess
class CalledProcessError(SubprocessError):
    """Raised when run() is called with check=True and the process
    returns a non-zero exit status.

    Attributes:
      cmd, returncode, stdout, stderr, output
    """
    def __init__(self, returncode: int|None, cmd, output=None, stderr=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
        self.stderr = stderr

    def __str__(self) -> str:
        return f"Command {self.cmd} -> {self.returncode}: {self.stderr}"
        # if self.returncode and self.returncode < 0:
        #     return f"Command {self.cmd} died"
        #     # try:
        #     #     return "Command '%s' died with %r." % (
        #     #             self.cmd, signal.Signals(-self.returncode))
        #     # except ValueError:
        #     #     return "Command '%s' died with unknown signal %d." % (
        #     #             self.cmd, -self.returncode)
        # else:
        #     return "Command '%s' returned non-zero exit status %d." % (
        #             self.cmd, self.returncode)

    @property
    def stdout(self):
        """Alias for output attribute, to match stderr"""
        return self.output

    @stdout.setter
    def stdout(self, value):
        # There's no obvious reason to set this, but allow it anyway so
        # .stdout is a transparent alias for .output
        self.output = value


# class NotUniqueError(ValueError):
#     """If something is not unique, but it should
#     """
#     def __init__(self, *args, check=None, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.check = check


class GatheringTaskGroup(asyncio.TaskGroup):
    def __init__(self):
        super().__init__()
        self.__tasks = []

    def create_task(self, coro, *, name=None, context=None):
        task = super().create_task(coro, name=name, context=context)
        self.__tasks.append(task)
        return task

    def results(self):
        return {task.get_name(): task.result() for task in self.__tasks}


def printfunc(func):

    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        # Print the function name and arguments
        name = func.__name__
        print(f"  Using check {name!r}...")
        return await func(name, *args, **kwargs)

    # Return the appropriate wrapper based on whether the function is a coroutine
    return async_wrapper


# -------------------------
def dupes(alist: list) -> list:
    """Returns a list of duplicate entries from the given list.
    """
    return [x for x, y in groupby(sorted(alist)) if len(list(y)) > 1]


@printfunc
async def check_dc_in_language(funcname, tree: etree._ElementTree):
    """Make sure each dc appears only once within a language

     :param filename: the XML filename to check
     :return: True if all is okay, False if there are duplicates
    """
    languages = tree.xpath("//language")
    for lang in languages:
        langcode = lang.attrib.get("lang")
        setid = lang.xpath("ancestor::docset/@setid")
        if not setid:
            # We can't find a docset for category/language, so continue
            continue
        dcs = [dc.text for dc in lang.iterdescendants("dc")]

        if len(dcs) != len(set(dcs)):
            raise ValueError(
                (f"[{funcname}] Some dc elements within a language have non-unique values. "
                 "Check for occurrences of the following duplicated "
                 f"dc elements in docset={setid}/language={langcode}: "
                 f"{dupes(dcs)}"
                )
            )


@printfunc
async def check_duplicate_categoryid(funcname, tree: etree._ElementTree):
    """
    we want to allow IDs that start with a digit, hence we can't use
    RelaxNG's xsd:ID data type, but we can use xmlstarlet to check
    """
    categoryids = tree.xpath("//@categoryid")
    if len(categoryids) != len(set(categoryids)):
        raise ValueError(
            (f"[{funcname}] Some categoryid values are not unique. "
             "Check for occurrences of the following duplicated categoryid(s): "
             f"{dupes(categoryids)}"
             )
        )


@printfunc
async def check_duplicated_format_in_extralinks(funcname, tree: etree._ElementTree):
    """
    make sure each document format appears only once within a
    given link's language element
    """

    links = tree.xpath("//language[parent::link/parent::external]")
    for link in links:
        current_id = link.xpath("url[1]/@href")
        formats = link.xpath("url/@format")

        if len(formats) != len(set(formats)):
            raise ValueError(
                (f"[{funcname}] For the link with the URL {current_id}, some of the "
                "values of format attributes in <url> elements are duplicated. "
                "Check for occurrences of the following duplicated format "
                "attribute(s) in the link {current_id}: "
                f"{dupes(formats)}"
                )
            )


@printfunc
async def check_duplicated_linkid(funcname, tree: etree._ElementTree):
    """Check for duplicate linkends

     we want to allow IDs that start with a digit, hence we can't use
     RelaxNG's xsd:ID data type, but we can use xmlstarlet to check
     @linkids only need to be locally unique (i.e. within one <internal/> element).

     :param filename: the XML filename to check
     :return: True if all is okay, False if there are duplicates
    """
    for external in tree.xpath("//external"):
        linkids =  external.xpath("link/@linkid")

        if len(linkids) != len(set(linkids)):
            curdocset = external.xpath("ancestor::docset/@setid")[0]
            raise ValueError(
                (
                f"[{funcname}] Some linkid values are not unique."
                "Check for occurrences of the following duplicated linkid(s) "
                f"within the docset {curdocset!r}: {dupes(linkids)}"
                )
            )


@printfunc
async def check_duplicate_setid(funcname, tree: etree._ElementTree):
    """Checks all @setid attributes if they are unique

    we want to allow IDs that start with a digit, hence we can't use RelaxNG's
    xsd:ID data type, but we can use xmlstarlet to check

    """
    setids = tree.xpath("//@setid")
    if len(setids) != len(set(setids)):
        # dupes = [x for x, y in groupby(sorted(setids)) if len(list(y)) > 1]
        raise ValueError(
            (f"[{funcname}] Some setid values are not unique. "
             "Check for occurrences of the following duplicated setid(s): "
             f"{dupes(setids)}"
             )
        )


@printfunc
async def check_duplicated_url_in_extralinks(funcname, tree: etree._ElementTree):
    """Make sure each URL appears only once within a given external links section
    """
    externals = tree.xpath("//external")
    for external in externals:
        current_id = external.xpath("ancestor::docset/@setid")
        urls = external.xpath("descendant::url/@href")
        if len(urls) != len(set(urls)):
            raise ValueError(
                (f"[{funcname}] Within the external links section of docset {current_id},"
                  "some URLs are duplicated. "
                  "Check for occurrences of the following duplicated URL(s) "
                  f"within the external links of docset {current_id}: "
                  f"{dupes(urls)}")
            )


@printfunc
async def check_enabled_format(funcname, tree: etree._ElementTree):
    """All format tags need at least one format attribute set to "1" or "true"
    """
    format_issues = tree.xpath("//format[not(@*='true') and not(@*='1')]")
    if format_issues:
        raise ValueError(
            (f"[{funcname}] There is/are {len(format_issues)} format element(s) where "
             "no attribute is set to 'true' or '1'."
             )
        )


@printfunc
async def check_format_subdeliverable(funcname, tree: etree._ElementTree):
    """Make sure that deliverables that contain subdeliverables only
    enable html or single-html as format
    """
    deliverables = tree.xpath("//deliverable[subdeliverable]")

    for deli in deliverables:
        # hasbadformat=$($starlet sel -t -v "(//deliverable[subdeliverable])
        hasbadformat = deli.xpath("format/@*[local-name(.) = 'epub' or local-name(.) = 'pdf'][. = 'true' or . = '1']")
        if hasbadformat:
            setid = deli.xpath("ancestor::docset/@setid")
            language = deli.xpath("ancestor::language/@lang")
            dc = list(deli.iterchildren("dc"))
            raise ValueError(
                (f"[{funcname}] A deliverable that has subdeliverables has "
                 " PDF or EPUB enabled as a format: "
                 f"docset={setid}/language={language}/deliverable={dc}. "
                 "Subdeliverables are only supported for the formats HTML and Single-HTML.")
            )


@printfunc
async def check_lang_code_in_category(funcname, tree: etree._ElementTree):
    """Make sure each language code appears only once within a
    given product's category names
    """
    categories = tree.xpath("//category")
    for category in categories:
        langcodes = category.xpath("language/@lang")
        if len(langcodes) != len(set(langcodes)):
            current_id = category.attrib.get("categoryid")
            raise ValueError(
                (f"[{funcname}] Some of the name translations of category {current_id} "
                 "have non-unique lang attributes. "
                 "Check for occurrences of the following duplicated lang "
                  "attribute(s) in the language elements of "
                  f"category {current_id}"
                  f"{dupes(langcodes)}"
                  )
            )


@printfunc
async def check_lang_code_in_desc(funcname, tree: etree._ElementTree):
    """Make sure each language code appears only once within a
    given product's description texts (desc)
    """
    langcodes = tree.xpath("//product/desc/@lang")
    if len(langcodes) != len(set(langcodes)):
        raise ValueError(
            (f"[{funcname}] Some desc elements have non-unique lang attributes. "
             "Check for occurrences of the following duplicated "
             "lang attribute(s) in desc elements: "
             f"{dupes(langcodes)}"
             )
        )


@printfunc
async def check_lang_code_in_docset(funcname, tree: etree._ElementTree):
    """Make sure each language code appears only once within a given set
    """
    setids = tree.xpath("//@setid")
    for docset in setids:
        langcodes = tree.xpath(f"//docset[@setid='{docset}']/builddocs/language/@lang")
        if len(langcodes) != len(set(langcodes)):
            raise ValueError(
                (f"[{funcname}] Some language elements within a set have non-unique "
                "lang attributes. "
                "Check for occurrences of the following duplicated "
                f"lang attribute(s) in docset {docset}: "
                f"{dupes(langcodes)}"
                )
            )


@printfunc
async def check_lang_code_in_extralinks(funcname, tree: etree._ElementTree):
    """Make sure each language code appears only once within a
    given link's language elements
    """
    links = tree.xpath("//link[parent::external]")
    for link in links:
        langcodes = link.xpath("language/@lang")
        if len(langcodes) != len(set(langcodes)):
            current_id = link.xpath("language[1]/url[1]/@href")
            current_id = "" if not current_id else current_id[0]
            raise ValueError(
                (f"[{funcname}] Some of the localized versions of {current_id!r} have "
                 "non-unique lang attributes. "
                 "Check for occurrences of the following duplicated "
                 "lang attribute(s) in the language elements "
                 f"of link {current_id!r}: "
                 f"{dupes(langcodes)}"
                 )
            )


@printfunc
async def check_lang_code_in_overridedesc(funcname, tree: etree._ElementTree):
    """Make sure each language code appears only once within a
    given product's description texts (desc)
    """
    overridedescs = tree.xpath("//docset/overridedesc")
    for overridedesc in overridedescs:
        langcodes = overridedesc.xpath("desc/@lang")
        if len(langcodes) != len(set(langcodes)):
            raise ValueError(
                (f"[{funcname}] Some overridedesc elements contain desc elements with "
                 "non-unique lang attributes. "
                 "Check for occurrences of the following duplicated "
                 "lang attribute(s) in <desc> elements: "
                 f"{dupes(langcodes)}")
            )

@printfunc
async def _check_site_sections(funcname, tree: etree._ElementTree):
    """Make sure all site sections from the document are also
    configured in the INI file
    """
    pass


@printfunc
async def check_subdeliverable_in_deliverable(funcname, tree: etree._ElementTree):
    """Make sure each subdeliverable appears only once within a dc
    """
    deliverables = tree.xpath("//deliverable[subdeliverable]")
    for deliverable in deliverables:
        # Create a list and each entry contains tuple(@category, text())
        filtered_subdeli = [
            (item.attrib.get("category"), item.text.strip())
            for item in deliverable.iterchildren("subdeliverable")
        ]
        if len(filtered_subdeli) != len(set(filtered_subdeli)):
            langcode= deliverable.xpath("ancestor::language/@lang")
            setid = deliverable.xpath("ancestor::docset/@setid")
            dc = deliverable.findtext("dc", default="n/a")
            raise ValueError(
                (f"[{funcname}] Some subdeliverable elements within a deliverable have "
                 "non-unique values. "
                 "Check for occurrences of the following duplicated subdeliverable(s) "
                 f"in docset={setid}/language={langcode}/dc={dc}: "
                 f"{dupes(filtered_subdeli)}")
            )


@printfunc
async def check_translation_deliverables(funcname, tree: etree._ElementTree):
    """Make sure that deliverables defined in translations are a
    subset of the deliverables defined in the default language
    """
    deliverables = tree.xpath("//deliverable[ancestor::language[not(@default) or not(@default='true' or @default='1')]]")
    for deliverable in deliverables:
        currentdc = deliverable.findtext("dc")
        if currentdc is None:
            continue

        isdefaultdc = deliverable.xpath(f"parent::language/preceding-sibling::language[@default='1' or @default='true']/descendant::dc[. = '{currentdc}']")
        if not isdefaultdc:
            setid = deliverable.xpath("ancestor::docset/@setid")
            setid = "" if not setid else setid[0]
            language = deliverable.xpath("ancestor::language/@lang")
            language = "" if not language else language[0]
            raise ValueError(
                (f"[{funcname}] The DC file {currentdc} is configured for "
                 f"docset={setid}/language={language} but not for the default "
                 f"language of docset={setid}. "
                 "Documents configured for translation languages must be "
                 "a subset of the documents configured for the default language."
                 )
            )

        # subdeliverables = deliverable.xpath("subdeliverable")
        for subdeliverable in deliverable.iterchildren("subdeliverable"):
            subname = subdeliverable.text
            is_default_subdeliverable=subdeliverable.xpath(
                f"ancestor::language/preceding-sibling::language"
                "[@default='1' or @default='true']/descendant::deliverable"
                f"[dc = '{currentdc}']/subdeliverable[. = '{subname}']"
            )
            if not is_default_subdeliverable:
                setid = deliverable.xpath("ancestor::docset/@setid")[0]
                language = deliverable.xpath("ancestor::language/@lang")[0]
                raise ValueError(
                    (f"[{funcname}] The subdeliverable {subname!r} is configured "
                     f"for docset={setid!r}/language={language!r}/deliverable={currentdc!r} "
                     "but not for the same deliverable of the default language "
                     f"of docset={setid!r}. "
                     "Documents configured for translation languages must be "
                     "a subset of the documents configured for the default language.")
                )


@printfunc
async def check_category_refs(funcname, tree: etree._ElementTree):
    """Make sure that all references to category ids actually
    reference an existing category
    """
    # check-category-refs.xsl
    missing_category_refs = []
    categories = set(tree.xpath("//@category"))
    categoryids = tree.xpath("//@categoryid")
    for cat in categories:
        if cat not in categoryids:
            missing_category_refs.append(cat)

    if missing_category_refs:
        raise ValueError(
            (f"[{funcname}] There are references in this file "
             "that don't exist. Found these unresolved references: "
             f"{missing_category_refs}. "
             "The following categories are valid in this file: "
             f"{categoryids}"
             )
        )


# Collect all functions that start with "check_"
TASKS = [func for name, func in globals().items()
         if callable(func) and name.startswith("check_")
         ]


# ---------------------
async def calculate_md5(path) -> str:
    """Calculate the MD5 hash"""
    md5 = hashlib.md5()
    async with aiofiles.open(path, "rb") as f:
        while True:
            chunk = await f.read(4096)
            if not chunk:
                break
            md5.update(chunk)
    return md5.hexdigest()


def load_xml(path: Path) -> etree._ElementTree:
    """Load an XML file into an ElementTree."""
    # print(f"Checking {path}...")
    return etree.parse(path)



async def process_file(xmlfile: Path) -> tuple[str, str]:
    """Create the tasks for config directory and checks directory"""
    tree = load_xml(xmlfile)

    async with asyncio.TaskGroup() as tg:
        print(f"Checking XML file {xmlfile.name}")
        task = tg.create_task(calculate_md5(xmlfile), name=xmlfile.name)

        for coroutine in TASKS:
            tg.create_task(coroutine(tree))
            # task.add_done_callback(lambda t: results.append(t.result()))

    return xmlfile.name, await task


async def validate_config(xmlfile: Path, schema_file: Path|str):
    """Validate the XML config against a RELAX NG schema"""
    cmd = shlex.split(f"jing -ci {schema_file} {xmlfile}")
    # result = subprocess.run(cmd, capture_output=True)

    print(f"Going to validate {xmlfile.name}...")
    # Create a subprocess to run the command
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    # Decode the output; as Jing doesn't have any output on success,
    # we can skip stdout
    _, stderr = await process.communicate()
    stderr_str = stderr.decode()
    if process.returncode is not None and process.returncode != 0:
        raise CalledProcessError(process.returncode, " ".join(cmd), stderr=stderr_str)


async def combine_config(xmlfile: Path, docservconfig: etree.Element):
    """Add each XML config file into the tree
    """
    tree = etree.parse(xmlfile)
    root = tree.getroot()
    docservconfig.append(root)


async def main(cliargs=None) -> int:
    """
    """
    # Parse CLI args. At the moment, we fake it:
    args = argparse.Namespace(
        configdir="/home/toms/repos/GL/susedoc/docserv-config/config.d",
        sharedir="/home/toms/repos/GL/susedoc/docserv-devel/docserv/share/",
        # ---
        checksdir="{sharedir}/validate-product-config/checks",
        product_config_schema="{sharedir}/validate-product-config/product-config-schema.rnc",
        simplify_xslt="{sharedir}/simplify-product-config/simplify.xsl",
    )

    # Replace placeholders
    for key in args.__dict__:
        value = getattr(args, key)
        setattr(args, key, value.format(sharedir=args.sharedir))

    failed_files = []
    validated_files = {}
    md5sums = {}

    # print("[INFO] The available checks", TASKS)
    docservconfig = etree.ElementTree(etree.Element("docservconfig"))

    start_time = time.time()  # Record the start time
    file_paths = Path(args.configdir).glob("*.xml")
    for idx, path in enumerate(file_paths, 1):
        try:
            # (1) Validate each XML config
            await validate_config(path, args.product_config_schema)

            # (2) Check each XML config against different functions
            results = await process_file(path)
            md5sums.update((results,))

            # (3) Combine every XML config
            await combine_config(path, docservconfig.getroot())

        except* (ValueError,
                 TypeError,
                 etree.XMLSyntaxError,
                 etree.XPathEvalError) as te:
            for error in te.exceptions:
                print(f" => [Error] Processing {path.name}: {error}")
                failed_files.append((path, error))

        except* CalledProcessError as te:
            for error in te.exceptions:
                validated_files[path.name] = error.stderr

    print("\nWriting result docservconfig to /tmp/docservconfig.xml...")
    docservconfig.write("/tmp/docservconfig.xml",
                        encoding="utf-8",
                        pretty_print=True,
                        xml_declaration=True,
    )

    # check for uniqueness of productid values (which we can't do before
    # stitching the file together)
    productids = sorted(docservconfig.xpath("//@productid"))
    if len(productids) != len(set(productids)):
        raise ValueError(
            (
            f"(global check): Some productid values in {args.configdir!r} are not unique. "
            "Check for the following productid values:"
            f"{dupes(productids)}"
            )
        )
    end_time = time.time()  # Record the end time
    elapsed_time = end_time - start_time  # Calculate the elapsed time

    print("\n=== SUMMARY ===")
    if failed_files:
        print(f"  => Found {len(failed_files)} failed XML files ===")
        for idx, (path, error) in enumerate(failed_files, 1):
            print(f"{idx}: File {path.name!r}: {error}")
        returncode = 1

    if validated_files:
        print(f"  => Found {len(validated_files)} invalid XML files ===")
        for idx, (path, error) in enumerate(validated_files, 1):
            print(f"{idx}: File {path.name!r}: {error}")

    if not(failed_files) and not(validated_files):
        print(f"  => OK! All fine!")
        returncode = 0

    print("MD5sum", md5sums)

    print(f"""
  Checked {idx} XML files using {len(TASKS)} checks each resulting in {idx*len(TASKS)} tasks
  Processing completed in {elapsed_time:.3f} seconds""")
    return returncode


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))