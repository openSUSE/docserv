from setuptools import setup, find_packages
setup(
    name="docserv",
    version="0.1",
    packages=find_packages(),
    scripts=['docserv.py', 'docserv-build.py'],
    install_requires=[],
    package_data={
        '': ['*.rst']
    },
    author="SUSE Documentation Team",
    author_email="doc-team@suse.com",
    description="Build server for DAPS documentation",
    license="GPL-2.0-or-later",
    keywords="DAPS build documentation",
    url="http://github.com/SUSEdoc/",
    project_urls={
        "Bug Tracker": "http://github.com/SUSEdoc/docserv/issues",
        "Documentation": "http://github.com/SUSEdoc/docserv/wiki",
        "Source Code": "http://github.com/SUSEdoc/docserv",
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Topic :: Documentation',
        'Topic :: Software Development :: Documentation',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ]
)
