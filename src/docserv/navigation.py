import itertools
import json
import logging
from pathlib import Path
import os.path

from lxml import etree
from jinja2 import Environment, FileSystemLoader

from .common import BIN_DIR, CACHE_DIR, CONF_DIR, SHARE_DIR


logger = logging.getLogger(__name__)


def init_jinja_template(path) -> Environment:
    """Initialize the Jinja templates"""
    env = Environment(loader=FileSystemLoader(path),
                      trim_blocks=True,
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
    """
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


def render_and_save(env, template: str, outputdir: str, bih) -> None:
    """Render a Jinja template and save the output to a file"""
    # Replaces/extends docserv-build-navigation script
    servername = bih.config['server']['name']
    target = bih.build_instruction['target']
    product = bih.product
    docset = bih.docset
    lang = bih.lang
    # Templates
    indextmpl = bih.config['targets'][target]['jinja_template_index']
    hometmpl = bih.config['targets'][target]['jinja_template_home']
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
    site_sections, default_site_section
    )

    workdata = {
        "products": {
            "meta": bih.config['targets'][target]['jinjacontext_home'],
            "template": hometmpl,
            "render-args": dict(),
            "output": "homepage2.html",
        },

        "smart": {
            "meta": "smart_metadata.json",  # TODO: introduce a key in
            "template": indextmpl,
            "render-args": dict(dataSmartDocs=True),
            "output": "SmartDocs.html",
        },

        "sbp": {
            "meta": "sdb_metadata.json",
            "template": indextmpl,
            "render-args": dict(isSBP=True, category="Systems Management"),
            "output": "systems-management.html",
        },

        "trd-ibm": {
            "meta": "trd_metadata.json",
            "template": indextmpl, # TODO: use correct TRD template
            "render-args": dict(isTRD=True, partner='IBM'),
            "output": "IBM.html",
        },
    }

    # Load the Jinja template
    tmpl = env.get_template(template)

    # Iterate over language and workdata keys:
    for lang, item in itertools.product(["en-us"], # TODO: all_langs,
                                  workdata.keys(),
                                  # site_sections,
                                  # lifecycles,
                                  ):
        meta = os.path.join(CACHE_DIR, servername, target, workdata[item]["meta"])
        template = workdata[item]["template"]
        args: dict = workdata[item]["render-args"]
        output = workdata[item]["output"]

        if not os.path.exists(meta):
            raise FileNotFoundError(
                f"Expected JSON file {meta}, but I couldn't find it."
            )

        logger.debug("Processing language %s/%s", item, lang)
        os.makedirs(f"{outputdir}/{lang}", exist_ok=True)

        # Read JSON metadata
        with open(meta, "r") as fh:
            context = json.load(fh)
            logger.debug("JSON context successfully loaded (%r)", meta)

        # Render and save rendered HTML
        output = os.path.join(outputdir, lang, output)
        with open(output, "w") as fh:
            content = tmpl.render(data=context, **args)
            fh.write(content)
            logger.debug("Wrote %s", output)

    logger.debug("All languages and products are processed.")


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
