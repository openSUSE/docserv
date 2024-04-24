import json
from pathlib import Path
import os.path

from lxml import etree
from jinja2 import Environment, FileSystemLoader

from .common import BIN_DIR, CACHE_DIR, CONF_DIR, SHARE_DIR
from .log import logger


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


def render_and_save(env, template, output, bih) -> None:
    """Render a Jinja template and save the output to a file"""
    servername = bih.config['server']['name']
    target = bih.build_instruction['target']
    product = bih.product
    docset = bih.docset
    lang = bih.lang
    jsondata = bih.config['targets'][target]['jinjacontext_home']
    logger.debug("""Useful variables:
    docserv config: %r
    target: %r
    product: %r
    docset: %r
    lang: %r
    jsondata: %r
    """, servername, target, product, docset, lang, jsondata)

    # logger.debug("configfile=%s target=%s", bih.config['server']['name'], target)
    contextfile = os.path.join(CACHE_DIR,
                               servername,
                               target,
                               jsondata
                               )
    logger.debug("Loading JSON context from %s", contextfile)
    if not os.path.exists(contextfile):
        logger.error("JSON context file for rending not found. Expected %s", contextfile)
        context = {}
        return

    with open(contextfile, "r") as fh:
        context = json.load(fh)
    logger.debug("JSON context successfully loaded.")

    logger.debug("contextfile=%s", contextfile)

    output = "/tmp/index.html"
    tmpl = env.get_template(template)
    with open(output, "w") as fh:
        fh.write(tmpl.render(context))


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
