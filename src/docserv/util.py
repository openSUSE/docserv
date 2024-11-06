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
    returncode = int(s.returncode)
    out = out.decode("utf-8").rstrip()
    err = err.decode("utf-8").rstrip()

    logger.debug("  Return code: %s", returncode)
    if out:
        logger.debug("  stdout: %s", out)
    if err:
        logger.debug("  stderr: %s", err)

    return returncode, out, err


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


def stitching(stitchcmd: str,
              valid_languages: str,
              valid_site_sections: str,
              target: str,
              config_dir: str,
              stitch_tmp_file: str,
              revalidate: bool = True,
              ) -> tuple[int, str|bytes, str|bytes]:
    # cmd = ('%s --simplify --revalidate-only '
    #        '--valid-languages="%s" '
    #        '--valid-site-sections="%s" '
    #        '%s %s'
    #        ) % (
    #     os.path.join(BIN_DIR, 'docserv-stitch'),
    #     " ".join(self.config['server']['valid_languages']),
    #     self.config['targets'][target]['site_sections'],
    #     self.config['targets'][target]['config_dir'],
    #     self.stitch_tmp_file,
    #     )
    revalidate_str = "--revalidate-only" if revalidate else ""
    cmd = (f"{stitchcmd} "
            "--simplify "
            f"{revalidate_str} "
            f'--valid-languages="{valid_languages}" '
            f'--valid-site-sections="{valid_site_sections}" '
            f"--target={target} "
            f"{config_dir} "
            f"{stitch_tmp_file}"
            )
    logger.debug("Stitching command: %s", cmd)
    rc, out, err = run(cmd)
    return rc, out, err