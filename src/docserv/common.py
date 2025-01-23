import os

#: Contains the scripts that Docserv uses
BIN_DIR = os.getenv('DOCSERV_BIN_DIR', "/usr/bin/")

#: Contains the Docserv XML config files, Jinja templates etc.
CONF_DIR = os.getenv('DOCSERV_CONFIG_DIR', "/etc/docserv/")

#: Contains some shareable resources
SHARE_DIR = os.getenv('DOCSERV_SHARE_DIR', "/usr/share/docserv/")

#: Contains caching content
CACHE_DIR = os.getenv('DOCSERV_CACHE_DIR', "/var/cache/docserv/")

#: Contains the root directory of a project dir, usually docserv-devel,
#: when used from Git
PROJECT_DIR = os.getenv('DOCSERV_PROJECT_DIR', "/tmp/docserv-devel")

#: Contains the path to the Docserv source code
DOCSERV_CODE_DIR = os.path.join(os.path.dirname(__file__))

#: The file extension of the meta file
META_FILE_EXT = ".meta"