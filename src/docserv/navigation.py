import itertools
import json
import logging
from pathlib import Path
import os.path
from typing import Any

from lxml import etree
from jinja2 import Environment, FileSystemLoader, DebugUndefined
from jinja2.exceptions import TemplateError, UndefinedError

from .common import BIN_DIR, CACHE_DIR, CONF_DIR, SHARE_DIR


logger = logging.getLogger(__name__)


def init_jinja_template(path: str) -> Environment:
    """Initialize the Jinja templates"""
    logger.debug("Initializing Jinja2 environment with %r", path)
    env = Environment(loader=FileSystemLoader(path),
                      trim_blocks=True,
                      lstrip_blocks=True,
                      undefined=DebugUndefined,
                      extensions=['jinja2.ext.debug']
                      )
    env.filters['file_exists'] = os.path.exists
    return env


def create_cache(cache_path: str, stitched_cache: str) -> None:
    """Combine all cached XML files into one

    :param cache_path: the path to the cache directory
    :param stitched_cache: the combined content of all
        cached XML files stored (usually "cache.xml")
    """
    outroot = etree.Element("docservcache")
    for f in Path(cache_path).glob("**/*.xml"):
        root = etree.parse(f)
        outroot.append(root.getroot())

    with open(stitched_cache, "w") as fh:
        fh.write(etree.tostring(outroot, encoding='unicode', pretty_print=True))


def build_json_home(tree: etree._Element|etree._ElementTree,
                    bih) -> tuple[str, str]:
    """Create a build navigation JSON
    """
    target = bih.build_instruction['target']
    # product = bih.product
    # docset = bih.docset
    # lang = bih.lang
    server_name = bih.config['server']['name']
    target = bih.build_instruction['target']
    homepage_json = os.path.join(SHARE_DIR, "homepage/homepage.xsl")
    output = os.path.join(CACHE_DIR, server_name, target, "homepage.json")

    logger.debug("Transforming stitch XML with (%r)...",
                 homepage_json,
                 )
    transform = etree.XSLT(etree.parse(homepage_json,
                                       parser=etree.XMLParser())
    )
    result = transform(tree)
    # Save result to file
    with open(output, "w") as fh:
        fh.write(str(result))
    logger.debug("Wrote JSON to %r", output)
    return output, result


def list_all_products_with_docsets(tree: etree._Element|etree._ElementTree):
    """List all products and their docsets

    :param tree: the XML tree from the stitched Docserv config
    :yield: a string in the format "product/docset", for example
      "sles-sap/trento"
    """
    # Replaces list-all-products.xsl
    for dc in tree.iter("docset"):
        yield (f"{dc.xpath('ancestor::product/@productid')[0]}"
               "/"
               f"{dc.attrib.get('setid', '')}"
               )


def relatedproducts(tree: etree._Element|etree._ElementTree,
                    product: str,
                    docset: str,
                    ) -> list[str]:
    """Returns the dependencies of a specific product/docset
    """
    # Replaces list-related-products.xsl
    # $xsltproc \
    # --stringparam product "$relevant_product" \
    # --stringparam docset "$relevant_docset" \
    # --stringparam internal-mode "$internal_mode" \
    # "$related_stylesheet" "$stitched_config" | \
    # sort -u
    related_stylesheet = f"{SHARE_DIR}/build-navigation/list-related-products.xsl"
    # xml = etree.parse(stitched_config)
    # transform = etree.XSLT(related_stylesheet)
    # params = {
    #     "product": product,
    #     "docset": docset,
    #     "internal-mode": 'false',
    # }
    # result = transform(xml, **params)
    # sort -u ?

    #
    result = []
    foundproduct = tree.findall(f"product[@productid={product!r}]", namespaces=None)
    if not foundproduct:
        logger.fatal("Product ID from %s does not exist", product)
        return result
    if len(foundproduct) > 1:
        logger.fatal("Docserv config contains non-unique product/docset")
        return result
    founddocset = foundproduct[0].findall(f"docset[@setid={docset!r}]")
    if not founddocset:
        logger.fatal("Docset ID from %s does not exist within product=%s",
                     docset, product)
        return result

    # Find all references that matches a ref with the same product/docset
    for ref in tree.iterfind(f"//docset/internal/ref"
                             f"[@product='{product}']"
                             f"[@docset='{docset}']",
                             namespaces=None,
    ):
        result.append("{}/{}".format(
            ref.xpath("ancestor::product/@productid")[0],
            ref.xpath("ancestor::docset/@setid")[0]
            )
        )

    return result


def docserv2json(tree: etree._Element|etree._ElementTree,
                 product: str,
                 docset: str) -> dict:
    """
    Convert the stitched Docserv XML to JSON

    :param tree: the XML tree of the stitched Docserv config
    :return: a dictionary with the JSON content
    """
    # etree.XSLT.strparam
    stylesheet = os.path.join(SHARE_DIR, "docserv-config/docservconfig2json.xsl")
    xslt_tree = etree.parse(stylesheet, parser=etree.XMLParser())
    transform = etree.XSLT(xslt_tree)
    params = {"infile": "false()",
              "product": etree.XSLT.strparam(product),
              "docset": etree.XSLT.strparam(docset),
              }
    result = transform(tree, **params)
    # Check if we have any errors other than XSLT
    for entry in transform.error_log:
        if entry.domain != etree.ErrorDomains.XSLT:
            logger.error("Error from XSLT transformation: %s", entry.message)

    return json.loads(str(result))


def get_translations(tree: etree._Element|etree._ElementTree,
                     product: str,
                     docset: str) -> list[str]:
    """
    Get all translations for a specific product/docset

    :param tree: the XML tree of the stitched Docserv config
    :param product: the product ID
    :param docset: the docset ID
    :return: a list of all translations
    """
    return tree.xpath(
        f"/*/product[@productid={product!r}]/"
        f"docset[@setid={docset!r}]/"
        f"builddocs/language/@lang"
    )


def get_all_dcfiles(tree: etree._Element|etree._ElementTree,
                    product: str,
                    docset: str,
                    lang: str = "en-us") -> list[str]:
    """
    Get all English DC files by default (without subdeliverables)

    :param tree: the XML tree of the stitched Docserv config
    :return: a list of all English DC files
    """
    return tree.xpath(
        f"/*/product[@productid={product!r}]/"
        f"docset[@setid={docset!r}]/"
        f"builddocs/language[@lang={lang!r}]/"
        f"deliverable[not(subdeliverable)]/dc/text()"
    )


def render_and_save(env, outputdir: str, bih, stitched_config: str) -> None:
    # Replaces/extends docserv-build-navigation script
    """Render a Jinja template and save the output to a file

    :param env: the Jinja environment
    :param outputdir: the output directory where to store the rendered HTML files
    :param bih: the instance of the BuildInstructionHandler
    :param stitched_config: the stitched Docserv config
    """
    # Create shortcuts:
    servername = bih.config['server']['name']
    target = bih.build_instruction['target']
    product = bih.product
    docset = bih.docset
    requested_lang = bih.lang
    targetconfig = bih.config['targets'][target]
    json_dir = targetconfig['json_dir']
    json_i18n_dir = targetconfig['json_i18n_dir']
    json_langs = targetconfig['json_langs']
    basecachedir = os.path.join(CACHE_DIR, servername, target)

    # Parse the stitched Docserv config
    tree = etree.parse(stitched_config, parser=etree.XMLParser())

    available_trans = get_translations(tree, product, docset)

    backup_path = targetconfig['backup_path']
    # Templates, could raise TemplateNotFound
    # logger.debug("Target config: %s", targetconfig)
    logger.debug("Jinja_template_index=%s",
                 targetconfig['jinja_template_index']
    )
    indextmpl = env.get_template(targetconfig['jinja_template_index'])
    hometmpl = env.get_template(targetconfig['jinja_template_home'])

    # jsondata = targetconfig['jinjacontext_home']
    # site_sections = targetconfig['site_sections'].split()
    # default_site_section = targetconfig['default_site_section']
    # If valid_languages contains more than one spaces, this doesn't hurt
    all_langs = bih.config['server']['valid_languages']
    lifecycles = ["supported", "unsuppoted"]
    logger.debug("""Useful variables:
    docserv config/target: %s/%s
    product/docset: %s/%s
    requested lang: %r
    json_dir: %r
    outputdir: %r
    translations: %s
    """,
    servername, target, product, docset, requested_lang, json_dir, outputdir,
    available_trans,
    # jsondata,
    # default_site_section,
    )

    # Create directories for all products
    data_path = "docserv/data"
    for p in list_all_products_with_docsets(tree):
        fulldir = os.path.join(backup_path, data_path, p, requested_lang, p)
        if not os.path.exists(fulldir):
            logger.debug("Creating directory %s", fulldir)
            os.makedirs(fulldir, exist_ok=True)

    # TODO: should that be retrieved from Docserv config?
    workdata: dict[str, dict[str, Any]] = {
        "": {
            # targetconfig['jinjacontext_home'],
            "meta": "homepage.json",
            "template": hometmpl,
            "render_args": {},
        },

        # Our products sorted alphabetically
        "appliance": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "compliance": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "container": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "hpe-helion": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "liberty": {
             "render_args": {"isProduct": True},
             "template": indextmpl,
        },
        "neufector": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "opensuse": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "rancher": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "sbp": {
            # "meta": "sbp_metadata.json",
            "template": indextmpl,
            "render_args": dict(isSBP=True,),
        },
        "ses": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "sled": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "sle-ha": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "sle-hpc": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "sle-micro": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "sle-pos": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "sle-public-cloud": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "sle-rt": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "sles": {
             "render_args": {"isProduct": True},
             "template": indextmpl,
        },
        "sles-sap": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "sle-vmdp": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "smart": {
            "render_args": {"isSmartDocs": True},
            "template": indextmpl,
        },
        "smt": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "soc": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "style": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "subscription": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "suma": {
             "render_args": {"isProduct": True},
             "template": indextmpl,
        },
        "suma-retail": {
             "render_args": {"isProduct": True},
             "template": indextmpl,
        },
        "suse-ai": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "suse-caasp": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "suse-cap": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "suse-distribution-migration-system": {
            "render_args": {"isProduct": True},
            "template": indextmpl,
        },
        "suse-edge": {
             "render_args": {"isProduct": True},
             "template": indextmpl,
        },
        # "sle16": {
        #     "render_args": {"isProduct": True},
        #     "template": indextmpl,
        # },
        "trd": {
            "meta": "trd_metadata.json",
            "template": indextmpl,
            "render_args": {"isTRD": True,},
        },
    }

    # logger.debug("workdata dict %s", workdata)

    def process(path:str, meta:str, template, args:dict, output:str):
        """Process the Jinja rendering process
        """
        if not os.path.exists(meta):
            raise FileNotFoundError(
                f"Expected JSON file {meta}, but I couldn't find it."
            )
        os.makedirs(path, exist_ok=True)
        # Read JSON metadata
        with open(meta, "r") as fh:
            context = json.load(fh)

        logger.debug("JSON context successfully loaded (%r)", meta)
        transfile = os.path.join(json_i18n_dir, f"{requested_lang.replace('-', '_')}.json")
        if not os.path.exists(transfile):
            logger.error("Translation file %r does not exist", transfile)
            logger.warning("Using default translation file en_us.json")
            transfile = os.path.join(json_i18n_dir,"en_us.json")

        try:
            with open(transfile, "r") as fh:
                transdata = json.load(fh)
        except FileNotFoundError as err:
            logger.error("Translation file %r does not exist", transfile)
            transdata = {}
        except json.JSONDecodeError as err:
            logger.error("Error decoding JSON file %r", transfile)
            transdata = {}

        # Render and save rendered HTML
        logger.debug("Writing output %s with template %s and args=%s",
                     output, template, args)
        output = os.path.join(path, output)
        try:
            with open(output, "w") as fh:
                content = template.render(data=context,
                                          # debug=True,
                                          translations=transdata,
                                          lang=lang.replace("_", "-"),
                                          **args)
                fh.write(content)
            logger.debug("Wrote %s with args=%s", output, args)

        except UndefinedError as err:
            logger.exception("Jinja undefined error", err)
            raise
        except TemplateError as err:
            logger.exception("Jinja error", err)
            raise

    # Iterate over all translations
    # Overwrites lang variable
    for lang in [requested_lang]:  # available_trans:
        logger.debug("Going to render index page for %s/%s/%s", lang, product, docset)
        jsonfile = os.path.join(json_dir, product, f"{docset}.json")

        if not os.path.exists(jsonfile):
            logger.error("JSON metadata file %r does not exist", jsonfile)
            logger.error("Cannot render index page for %s/%s", product, docset)
            # return

        path = os.path.join(outputdir, lang, product, docset)
        template = workdata[product]["template"]
        args = workdata[product]["render_args"]

        try:
            process(path, jsonfile, template, args, "index.html")
        except FileNotFoundError as err:
            logger.warning("%s", err)

    # TODO: create a cache.xml?
    # homepagejson, result = build_json_home(bih, stitched_config)

    homepagejsonfile = os.path.join(json_dir, "homepage.json")
    if not os.path.exists(homepagejsonfile):
        logger.error("Homepage JSON metadata file %r does not exist", homepagejsonfile)
        return

    path = os.path.join(outputdir)
    process(path,
            homepagejsonfile,
            workdata[""]["template"],
            workdata[""]["render_args"],
            "index.html")
    logger.debug("Wrote root homepage index.html")

    path = os.path.join(outputdir, lang)
    process(path,
            homepagejsonfile,
            workdata[""]["template"],
            workdata[""]["render_args"],
            "index.html")
    logger.debug("Wrote homepage index.html for %s", lang)

    # Search
    #process(outputdir, meta, env.get_template("search.html.jinja"), {}, "search.html")
    #process(os.path.join(outputdir, lang),
    #        meta, env.get_template("search.html.jinja"), {}, "search.html")

    logger.debug("Done with index page for %s/%s/%s", lang, product, docset)