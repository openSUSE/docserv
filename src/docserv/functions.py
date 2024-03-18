import datetime
import json
import logging
import os
import subprocess
import tempfile
from email.mime.text import MIMEText

my_env = os.environ

logger = logging.getLogger('docserv')

BIN_DIR = os.getenv('DOCSERV_BIN_DIR', "/usr/bin/")
CONF_DIR = os.getenv('DOCSERV_CONFIG_DIR', "/etc/docserv/")
SHARE_DIR = os.getenv('DOCSERV_SHARE_DIR', "/usr/share/docserv/")
CACHE_DIR = os.getenv('DOCSERV_CACHE_DIR', "/var/cache/docserv/")


def resource_to_filename(url):
    """
    To create valid directory names, transform URLs like https://github.com/SUSE/doc-sle
    into https___github_com_SUSE_doc_sle
    """
    replace = "/\\-.,:;#+`´{}()[]!\"§$%&"
    for char in replace:
        url = str(url).replace(char, '_')
    return url


def feedback_message(text, subject, to, send_mail = False):
    """
    If mail is enabled, send mail via the local sendmail command.
    Alternatively, write a text file to the cache directory.
    """
    # 100kB of text is enough, right?
    text = ('[message truncated]\n\n' + text[:100000] + '...') if len(text) > 100000 else text
    if send_mail == True:
        logger.debug("Sending mail to %s", to)
        msg = MIMEText(text)
        msg["To"] = to
        msg["Subject"] = subject
        p = subprocess.Popen(["/usr/sbin/sendmail", "-t", "-oi"],
                             stdin=subprocess.PIPE, universal_newlines=True)
        p.communicate(msg.as_string())
    else:
        now = datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()
        handle, path = tempfile.mkstemp(suffix=".txt", prefix="docserv-message-%s-" % now, dir=CACHE_DIR, text=True)
        logger.debug("Writing message to %s", path)
        msg = open(handle, 'w')
        msg.write('To:      %s\nSubject: %s\n\n%s' % (to, subject, text))
        msg.close()

def parse_d2d_filelist(directory, format):
    """
    Parse the returned filelist.json from daps2docker which contains the
    list of documents that were built.
    """
    try:
        f = open(os.path.join(directory, 'filelist.json'), 'r')
    except FileNotFoundError:
        return False

    try:
        filelist = json.loads(f.read())
    # Under some circumstances, we get empty/invalid file lists. In such
    # cases, it's probably better to declare the build failed.
    except json.decoder.JSONDecodeError:
        return False

    f.close()

    try:
        for deliverable in filelist.keys():
            if (filelist[deliverable]['format'] == format and
                filelist[deliverable]['status'] == 'succeeded' and
                filelist[deliverable]['file'] != False):
                # returning the first result is fine as long as we only build
                # 1 document per D2D run, if we ever switched to building
                # different documents in the same container, this would
                # become an issue.
                return filelist[deliverable]['file'].strip()
    except KeyError:
        return False

def print_help():
    print(f"""This is a daemon. Invoke it with either of the following commands:

> systemctl start docserv@CONFIG_FILE
or
> docserv CONFIG_FILE

The CONFIG_FILE must reside in {CONF_DIR} and end with .ini.""")
