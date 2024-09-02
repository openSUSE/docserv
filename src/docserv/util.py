import logging
import re
import shlex
import shutil
import subprocess
import os
import typing as t

from .common import BIN_DIR, CACHE_DIR, CONF_DIR, DOCSERV_CODE_DIR, SHARE_DIR, PROJECT_DIR


#:
curly_pattern = re.compile(r"\{([a-zA-Z0-9._-]+)\}")

#: Instantiate our logger
logger = logging.getLogger(__name__)


def run(command: str|list[str]) -> tuple[int, str, str]:
    """Run a command as subprocess

    :param command: the command to be executed
    :return: a tuple with the return code (int),
             the output (bytes) and
             the error message (bytes)
    """
    if isinstance(command, str):
        command = shlex.split(t.cast(str, command))
    logger.debug("Running command: %s", command)
    s = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = s.communicate()

    return int(s.returncode), out.decode("utf-8").rstrip(), err.decode("utf-8").rstrip()


def replace_placeholders(path: str, currenttargetname: str, servername: str) -> str:
    """Replace placeholder in curly brackets notation
    """
    # servername = self.config['server']['name']
    path = path.format(
        # the project directory where to find the Docserv INI file
        projectdir=PROJECT_DIR,
        # The current name of the server (=docserv ini filename)
        servername=servername,
        # The current target name that is processed
        targetname=currenttargetname,
        # the config directory
        configdir=CONF_DIR,
        # the cache directory
        cachedir=CACHE_DIR,
        # cache dir plus servername and targetname
        fullcachedir=os.path.join(CACHE_DIR,
                        servername,
                        currenttargetname,
                        ),
        # The docserv directory where all source code is stored
        codedir=DOCSERV_CODE_DIR,
    )

    # Just do some sanity checking for curly brackets that got NOT replaced:
    match = curly_pattern.search(path)
    if match:
        raise ValueError(f"Unknown placeholder {match.group(0)!r} in path {path!r}.")
    # logger.debug("Path after replacing placeholders: %s", path)
    return path


def removedir(path: str) -> None:
    """Remove a directory and all its content
    """
    logger.debug("Removing directory: %s", path)
    shutil.rmtree(path)
