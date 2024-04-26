import os

# Variables
BIN_DIR = os.getenv('DOCSERV_BIN_DIR', "/usr/bin/")
CONF_DIR = os.getenv('DOCSERV_CONFIG_DIR', "/etc/docserv/")
SHARE_DIR = os.getenv('DOCSERV_SHARE_DIR', "/usr/share/docserv/")
CACHE_DIR = os.getenv('DOCSERV_CACHE_DIR', "/var/cache/docserv/")

#: Contains the root directory of a project dir, usually docserv-devel,
#: when used from Git
PROJECT_DIR = os.getenv('DOCSERV_PROJECT_DIR', "/tmp/docserv-devel")

DOCSERV_CODE_DIR = os.path.join(os.path.dirname(__file__))