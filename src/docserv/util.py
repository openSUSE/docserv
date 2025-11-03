import shlex
import subprocess


def run(command: str) -> tuple: # tuple[int, bytes, bytes]
    """Run a command as subprocess

    :param command: the command to be executed
    :return: a tuple with the return code (int),
             the output (bytes) and
             the error message (bytes)
    """
    cmd = shlex.split(command)
    s = subprocess.Popen(cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = s.communicate()
    return int(s.returncode), out, err