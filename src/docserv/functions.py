import logging
import os
import re
import subprocess
from email.mime.text import MIMEText
from hashlib import md5

my_env = os.environ

logger = logging.getLogger('docserv')


def resource_to_filename(url):
    """
    To create valid and unique directory names, transform Git remote URLs:
    https://github.com/SUSE/doc-sle.git -> [MD5_SUM]-doc-sle.git
    """
    remote_id = md5(bytes(url, 'utf-8')).hexdigest()
    humane_name = re.sub(r'[^A-Za-z0-9._+-]', '-',(re.sub(r'^.*/', '', url)))
    return ("%s-%s", remote_id, humane_name)


def mail(text, subject, to):
    """
    Send mail via the local sendmail command.
    """
    logger.debug("Sending mail to %s", to)
    # 100kB of text is enough, right?
    text = ('[message truncated]\n\n' + text[:100000] + '...') if len(text) > 100000 else text
    msg = MIMEText(text)
    msg["To"] = to
    msg["Subject"] = subject
    p = subprocess.Popen(["/usr/sbin/sendmail", "-t", "-oi"],
                         stdin=subprocess.PIPE, universal_newlines=True)
    p.communicate(msg.as_string())


def print_help():
    print("""This is a daemon. Invoke it with either of the following commands:

> systemctl start docserv@CONFIG_FILE
or
> docserv CONFIG_FILE

The CONFIG_FILE must reside in /etc/docserv/ and end with .ini.""")
