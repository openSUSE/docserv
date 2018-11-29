# /usr/bin/env python3
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


from setuptools import setup, find_packages

setup(
    name="docserv",
    version="0.9.10",
    packages=find_packages(),
    scripts=['bin/docserv', 'bin/docserv-stitch'],
    install_requires=[],
    data_files=[
        ('/etc/docserv/', ['config/docserv.ini']),
        ('/etc/docserv/config.d/', ['config/config.d/sles.xml']),
        ('/usr/lib/systemd/system/', ['systemd/docserv.service']),
        ('/usr/share/docserv/templates/', ['share/templates/index.html']),
        ('/usr/share/docserv/xslt/', ['share/xslt/positive-config.xsl']),
        ('/usr/share/docserv/schema/', ['share/schema/config-validation.rnc']),
        ('/usr/share/docserv/', ['schema/config-validation.rnc'])
    ],
    author="SUSE Documentation Team",
    author_email="doc-team@suse.com",
    description="Build server for DAPS documentation",
    license="GPL-2.0-or-later",
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
