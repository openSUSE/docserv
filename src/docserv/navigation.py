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


def init_jinja_template(path) -> Environment:
    """Initialize the Jinja templates"""
    env = Environment(loader=FileSystemLoader(path),
                      trim_blocks=True,
                      lstrip_blocks=True,
                      undefined=DebugUndefined,
                      extensions=['jinja2.ext.debug']
                      )
    return env


def create_cache(cache_path, stitched_cache):
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


def build_site_section(bih, stitched_config):
    """Create a build navigation JSON
    """
    target = bih.build_instruction['target']
    product = bih.product
    docset = bih.docset
    lang = bih.lang
    ui_languages = bih.config['server']['valid_languages']
    site_sections = bih.config['targets'][target]['site_sections']
    default_site_section =bih.config['targets'][target]['default_site_section']
    cache_file = "TBD"
    internal_mode = "false"
    build_navigation_json = "build-navigation/build-navigation-json.xsl"
    output_root = "TBD"

    # xsltproc \
    # --stringparam "output_root" "$output_dir/$data_path/" \
    # --stringparam "cache_file" "$cache_file" \
    # --stringparam "internal_mode" "$internal_mode" \
    # --stringparam "ui_languages" "$ui_languages" \
    # --stringparam "site_sections" "$site_sections_deduped" \
    # --stringparam "default_site_section" "$default_site_section" \
    # --stringparam "product" "$this_product" \
    # --stringparam "docset" "$this_docset" \
    # "$build_navigation_json" \
    # "$stitched_config"

    xml = etree.parse(stitched_config)
    transform = etree.XSLT(build_navigation_json)
    result = transform(xml,
                       output_root=output_root,
                       cache_file=cache_file,
                       internal_mode=internal_mode,
                       ui_languages=ui_languages,
                       site_sections=site_sections,
                       default_site_section=default_site_section,
                       product=product,
                       docset=docset,
                       )
    # Maybe convert from bytes -> unicode?
    return result


def list_all_products(config: str):
    """List all products and docsets

    :param config: the stitched Docserv config
    :yield: a string in the format "product/docset", for example
      "sles-sap/trento"
    """
    # Replaces list-all-products.xsl
    tree = etree.parse(config)
    for dc in tree.iter("docset"):
        yield (f"{dc.xpath('ancestor::product/@productid')[0]}"
               "/"
               f"{dc.attrib.get('setid', '')}"
               )


def relatedproducts(product, docset, stitched_config: str):
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
    xml = etree.parse(stitched_config)
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
    foundproduct = xml.findall(f"product[@productid = '{product}']")
    if not foundproduct:
        logger.fatal("Product ID from %s does not exist", product)
        return result
    if len(foundproduct) > 1:
        logger.fatal("Docserv config contains non-unique product/docset")
        return result
    founddocset = foundproduct[0].findall(f"docset[@setid = '{docset}']")
    if not founddocset:
        logger.fatal("Docset ID from %s does not exist within product=%s",
                     docset, product)
        return result

    # Find all references that matches a ref with the same product/docset
    for ref in xml.iterfind(f"//docset/internal/ref"
                             f"[@product='{product}']"
                             f"[@docset='{docset}']"
    ):
        result.append("{}/{}".format(
            ref.xpath("ancestor::product/@productid")[0],
            ref.xpath("ancestor::docset/@setid")[0]
            )
        )

    return result


def render_and_save(env, outputdir: str, bih) -> None:
    # Replaces/extends docserv-build-navigation script
    """Render a Jinja template and save the output to a file

    :param env: the Jinja environment
    :param outputdir: the output directory where to store the rendered HTML files
    :param bih: the instance of the BuildInstructionHandler
    """
    servername = bih.config['server']['name']
    target = bih.build_instruction['target']
    product = bih.product
    docset = bih.docset
    lang = bih.lang
    # Templates, could raise TemplateNotFound
    indextmpl = env.get_template(bih.config['targets'][target]['jinja_template_index'])
    hometmpl = env.get_template(bih.config['targets'][target]['jinja_template_home'])

    # jsondata = bih.config['targets'][target]['jinjacontext_home']
    # site_sections = bih.config['targets'][target]['site_sections'].split()
    # default_site_section = bih.config['targets'][target]['default_site_section']
    # If valid_languages contains more than one spaces, this doesn't hurt
    all_langs = bih.config['server']['valid_languages'].split()
    lifecycles = ["supported", "unsuppoted"]
    logger.debug("""Useful variables:
    docserv config: %r
    target: %r
    product: %r
    docset: %r
    lang: %r
    outputdir: %r
    """, servername, target, product, docset, lang, outputdir,
    # jsondata,
    # default_site_section,
    )

    # TODO: retrieve them from JSON
    subitems = { # dict[str, list[tuple[str, dict[str, Any]], ...]]

        # str:   list[tuple]
        # only smart/index.html needed
        # "smart": [
        #            ('container', dict(isSmartDocs=True)),
        #            ('deploy-upgrade', dict(dataSmartDocs=True)),
        #            ('micro-clouds', dict(dataSmartDocs=True)),
        #            ('network', dict(dataSmartDocs=True)),
        #            ('rancher', dict(dataSmartDocs=True)),
        #            ('security', dict(dataSmartDocs=True)),
        #            ('systems-management', dict(dataSmartDocs=True)),
        #            ('systemtuning-performance', dict(dataSmartDocs=True)),
        #            ('virtualization-cloud', dict(dataSmartDocs=True)),
        #            ],

        # no sbp/index.html
        "sbp": [
                ('cloud-computing', dict(isSBP=True, category="Cloud")),
                ('container-virtualization', dict(isSBP=True,
                                                  category="Containerization")),
                # ('deprecated', dict(isSBP=True, category="Deprecated")),
                # ('desktop-linux', dict(isSBP=True, category="Desktop and Linux")),
                ('sap-12', dict(isSBP=True,
                                category="SAP applications on SUSE Linux Enterprise 12")),
                ('sap-15', dict(isSBP=True,
                                category="SAP applications on SUSE Linux Enterprise 15")),
                # ('server-linux', dict(isSBP=True, category="Server and Linux")),
                ('storage', dict(isSBP=True, category="Storage")),
                ('systems-management', dict(isSBP=True, category="Systems Management")),
                ('security', dict(isSBP=True, category="Security")),
                ('tuning-performance', dict(isSBP=True, category="Tuning & Performance")),
                ],

        # no trd/index.html
        "trd": [
                ("ampere", dict(isTRD=True, partner="Ampere")), # l
                # ("aws", dict(isTRD=True, partner="AWS")),
                # ("azure", dict(isTRD=True, partner="Azure")),
                ("cisco", dict(isTRD=True, partner="Cisco")), # l
                ("clastix", dict(isTRD=True, partner="Clastix")),
                ("dell-technologies", dict(isTRD=True, partner="Dell Technologies")), # l
                ("fortinet", dict(isTRD=True, partner="Fortinet")), # l
                # ("gcp", dict(isTRD=True, partner="GCP")),
                ("hewlett-packard-enterprise", dict(isTRD=True, partner="Hewlett Packard Enterprise")), #
                ("hp", dict(isTRD=True, partner="HP")), # l
                ("ibm", dict(isTRD=True, partner="IBM")), # l
                ("jupyter", dict(isTRD=True, partner="Jupyter")), # l
                # ("kubecost", dict(isTRD=True, partner="Kubecost")), # l
                ("kubeflow", dict(isTRD=True, partner="Kubeflow")), #
                ("lenovo", dict(isTRD=True, partner="Lenovo")),
                ("managed-service-provider", dict(isTRD=True, partner="Managed Service Provider")),
                ("minio", dict(isTRD=True, partner="MinIO")),
                ("nvidia", dict(isTRD=True, partner="NVIDIA")),
                ("ondat", dict(isTRD=True, partner="Ondat")),
                ("rancher", dict(isTRD=True, partner="Rancher")),
                ("supermicro", dict(isTRD=True, partner="Supermicro")),
                ("suse", dict(isTRD=True, partner="SUSE")),
                ("veeam", dict(isTRD=True, partner="Veeam")),
                ("wordpress", dict(isTRD=True, partner="WordPress")),
                ],

    }

    # TODO: Somehow we need to create this data automatically
    workdata: dict[str, dict[str, Any]] = {
        # This entry will be remove later
        "": {
            # bih.config['targets'][target]['jinjacontext_home'],
            "meta": "homepage_docserv_bigfile.json",
            "template": hometmpl,
            "render_args": dict(),
            "output": "index.html",
        },

        # SBP, top-level page will be removed later
        "sbp": {
            "meta": "sbp_metadata.json",
            "template": indextmpl,
            "render_args": dict(isSBP=True,),
            "output": "index.html",
        },

        # TRD, top-level page will be removed later
        "trd": {
            "meta": "trd_metadata.json",
            "template": indextmpl,
            "render_args": dict(isTRD=True, ),
            "output": "index.html",
        },

        # ---------------------
        # Product Documentation
        #
        # Liberty
        "liberty/7": {
            "meta": "liberty_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Liberty Linux",
                                version="7",
                                ),
            "output": "index.html",
        },
        "liberty/8": {
            "meta": "liberty_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Liberty Linux",
                                version="8",
                                ),
            "output": "index.html",
        },
        "liberty/9": {
            "meta": "liberty_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Liberty Linux",
                                version="9",
                                ),
            "output": "index.html",
        },
        # SLES for SAP
        "sles-sap/15-SP5": {
            "meta": "slesforsap_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Linux Enterprise Server for SAP Applications",
                                version="15 SP5"),
            "output": "index.html",
        },
        "sles-sap/15-SP4": {
            "meta": "slesforsap_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Linux Enterprise Server for SAP Applications",
                                version="15 SP4"),
            "output": "index.html",
        },
        "sles-sap/15-SP3": {
            "meta": "slesforsap_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Linux Enterprise Server for SAP Applications",
                                version="15 SP3"),
            "output": "index.html",
        },
        "sles-sap/15-SP2": {
            "meta": "slesforsap_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Linux Enterprise Server for SAP Applications",
                                version="15 SP2"),
            "output": "index.html",
        },
        # SLE Micro
        "sle-micro/5.5": {
            "meta": "sle_micro_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Linux Enterprise Micro",
                                version="5.5",
                            ),
            "output": "index.html",
        },
        "sle-micro/5.4": {
            "meta": "sle_micro_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Linux Enterprise Micro",
                                version="5.4",
                            ),
            "output": "index.html",
        },
        # SLE16/Smart Docs
        "sle16": {
            "meta": "sle16_smart_metadata.json",
            "template": indextmpl,
            "render_args": dict(isSmartDocs=True,
                                product="SUSE Linux Enterprise Micro",
                                version="16",
                            ),
            "output": "index.html",
        },
        # SUMA
        "suma/4.3": {
            "meta": "suma_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Manager",
                                version="4.3",
                            ),
            "output": "index.html",
        },
        "suma/5.0": {
            "meta": "suma_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Manager",
                                version="5.0",
                            ),
            "output": "index.html",
        },
        # SLED
        "sled/15-SP5": {
            "meta": "sled_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Linux Enterprise Desktop",
                                version="15 SP5",
                            ),
            "output": "index.html",
        },
        # SLES
        "sles/12-SP5": {
            "meta": "sles_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Linux Enterprise Server",
                                version="12 SP5",
                            ),
            "output": "index.html",
        },
        "sles/15-SP2": {
            "meta": "sles_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Linux Enterprise Server",
                                version="15 SP2",
                            ),
            "output": "index.html",
        },
        "sles/15-SP3": {
            "meta": "sles_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Linux Enterprise Server",
                                version="15 SP3",
                            ),
            "output": "index.html",
        },
        "sles/15-SP4": {
            "meta": "sles_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Linux Enterprise Server",
                                version="15 SP4",
                            ),
            "output": "index.html",
        },
        "sles/15-SP5": {
            "meta": "sles_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Linux Enterprise Server",
                                version="15 SP5",
                            ),
            "output": "index.html",
        },
        # SUSE Edge
        "edge/3.0": {
            "meta": "edge_metadata.json",
            "template": indextmpl,
            "render_args": dict(isProduct=True,
                                product="SUSE Edge",
                                version="3.0",
                            ),
            "output": "index.html",
        },
    }

    logger.debug("Iterating over subitems")
    for item, categories in subitems.items():
        logger.debug("Grabbed %s", item)
        for cat, args in categories:
            logger.debug("Handle subitem %s with args %s", cat, args)
            meta = workdata[item]["meta"]
            template = workdata[item]["template"]
            merged_args = {}
            # Merge the two dicts
            merged_args.update(workdata[item]["render_args"])
            merged_args.update(args)
            output = "index.html"
            workdata[f"{item}/{cat}"] = dict(
                meta=meta,
                template=template,
                # "Protect" against None:
                render_args=merged_args,  # {**render_args, **args}
                output=output,
            )
    # Remove the top-level entry for trd and sbp?
    workdata.pop("trd")
    workdata.pop("sbp")
    # workdata.pop("smart")

    logger.debug("workdata dict %s", workdata)

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
        # Render and save rendered HTML
        logger.debug("Writing output %s with template %s and args=%s",
                     output, template, args)
        output = os.path.join(path, output)
        try:
            with open(output, "w") as fh:
                content = template.render(data=context,
                                          # debug=True,
                                          **args)
                fh.write(content)
            logger.debug("Wrote %s with args=%s", output, args)

        except UndefinedError as err:
            logger.exception("Jinja undefined error", err)
            raise
        except TemplateError as err:
            logger.exception("Jinja error", err)
            raise


    # Iterate over language andD workdata keys:
    for lang, item in itertools.product([lang], # TODO: all_langs,
                                  workdata.keys(),
                                  # site_sections,
                                  # lifecycles,
                                  ):
        meta = os.path.join(CACHE_DIR, servername, target, workdata[item]["meta"])
        template = workdata[item]["template"]
        args: dict = workdata[item]["render_args"]
        output = workdata[item]["output"]

        logger.debug("Processing language %s/%s", lang, item)
        path = os.path.join(outputdir, lang, *(item.split("/")))

        process(path, meta, template, args, output)

    # Search
    process(outputdir, meta, env.get_template("search.html.jinja"), {}, "search.html")
    process(os.path.join(outputdir, lang),
            meta, env.get_template("search.html.jinja"), {}, "search.html")

    logger.debug("All languages and products are processed.")
