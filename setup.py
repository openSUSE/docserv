from setuptools import setup, find_packages
setup(
    name="docserv",
    version="0.9.6",
    packages=find_packages(),
    scripts=['bin/docserv', 'bin/docserv-stitch'],
    install_requires=[],
    data_files=[
        ('/etc/docserv/', ['config/docserv.ini']),
        ('/etc/docserv/config.d/', ['config/config.d/sles.xml']),
        ('/usr/lib/systemd/system/', ['systemd/docserv.service']),
        ('/usr/share/docserv/templates/', ['templates/index.html'])
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
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ]
)
