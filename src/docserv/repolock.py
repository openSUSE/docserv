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

from docserv.functions import resource_to_filename

my_env = os.environ

logger = logging.getLogger('docserv')

class RepoLock:
    """
    It is not safe to run multiple git commands on one repository
    at the same time. For example, running git pull in parallel
    in one repo breaks git. This can happen if build intructions
    for several languages are sent at the same time. Therefore
    we need to lock the usage of git repos down to only one thread
    at a time.
    """
    def __init__(self, repo_dir, thread_id, gitLocks, gitLocksLock):
        """
        repo_dir -- path to a repository
        thread_id -- ID of thread calling this method
        gitLocks -- dict of all existing gitLocks
        gitLocksLock -- Lock for accessing gitLocks
        """
        self.gitLocks = gitLocks
        self.gitLocksLock = gitLocksLock
        self.resource_name = resource_to_filename(repo_dir)
        self.gitLocksLock.acquire()
        if self.resource_name not in gitLocks:
            self.gitLocks[self.resource_name] = threading.Lock()
        self.gitLocksLock.release()
        self.acquired = False
        self.thread_id = thread_id

    def acquire(self, blocking=True):
        if self.gitLocks[self.resource_name].acquire(blocking):
            self.acquired = True
            logger.debug("Thread %i: Acquired lock %s.",
                         self.thread_id,
                         self.resource_name)
            return True
        return False

    def release(self):
        if self.acquired:
            self.gitLocks[self.resource_name].release()
            self.acquired = False
            logger.debug("Thread %i: Released lock %s.",
                         self.thread_id,
                         self.resource_name)
