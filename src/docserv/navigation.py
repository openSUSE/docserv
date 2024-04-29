import itertools
import json
import logging
from pathlib import Path
import os.path
from typing import Any

from lxml import etree
from jinja2 import Environment, FileSystemLoader

from .common import BIN_DIR, CACHE_DIR, CONF_DIR, SHARE_DIR


logger = logging.getLogger(__name__)


def init_jinja_template(path) -> Environment:
    """Initialize the Jinja templates"""
    env = Environment(loader=FileSystemLoader(path),
                      trim_blocks=True,
                      lstrip_blocks=True,
                      # extensions=
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
    """Render a Jinja template and save the output to a file

    :param env: the Jinja environment
    :param outputdir: the output directory where to store the rendered HTML files
    :param bih: the instance of the BuildInstructionHandler
    """
    # Replaces/extends docserv-build-navigation script
    servername = bih.config['server']['name']
    target = bih.build_instruction['target']
    product = bih.product
    docset = bih.docset
    lang = bih.lang
    # Templates, could raise TemplateNotFound
    indextmpl = env.get_template(bih.config['targets'][target]['jinja_template_index'])
    hometmpl = env.get_template(bih.config['targets'][target]['jinja_template_home'])

    # trdtmpl = bih.config['targets'][target]['jinja_template_trd']
    # templatedir = bih.config['targets'][target]['jinja_template_dir']
    #
    jsondata = bih.config['targets'][target]['jinjacontext_home']
    site_sections = bih.config['targets'][target]['site_sections'].split()
    default_site_section = bih.config['targets'][target]['default_site_section']
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
    jsondata: %r
    site_sections: %r
    default_site_section: %r
    """, servername, target, product, docset, lang, outputdir, jsondata,
    site_sections, default_site_section,
    )

    # TODO: retrieve them from JSON
    subitems = { # dict[str, list[tuple[str, dict]]]
        # str:   list[tuple]
        "smart": [('container', dict(dataSmartDocs=True)),
                  ('deploy-upgrade', dict(dataSmartDocs=True)),
                  ('micro-clouds', dict(dataSmartDocs=True)),
                  ('network', dict(dataSmartDocs=True)),
                  ('rancher', dict(dataSmartDocs=True)),
                  ('security', dict(dataSmartDocs=True)),
                  ('systems-management', dict(dataSmartDocs=True)),
                  ('systemtuning-performance', dict(dataSmartDocs=True)),
                  ('virtualization-cloud', dict(dataSmartDocs=True)),
                  ],

        "sbp": [('cloud-computing', dict(isSBP=True, category="Cloud Computing")),
                ('container-virtualization', dict(isSBP=True, category="Container and Virtualization")),
                ('deprecated', dict(isSBP=True, category="Deprecated")),
                ('desktop-linux', dict(isSBP=True, category="Desktop and Linux")),
                ('sap-12', dict(isSBP=True, category="SAP 12")),
                ('sap-15', dict(isSBP=True, category="SAP 15")),
                ('server-linux', dict(isSBP=True, category="Server and Linux")),
                ('storage', dict(isSBP=True, category="Storage")),
                ('systems-management', dict(isSBP=True, category="Systems Management")),
                ],

        "trd": [("ibm", dict(isTRD=True, partner="IBM")),
                ("suse", dict(isTRD=True, partner="SUSE")),
                ("cisco", dict(isTRD=True, partner="Cisco")),
                ],
    }


    # TODO: Somehow we need to create this data automatically
    workdata = {
        # This entry will be remove later
        "": {
            "meta": bih.config['targets'][target]['jinjacontext_home'],
            "template": hometmpl,
            "render_args": dict(),
            "output": "index.html",
        },

        # Smart Docs
        "smart": {
            "meta": "smart_metadata.json",  # TODO: introduce a key in
            "template": indextmpl,
            "render_args": dict(dataSmartDocs=True),
            "output": "index.html",
        },

        # SBP
        "sbp": {
            "meta": "sdb_metadata.json",
            "template": indextmpl,
            "render_args": dict(isSBP=True,),
            "output": "index.html",
        },

        # TRD
        "trd": {
            "meta": "trd_metadata.json",
            "template": indextmpl,
            "render_args": dict(isTRD=True, ),
            "output": "index.html",
        },
        # "trd/ibm": {
        #     "meta": "trd_metadata.json",
        #     "template": indextmpl,
        #     "render_args": dict(isTRD=True, partner='IBM'),
        #     "output": "index.html",
        # },
        # "trd/suse": {
        #     "meta": "trd_metadata.json",
        #     "template": indextmpl,
        #     "render_args": dict(isTRD=True, partner='SUSE'),
        #     "output": "index.html",
        # },
        # "trd/cisco": {
        #     "meta": "trd_metadata.json",
        #     "template": indextmpl,
        #     "render_args": dict(isTRD=True, partner='SUSE'),
        #     "output": "index.html",
        # },
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
        output = os.path.join(path, output)
        with open(output, "w") as fh:
            content = template.render(data=context, **args)
            fh.write(content)
        logger.debug("Wrote %s", output)


    # Manually create the home page and remove it from the workdata dictionary
    # home = workdata.pop("home")
    # meta, template, args, output = (home["meta"],
    #                                home["template"],
    #                                home["render_args"],
    #                                home["output"])
    # process(outputdir, meta, template, args, output)


    # Iterate over language and workdata keys:
    for lang, item in itertools.product(["en-us"], # TODO: all_langs,
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


    logger.debug("All languages and products are processed.")
