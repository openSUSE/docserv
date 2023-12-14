#!/usr/bin/env python3
"""

Create translations
-------------------

1. Make sure you have pybabel installed.
2. Change to "templates" directory on docserv-config repo.
   a) Create a directory structure inside templates:
      $ mkdir -p translations/de/LC_MESSAGES
3. Create a file babel.cfg with the following content
   [jinja2: **.html.jinja2]
   encoding = utf-8
   ignore_tags = script,style
   include_attrs = alt title summary
   keyword = trans
4. Run:
   $ pybabel extract -F babel.cfg -o docserv.pot \
     --copyright-holder="SUSE" --project=docserv \
     *.html.jinja2
5. Initialize the translation file (replace LANG with the language
   you want to create):
   $ pybabel init -i docserv.pot -D docserv -d translations -l LANG
6. "Translate" the MO file in translations/LANG/LC_MESSAGES/docserv.po
   Use lokalize
7. Compile MO to PO:
   $ pybabel compile -D docserv -d translations/ -l de
   compiling catalog translations/de/LC_MESSAGES/docserv.po to translations/de/LC_MESSAGES/docserv.mo
8. Repeat the last step with other languages.


Updating translations
---------------------

1. Extract the new strings:
   $ pybabel extract -F babel.cfg -o docserv.pot \
     --copyright-holder="SUSE" --project=docserv \
     *.html.jinja2
2. Update the catalog translations:
   $ pybabel update -d translations -D docserv -i docserv.pot
   updating catalog translations/de/LC_MESSAGES/docserv.po based on docserv.pot
   updating catalog translations/es/LC_MESSAGES/docserv.po based on docserv.pot
   ...
3. Compile PO to MO

Example
-------

$ docserv-build-navigation  --product="sles" --docset="15-SP2" \
    --stitched-config="/tmp/docserv_stitch_q7pjc_gp/productconfig_simplified_doc-suse-com.xml" \
    --ui-languages="en-us de-de fr-fr pt-br ja-jp zh-cn es-es" \
    --site-sections="main sbp trd smart" \
    --default-site-section="main" \
    --default-ui-language="en-us" \
    --omit-lang-path="en-us" \
    --cache-dir="/var/cache/docserv/docserv/doc-suse-com" \
    --template-dir="/etc/docserv/template-doc-suse-com/" \
    --output-dir="/tmp/docserv_navigation_zmgu11h6" \
    --base-path="/" \
    --fragment-dir="/etc/docserv/fragments-doc-suse-com/fragments" \
    --fragment-l10n-dir="/etc/docserv/fragments-doc-suse-com/l10n"

"""


__version__ = "0.1.0"
__author__ = "Tom Schraitle <tom@suse.de>"

import argparse
import os
from pathlib import Path
import re
import sys
import tempfile

import jinja2


PROG=Path(__file__)
SCRIPTDIR=PROG.parent
JAVA_FLAGS="-Dorg.apache.xerces.xni.parser.XMLParserConfiguration=org.apache.xerces.parsers.XIncludeParserConfiguration"
POSSIBLE_LANGS = tuple(
    "ar-ar,cs-cz,de-de,en-us,es-es,fr-fr,hu-hu,it-it,"
    "ja-jp,ko-kr,nl-nl,pl-pl,pt-br,ru-ru,sv-se,zh-cn,zh-tw".split(",")
)
TEMPLATE_DEFAULT=""
TEMPLATE_PRODUCT=""

#
DS_SHARE_DIR = os.getenv('DOCSERV_SHARE_DIR', "/usr/share/docserv/")
DS_CONFIG_DIR = os.getenv('DOCSERV_CONFIG_DIR', '/etc/config/docserv')
DS_BIN_DIR = os.getenv('DOCSERV_BIN_DIR', '/usr/bin')


# Our Jinja templates
template_path="templates"
# Where to place the JSON data files
data_path='docserv/data'
# Where to place the template's resource files (JS, CSS, images)
res_path='docserv/res/'
# Where to place fragment files
fragment_path='docserv/fragments'
#
enable_ssi_fragments=0
#
all_stylesheet= f"{DS_SHARE_DIR}/build-navigation/list-all-products.xsl"
#
related_stylesheet=f"{DS_SHARE_DIR}/build-navigation/list-related-products.xsl"
#
stylesheet=f"{DS_SHARE_DIR}/build-navigation/build-navigation-json.xsl"


class LanguageAction(argparse.Action):
    """Parse action for languages (option --langs).

    Languages can be separated by comma
    """
    LANG_REGEX = re.compile(r'^([a-z]{2}-[a-z]{2}[, ])*[a-z]{2}-[a-z]{2}$')
    def __call__(self, parser, namespace, values, option_string=None):
        if type(self).LANG_REGEX.match(values):
            languages = re.split("[,; ]", values)
        else:
            parser.error(
                "Wrong syntax. "
                "Each languages must to be in the format '[a-z]{2}-[a-z]{2}'. "
                "More than one language need to be separated by commas."
            )
        # Check the values of the language itself to avoid typos
        invalid_langs = set(languages) - set(POSSIBLE_LANGS)
        if invalid_langs:
            parser.error(
                f"Invalid language(s): {', '.join(invalid_langs)}\n"
                f"(choose from {', '.join(POSSIBLE_LANGS)})"
            )
        if len(languages) != len(set(languages)):
            parser.error("Each language can occur only once")

        setattr(namespace, self.dest, languages)


class SeparateAction(argparse.Action):
    SEP_REGEX = re.compile(r'[ ,;]')
    def __call__(self, parser, namespace, values, option_string=None):
        if type(self).SEP_REGEX.search(values):
            v = [ _ for _ in type(self).SEP_REGEX.split(values) if _.strip() ]
        else:
            parser.error(
                "Wrong syntax. "
                "Each part must be separated by comma, semicolon, or space."
            )
        setattr(namespace, self.dest, v)


def parse_cli(cliargs=None) -> argparse.Namespace:
    """Parse CLI with :class:`argparse.ArgumentParser` and return parsed result

    :param cliargs: Arguments to parse or None (=use sys.argv)
    :return: parsed CLI result
    """
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Version %s written by %s " % (__version__, __author__),
    )

    parser.add_argument("--stitched-config",
                        required=True,
                        type=Path,
                        action="store",
                        help="Full docservconfig file (positive version)"
    )
    parser.add_argument("--template-dir",
                        required=True,
                        type=Path,
                        action="store",
                        help="Path to the template directory"
    )
    parser.add_argument("--cache-dir",
                        required=True,
                        type=Path,
                        help="Document metadata cache directory as generated by docserv script."
    )
    parser.add_argument("--output-dir",
                        required=True,
                        type=Path,
                        action="store",
                        help="Where to output HTML files"
    )
    parser.add_argument("--ui-languages",
                        required=True,
                        action=LanguageAction,
                        help="Languages that are supported by the UI templates"
    )
    parser.add_argument("--default-ui-language",
                        required=True,
                        action="store",
                        help="Default language of UI translations, used to find fallback translations."
    )
    parser.add_argument("--site-sections",
                        required=True,
                        # action="store",
                        action=SeparateAction,
                        help="Site sections that are supported"
    )
    parser.add_argument("--default-site-section",
                        required=True,
                        action="store",
                        help="Default site section, also used as the fallback"
    )
    parser.add_argument("--omit-lang-path",
                        required=True,
                        action="store",
                        help="Allows omitting the path component to the default page language"
    )
    parser.add_argument("--product",
                        required=True,
                        action="store",
                        help="Product to build UI for"
    )
    parser.add_argument("--docset",
                        required=True,
                        action="store",
                        help="Docset to build UI for"
    )
    parser.add_argument("--base_path",
                        required=True,
                        type=Path,
                        action="store",
                        help="Relative path to the root of the docserv2 directory on the host"
    )
    # Optional arguments
    parser.add_argument("--internal-mode",
                        action="store_true",
                        help="Enable features that are not supposed to be shown publically"
    )
    parser.add_argument("--fragment-dir",
                        action="store",
                        type=Path,
                        help="Directory for translatable SSI fragments"
    )
    parser.add_argument("--fragment-l10n-dir",
                        action="store",
                        type=Path,
                        help="Directory path for fragment translations (mandatory if previous parameter is set)"
    )

    # Parsing the arguments:
    args = parser.parse_args(args=cliargs)

    # Everything looks successful, lets prepare the environment:
    prepare(args)

    return args


def prepare(args: argparse.Namespace):
    """Prepare the environment
    """
    if args.fragment_dir:
        enable_ssi_fragments = 1

    if not args.cache_dir.exists():
        args.cache_dir.mkdir(parents=True, exist_ok=True)

    if not args.output_dir.exists():
        args.output_dir.mkdir(parents=True, exist_ok=True)


def render(args: argparse.Namespace):
    """Render the templates
    """
    from babel.support import Translations
    def get_translations():
        translations = Translations.load('translations', locales=['en'])
        return translations

    def install_translations(env):
        translations = get_translations()
        env.install_gettext_translations(translations)

    print("render, pwd=", os.getcwd())
    loader=jinja2.FileSystemLoader(
        [str(args.template_dir),
         "templates",
         DS_CONFIG_DIR
         ]
    )
    env = jinja2.Environment(
        extensions=['jinja2.ext.i18n', 'jinja2.ext.debug'],
        trim_blocks=True,
        loader=loader,
        autoescape=jinja2.select_autoescape()
    )
    # Install translations into the environment
    # install_translations(env)

    # print("Jinja", env, dir(env))
    template = env.get_template(f"section-{args.default_site_section}.supported.html.jinja2")

    if args.default_site_section == "main":
        doclist = ["Subscription Management System",
                   "SUSE Enterprise Storage",
                   "SUSE Linux Enterprise Server",
                   ]
    elif args.default_site_section == "sbp":
        doclist = ["Systems management",
                   "Storage",
                   "SAP applications on SUSE Linux Enterprise 15",
                   "SAP applications on SUSE Linux Enterprise 12",
                   "Linux server",
                   "Linux desktop",
                   "Containers and virtualization",
                   "Cloud computing",
                   ]
    elif args.default_site_section == "trd":
        doclist = ["Container Management", "Linux"]
    else:
        doclist = []


    return template.render(
        site=args.default_site_section,
        allsites=args.site_sections,
        product=args.product,
        docset=args.docset,
        title=f"{args.product}-{args.docset}",
        lang=args.default_ui_language,
        doclist=doclist,
    )


def main(cliargs=None):
    try:
        args = parse_cli(cliargs)
        # print("> Script:", PROG)
        # print("> Directory:", SCRIPTDIR)
        # print(args)

        # with tempfile.TemporaryDirectory(
        #     dir="/tmp",
        #     prefix="docserv-build-navigation-",
        #     delete=False,
        # ) as temp_dir:
        #    temp_dir = Path(temp_dir)
        #    print('> created temporary directory', temp_dir)
        data = render(args)
        print("> Data received %d" % len(data))
        index = args.output_dir / "index.html"
        index.write_text(data)
        print(f"> Written to {str(index)}")
        print("Done.")

    except jinja2.exceptions.TemplateRuntimeError as err:
        print((f"ERROR ({err.__class__.__name__}) "
               # f"name={err.name}:{err.lineno}\n"
               f"  {err}"),
              file=sys.stderr
        )
        # print(dir(err))
        print(dir(err.with_traceback))
        return 10


    except jinja2.exceptions.TemplateSyntaxError as err:
        print((f"ERROR ({err.__class__.__name__}) "
               f"name={err.name}:{err.lineno}\n"
               f"  {err}"),
              file=sys.stderr
        )
        return 100

    except jinja2.exceptions.TemplateNotFound as err:
        print(f"ERROR ({err.__class__.__name__}) {err}", file=sys.stderr)
        return 400

    #except Exception as exc:
    #    print(f"ERROR ({err.__class__.__name__}) {err}", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())