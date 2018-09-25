from setuptools import setup, find_packages
setup(
    name="docserv",
    version="0.1.4",
    packages=find_packages(),
    scripts=['bin/docserv', 'bin/docserv-build'],
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
