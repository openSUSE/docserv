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
    version="3.0",
    packages=find_packages('src'),
    package_dir={'': 'src'},
    entry_points={
        'console_scripts': [
            'docserv = docserv.docserv:main',
        ]
    },
    scripts=['bin/docserv-stitch', 'bin/docserv-dirs', 'bin/docserv-createconfig', 'bin/docserv-build-navigation', 'bin/docserv-dchash'],
    install_requires=[],
    data_files=[
        ('/usr/share/docserv/example/', ['config/docserv.ini']),
        ('/usr/share/docserv/example/config/config.d/', glob('config/config.d/sample_product.xml')),
        # template can be .html or .php (and potentially more in the future)
        ('/usr/share/docserv/example/template/', glob('config/templates/template.*')),
        ('/usr/share/docserv/example/template/', ['config/templates/translation.xml']),
        # will likely contain .css and .js and perhaps imagery of some sort
        ('/usr/share/docserv/example/template/res/', glob('config/templates/res/*')),
        ('/usr/share/docserv/validate-product-config/', ['share/validate-product-config/product-config-schema.rnc']),
        # there are bound to be more checks over time in here and they may include XSLT-based ones
        ('/usr/share/docserv/validate-product-config/checks/', glob('share/validate-product-config/checks/check-*.sh')),
        ('/usr/share/docserv/validate-product-config/checks/', glob('share/validate-product-config/checks/check-*.xsl')),
        # both of these currently contain a single .xsl file but there may be more in the future
        ('/usr/share/docserv/simplify-product-config/', glob('share/simplify-product-config/*.xsl')),
        ('/usr/share/docserv/build-navigation/',  glob('share/build-navigation/*.xsl')),
        ('/usr/lib/systemd/system/', ['systemd/docserv@.service']),
    ],
    author="SUSE Documentation Team",
    author_email="doc-team@suse.com",
    description="Build server for DAPS documentation",
    license="GPL-3.0-or-later",
    keywords="DAPS build documentation",
    url="http://github.com/SUSEdoc/",
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
