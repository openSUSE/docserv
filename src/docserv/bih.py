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

from docserv.deliverable import Deliverable
from docserv.functions import mail, resource_to_filename
from docserv.repolock import RepoLock

BIN_DIR = os.getenv('DOCSERV_BIN_DIR', "/usr/bin/")
CONF_DIR = os.getenv('DOCSERV_CONFIG_DIR', "/etc/docserv/")
SHARE_DIR = os.getenv('DOCSERV_SHARE_DIR', "/usr/share/docserv/")
CACHE_DIR = os.getenv('DOCSERV_CACHE_DIR', "/var/cache/docserv/")

logger = logging.getLogger('docserv')


class BuildInstructionHandler:
    """
    This object is created when a new build request
    is coming in via the API. This object parses the
    incoming request and with the help of the XML
    configuration creates a set of Deliverables.
    """

    def __init__(self, build_instruction, config, gitLocks, gitLocksLock, thread_id):
        # A dict with meta information about a Deliverable.
        # It is filled with Deliverable.dict().
        self.deliverables = {}
        self.deliverables_lock = threading.Lock()
        # A dict that contains all Deliverable objects
        # mapped with the Deliverable ID.
        self.deliverable_objects = {}
        self.deliverable_objects_lock = threading.Lock()
        # A list of Deliverable IDs that have not yet been
        # build / have to be built.
        self.deliverables_open = []
        self.deliverables_open_lock = threading.Lock()
        # A list of Deliverable IDs that are currently
        # building. That means a worker thread is currently
        # running daps for them.
        self.deliverables_building = []
        self.deliverables_building_lock = threading.Lock()

        self.cleanup_done = False
        self.cleanup_lock = threading.Lock()

        if self.validate(build_instruction, config):
            self.initialized = True
            self.build_instruction = build_instruction
            if 'deliverables' in build_instruction:
                self.deliverables = build_instruction['deliverables']
            self.config = config
            if not self.read_conf_dir():
                self.initialized = False
                return
            self.git_lock = RepoLock(resource_to_filename(
                self.remote_repo), thread_id, gitLocks, gitLocksLock)
            self.prepare_repo(thread_id)
            self.get_commit_hash()
        else:
            self.initialized = False
        return

    def cleanup(self):
        """
        Remove temporary files when build fails or all deliverables
        are finished.
        """
        if not self.cleanup_lock.acquire(False):
            return False

        logger.debug("Cleaning up %s", json.dumps(self.build_instruction['id']))

        commands = {}
        n = 0
        # (re-)generate overview page
        sync_source_tmp = tempfile.mkdtemp(prefix="docserv_oview_")
        commands[n] = {}
        commands[n]['cmd'] = "docserv-buildoverview %s--stitched_config=\"%s\" --ui-languages=\"%s\" --default-ui-language=%s --cache-dir=%s --doc-language=%s --template_dir=%s --output_dir=%s" % (
            "--internal-mode " if self.config['targets'][self.build_instruction['target']
                                                         ]['languages'] == "yes" else "",
            self.stitch_tmp_file,
            self.config['targets'][self.build_instruction['target']
                                   ]['languages'],
            self.config['targets'][self.build_instruction['target']
                                   ]['default_lang'],
            self.deliverable_cache_base_dir,
            self.build_instruction['lang'],
            self.config['targets'][self.build_instruction['target']
                                   ]['template_dir'],
            sync_source_tmp)

        # rsync build target directory to backup path
        backup_path = self.config['targets'][self.build_instruction['target']]['backup_path']
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "rsync -lr %s/ %s" % (
            sync_source_tmp, backup_path)

        # rsync built target directory with web server
        target_path = self.config['targets'][self.build_instruction['target']]['target_path']
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "rsync -lr %s/ %s" % (
            sync_source_tmp, target_path)

        if hasattr(self, 'local_repo_build_dir'):
            # build target directory
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "rm -rf %s" % self.local_repo_build_dir

        for i in range(0, n + 1):
            cmd = shlex.split(commands[i]['cmd'])
            logger.debug("Cleaning up %s, %s",
                         self.build_instruction['id'], commands[i]['cmd'])
            s = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = s.communicate()
            if int(s.returncode) != 0:
                logger.warning("Clean up failed! Unexpected return value %i for '%s'",
                               s.returncode, commands[i]['cmd'])
                self.mail(out, err, commands[i]['cmd'])
        self.cleanup_done = True
        self.cleanup_lock.release()

    def __del__(self):
        if not self.cleanup_done:
            self.cleanup()

    def __str__(self):
        return json.dumps(self.build_instruction)

    def __repr__(self):
        return self.build_instruction

    def dict(self):
        retval = self.build_instruction
        retval['open'] = self.deliverables_open
        retval['building'] = self.deliverables_building
        retval['deliverables'] = self.deliverables
        return retval

    def __getitem__(self, arg):
        return self.build_instruction

    def mail(self, command, out, err):
        msg = """Sorry. docserv² failed on build instruction:
Repo/Branch: %s %s

=== Build instruction ===
%s

=== Failed command ===
%s

=== STDOUT ===
%s

=== STDERR ===
%s
""" % (
            self.remote_repo,
            self.branch,
            self.build_instruction,
            command,
            out,
            err
        )
        to = ', '.join(self.maintainers)
        subject = "[docserv²] Failed build preparation"
        mail(msg, subject, to)

    def read_conf_dir(self):
        """
        Use the docserv-stitch command to stitch all single XML configuration
        files to a big config file. Then parse it and extract required information
        for the current build instruction.
        """
        target = self.build_instruction['target']
        if not self.config['targets'][target]['active'] == "yes":
            logger.debug("Target %s not active.", target)
            return False
        self.stitch_tmp_file = os.path.join(tempfile.mkdtemp(
            prefix="docserv_stitch_"), 'docserv_config_full.xml')
        logger.debug("Stitching XML config directory to %s",
                     self.stitch_tmp_file)
        cmd = '%s/docserv-stitch --make-positive --valid-languages="%s" %s %s' % (
            BIN_DIR,
            self.config['server']['valid_languages'],
            self.config['targets'][target]['config_dir'],
            self.stitch_tmp_file)
        logger.debug("Stitching command: %s", cmd)
        cmd = shlex.split(cmd)
        s = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        s.communicate()[0]
        rc = int(s.returncode)
        if rc == 0:
            logger.debug("Stitching of %s successful",
                         self.config['targets'][target]['config_dir'])
        else:
            logger.warning("Stitching of %s failed!",
                           self.config['targets'][target]['config_dir'])
            self.initialized = False
            return False

        self.local_repo_build_dir = os.path.join(self.config['server']['temp_repo_dir'], ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=12)))

        # then read all files into an xml tree
        self.tree = ElementTree.parse(self.stitch_tmp_file)
        xml_root = self.tree.getroot()
        try:
            xpath = ".//product[@productid='%s']/maintainers/contact" % (
                self.build_instruction['product'])
            self.maintainers = []
            stuff = xml_root.findall(xpath)
            for contact in stuff:
                self.maintainers.append(contact.text)

            xpath = ".//product[@productid='%s']/docset[@setid='%s']/builddocs/language[@lang='%s']/branch" % (
                self.build_instruction['product'], self.build_instruction['docset'], self.build_instruction['lang'])
            self.branch = xml_root.find(xpath).text

            xpath = ".//product[@productid='%s']/docset[@setid='%s']/builddocs/language[@lang='%s']/subdir" % (
                self.build_instruction['product'], self.build_instruction['docset'], self.build_instruction['lang'])
            self.build_source_dir = os.path.join(
                self.local_repo_build_dir,
                xml_root.find(xpath).text)

            xpath = ".//product[@productid='%s']/docset[@setid='%s']/builddocs/git/remote" % (
                self.build_instruction['product'], self.build_instruction['docset'])
            self.remote_repo = xml_root.find(xpath).text
        except AttributeError:
            logger.warning("Failed to parse xpath: %s", xpath)
            return False
        self.deliverable_cache_base_dir = '%s/%s' % (
            CACHE_DIR, self.config['server']['name'])
        return True

    def prepare_repo(self, thread_id):
        """
        Prepare the repository required for building the deliverables.
        This function updates the local clone of the repository, then
        clones the required branch into another local and temporary
        repository. With this, multiple builds of different branches
        can run at the same time.
        """
        commands = {}
        # Clone locally cached repository, does nothing if exists
        n = 0
        local_repo_cache_dir = os.path.join(
            self.config['server']['repo_dir'], resource_to_filename(self.remote_repo))
        commands[n] = {}
        commands[n]['cmd'] = "git clone %s %s" % (
            self.remote_repo, local_repo_cache_dir)
        commands[n]['ret_val'] = None
        commands[n]['repo_lock'] = local_repo_cache_dir

        # update locally cached repo
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "git -C %s pull --all " % local_repo_cache_dir
        commands[n]['ret_val'] = 0
        commands[n]['repo_lock'] = local_repo_cache_dir

        # update locally cached repo
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "git -C %s checkout %s " % (
            local_repo_cache_dir, self.branch)
        commands[n]['ret_val'] = 0
        commands[n]['repo_lock'] = local_repo_cache_dir

        # Create local copy in temp build dir
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "git clone --single-branch --branch %s %s %s" % (
            self.branch, local_repo_cache_dir, self.local_repo_build_dir)
        commands[n]['ret_val'] = 0
        commands[n]['repo_lock'] = None

        for i in range(0, n + 1):
            cmd = shlex.split(commands[i]['cmd'])
            if commands[i]['repo_lock'] is not None:
                self.git_lock.acquire()
            logger.debug("Thread %i: %s", thread_id, commands[i]['cmd'])
            s = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = s.communicate()
            self.git_lock.release()
            if commands[i]['ret_val'] is not None and not commands[i]['ret_val'] == int(s.returncode):
                logger.warning("Build failed! Unexpected return value %i for '%s'",
                               s.returncode, commands[i]['cmd'])
                self.mail(commands[i]['cmd'], out.decode(
                    'utf-8'), err.decode('utf-8'))
                self.initialized = False
                return False

        return True

    def get_commit_hash(self):
        """
        Extract HEAD commit hash from branch.
        """
        cmd = shlex.split("git -C "+self.local_repo_build_dir +
                          " log --format=\"%H\" -n 1")
        s = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        self.build_instruction['commit'] = s.communicate()[
            0].decode('utf-8').rstrip()
        logger.debug("Current commit hash: %s",
                     self.build_instruction['commit'])

    def validate(self, build_instruction, config):
        """
        Validate completeness of build instruction. Format:
        {'docset': '15ga', 'lang': 'en', 'product': 'sles', 'target': 'external'}
        """
        #
        if not isinstance(build_instruction, dict):
            logger.warning("Validation: Is not a dict")
            return False
        if not isinstance(build_instruction['docset'], str):
            logger.warning("Validation: docset is not a string")
            return False
        if not isinstance(build_instruction['lang'], str):
            logger.warning("Validation: lang is not a string")
            return False
        if not isinstance(build_instruction['product'], str):
            logger.warning("Validation: product is not a string")
            return False
        if not isinstance(build_instruction['target'], str):
            logger.warning("Validation: target is not a string")
            return False
        logger.debug("Valid build instruction: %s", build_instruction['id'])
        return True

    def generate_deliverables(self):
        """
        Iterate through delvierable elements in configuration and create
        instances of the Deliverable class for each.
        """
        if not self.initialized:
            return False
        xml_root = self.tree.getroot()
        logger.debug("Generating deliverables.")
        xpath = ".//product[@productid='%s']/docset[@setid='%s']/builddocs/language[@lang='%s']/deliverable" % (
            self.build_instruction['product'], self.build_instruction['docset'], self.build_instruction['lang'])
        for xml_deliverable in xml_root.findall(xpath):
            build_formats = xml_deliverable.find(".//format").attrib
            for build_format in build_formats:
                if build_formats[build_format] == "no" or build_formats[build_format] == "0" or build_formats[build_format] == "false":
                    continue
                subdeliverables = []
                for subdeliverable in xml_deliverable.findall("subdeliverable"):
                    subdeliverables.append(subdeliverable.text)
                deliverable = Deliverable(self,
                                          xml_deliverable.find(".//dc").text,
                                          build_format,
                                          subdeliverables
                                          )
                self.deliverables[deliverable.id] = deliverable.dict()
                self.deliverable_objects[deliverable.id] = deliverable
                self.deliverables_open.append(deliverable.id)
        # after all deliverables are generated, we don't need the xml tree anymore
        self.tree = None
        return True

    def get_deliverable(self):
        """
        return deliverable object that can run to build the output
        return None if all deliverables are already building
        return 'done' if all deliverables have finished building
        """
        retval = None
        deliverable_id = None
        with self.deliverables_open_lock:
            if len(self.deliverables_open) > 0:
                deliverable_id = self.deliverables_open.pop()
                with self.deliverable_objects_lock:
                    retval = self.deliverable_objects.pop(deliverable_id)
        if retval is not None:
            with self.deliverables_building_lock:
                self.deliverables_building.append(deliverable_id)
            return retval
        with self.deliverables_building_lock:
            retval = len(self.deliverables_building)
        if retval == 0:
            return 'done'
        else:
            return None
