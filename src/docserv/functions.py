import configparser
import datetime
import hashlib
import json
import logging
import os
import queue
import random
import shlex
import signal
import socket
import string
import subprocess
import sys
import tempfile
import threading
import time
from email.mime.text import MIMEText
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from xml.etree import ElementTree, cElementTree

my_env = os.environ

logger = logging.getLogger('docserv')


def resource_to_filename(url):
    """
    To create valid directory names, transform URLs like https://github.com/SUSE/doc-sle
    into https___github_com_SUSE_doc_sle
    """
    replace = "/\\-.,:;#+`´{}()[]!\"§$%&"
    for char in replace:
        url = str(url).replace(char, '_')
    return url


def mail(text, subject, to):
    """
    Send mail via the local sendmail command.
    """
    logger.debug("Sending mail to %s", to)
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
