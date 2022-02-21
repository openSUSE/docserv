#!/usr/bin/env python3
#
# Copyright (c) 2018 SUSE Linux GmbH
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of version 3 of the GNU General Public License as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, contact SUSE LLC.
#
# To contact SUSE about this file by physical or electronic mail,
# you may find current contact information at www.suse.com


from glob import glob
from os.path import basename, dirname, join as joinpath, splitext

from setuptools import find_packages, setup

setup(
    name="docserv",
    version="6.6",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'docserv = docserv.docserv:main',
        ]
    },
    scripts=[
        'bin/docserv-stitch',
        'bin/docserv-dirs',
        'bin/docserv-create-archive',
        'bin/docserv-createconfig',
        'bin/docserv-build-navigation',
        'bin/docserv-dchash',
        'bin/docserv-write-daps-param-file',
        'bin/docserv-write-xslt-param-file',
    ],
    install_requires=[],
    data_files=[
        ('/usr/share/docserv/example/', ['config/my-site.ini']),
        ('/usr/share/docserv/example/', ['config/xslt-params.txt']),
        ('/usr/share/docserv/example/product-config/', glob('config/product-config/*.xml')),
        # can contain .htaccess, a favicon, etc.
        ('/usr/share/docserv/example/server-root-files/', glob('config/server-root-files/*')),
        # template can be .html or .php (and potentially more in the future)
        ('/usr/share/docserv/example/template/', glob('config/templates/template-*')),
        # will likely contain .css and .js and perhaps imagery of some sort
        ('/usr/share/docserv/example/template/res/', glob('config/templates/res/*')),
        ('/usr/share/docserv/validate-product-config/', ['share/validate-product-config/product-config-schema.rnc']),
        # validation check, Bash-based or XSLT-based
        ('/usr/share/docserv/validate-product-config/', glob('share/validate-product-config/global-check-*')),
        ('/usr/share/docserv/validate-product-config/checks/', glob('share/validate-product-config/checks/check-*.sh')),
        ('/usr/share/docserv/validate-product-config/checks/', glob('share/validate-product-config/checks/check-*.xsl')),
        # contains a single .xsl file
        ('/usr/share/docserv/simplify-product-config/', glob('share/simplify-product-config/*.xsl')),
        # contains a couple .xsl files and a single .rnc
        ('/usr/share/docserv/build-navigation/', glob('share/build-navigation/*.xsl')),
        ('/usr/share/docserv/build-navigation/', glob('share/build-navigation/*.rnc')),
        # contains a single .js file currently
        ('/usr/share/docserv/build-navigation/web-resources/', glob('share/build-navigation/web-resources/*')),
        # contains a single .txt file currently
        ('/usr/share/docserv/rsync/', glob('share/rsync/*')),
        ('/usr/lib/systemd/system/', ['systemd/docserv@.service']),
    ],
    author="SUSE Documentation Team",
    author_email="doc-team@suse.com",
    description="Build server for DAPS documentation",
    license="GPL-2.0-or-later",
    keywords="DAPS build documentation",
    url="http://github.com/openSUSE/docserv",
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Topic :: Documentation',
        'Topic :: Software Development :: Documentation',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
