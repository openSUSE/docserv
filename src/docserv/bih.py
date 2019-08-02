import json
import logging
import os
import random
import shlex
import shutil
import string
import subprocess
import tempfile
import threading
from lxml import etree

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
            self.product = build_instruction['product']
            self.docset = build_instruction['docset']
            self.lang = build_instruction['lang']
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
            self.create_dir_structure()
        else:
            self.initialized = False
        return

    def create_dir_structure(self):
        """Create directory structure command.
        This directory is used within a build instruction.
        Example: /tmp/ds_caasp_2_en-us_12e312d3/en-us/caasp/2
        """
        prefix = "docserv_{}_{}_{}_".format(self.product, self.docset, self.lang)
        self.tmp_dir_bi = tempfile.mkdtemp(prefix=prefix)

        self.docset_relative_path = os.path.join(self.lang, self.product, self.docset)
        self.tmp_bi_path = os.path.join(self.tmp_dir_bi, self.docset_relative_path)

        os.makedirs(self.tmp_bi_path, exist_ok=True)

    def cleanup(self):
        """
        Copy built documentation to the right places.
        Remove temporary files when build fails or all deliverables
        are finished.
        """
        if not self.cleanup_lock.acquire(False):
            return False

        logger.debug("Cleaning up %s", json.dumps(self.build_instruction['id']))

        commands = {}
        n = 0
        if hasattr(self, 'tmp_bi_path') and os.listdir(self.tmp_bi_path):
            backup_path = self.config['targets'][self.build_instruction['target']]['backup_path']
            backup_docset_relative_path = os.path.join(backup_path, self.docset_relative_path)

            # remove contents of backup path for current build instruction
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "rm -rf %s" % (backup_docset_relative_path)

            # copy temp build instruction directory to backup path;
            # we only do that for products that are unpublished/beta/supported,
            # unsupported products only get an archive
            n += 1
            commands[n] = {}
            if self.lifecycle != 'unsupported':
                commands[n]['cmd'] = "rsync -lr %s/ %s" % (self.tmp_dir_bi, backup_path)
            else:
                commands[n]['cmd'] = "mkdir -p %s" % os.path.join(backup_path, self.docset_relative_path)

            # create zip archive
            n += 1
            commands[n] = {}
            zip_name = "{}-{}-{}.zip".format(self.product, self.docset, self.lang)
            zip_formats = self.config['targets'][self.build_instruction['target']]['zip_formats'].replace(" ",",")
            create_archive_cmd = '%s --input-path %s --output-path %s --zip-formats %s --cache-path %s --relative-output-path %s --product %s --docset %s --language %s' % (
                os.path.join(BIN_DIR, 'docserv-create-archive'),
                self.tmp_bi_path,
                os.path.join(backup_docset_relative_path, zip_name),
                zip_formats,
                os.path.join(self.deliverable_cache_base_dir, self.build_instruction['target']),
                os.path.join(self.docset_relative_path, zip_name),
                self.product,
                self.docset,
                self.lang)
            commands[n]['cmd'] = create_archive_cmd

            # (re-)generate navigation page
            tmp_dir_nav = tempfile.mkdtemp(prefix="docserv_navigation_")
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "docserv-build-navigation %s --product=\"%s\" --docset=\"%s\" --stitched-config=\"%s\" --ui-languages=\"%s\" --cache-dir=\"%s\" --template-dir=\"%s\" --output-dir=\"%s\" --base-path=\"%s\"" % (
                "--internal-mode" if self.config['targets'][self.build_instruction['target']
                                                             ]['internal'] == "yes" else "",
                self.build_instruction['product'],
                self.build_instruction['docset'],
                self.stitch_tmp_file,
                self.config['targets'][self.build_instruction['target']]['languages'],
                os.path.join(self.deliverable_cache_base_dir, self.build_instruction['target']),
                self.config['targets'][self.build_instruction['target']]['template_dir'],
                tmp_dir_nav,
                self.config['targets'][self.build_instruction['target']]['server_base_path'],
            )
            # rsync navigational pages dir to backup path
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "rsync -lr %s/ %s" % (
                tmp_dir_nav, backup_path)

            # rsync local backup path with web server target path
            target_path = self.config['targets'][self.build_instruction['target']]['target_path']
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "rsync --delete-after -lr %s/ %s" % (backup_path, target_path)

            # remove temp directory for navigation page
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "rm -rf %s" % tmp_dir_nav

        if hasattr(self, 'tmp_bi_path'):
            # remove temp build instruction directory
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "rm -rf %s" % self.tmp_dir_bi

        if hasattr(self, 'local_repo_build_dir'):
            # build target directory
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "rm -rf %s" % self.local_repo_build_dir


        if not commands:
            self.cleanup_done = True
            self.cleanup_lock.release()
            return

        for i in range(1, n + 1):
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

        self.stitch_tmp_dir = os.path.join(tempfile.gettempdir(), 'docserv_stitch')
        os.makedirs(self.stitch_tmp_dir, exist_ok = True)
        self.stitch_tmp_file = os.path.join(self.stitch_tmp_dir,
            ('productconfig_simplified_%s.xml' % target))
        logger.debug("Stitching XML config directory to %s",
                     self.stitch_tmp_file)
        cmd = '%s --simplify --revalidate-only --valid-languages="%s" %s %s' % (
            os.path.join(BIN_DIR, 'docserv-stitch'),
            self.config['server']['valid_languages'],
            self.config['targets'][target]['config_dir'],
            self.stitch_tmp_file)
        logger.debug("Stitching command: %s", cmd)
        cmd = shlex.split(cmd)
        s = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        self.out, self.err = s.communicate()
        rc = int(s.returncode)
        if rc == 0:
            logger.debug("Stitching of %s successful",
                         self.config['targets'][target]['config_dir'])
        else:
            logger.warning("Stitching of %s failed!",
                           self.config['targets'][target]['config_dir'])
            logger.warning("Stitching STDOUT: %s", self.out.decode('utf-8'))
            logger.warning("Stitching STDERR: %s", self.err.decode('utf-8'))

            self.initialized = False
            return False

        self.local_repo_build_dir = os.path.join(self.config['server']['temp_repo_dir'], ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=12)))

        # then read all files into an xml tree
        self.tree = etree.parse(self.stitch_tmp_file)
        try:
            xpath = "//product[@productid='%s']/maintainers/contact" % (
                self.product)
            self.maintainers = []
            stuff = self.tree.findall(xpath)
            for contact in stuff:
                self.maintainers.append(contact.text)

            xpath = "//product[@productid='%s']/docset[@setid='%s']/builddocs/language[@lang='%s']/branch" % (
                self.product, self.docset, self.lang)
            self.branch = self.tree.find(xpath).text

            xpath = "//product[@productid='%s']/docset[@setid='%s']/builddocs/git/@remote" % (
                self.product, self.docset)
            self.remote_repo = str(self.tree.xpath(xpath)[0])

            xpath = "//product[@productid='%s']/docset[@setid='%s']/@lifecycle" % (
                self.product, self.docset)
            self.lifecycle = str(self.tree.xpath(xpath)[0])
        except AttributeError:
            logger.warning("Failed to parse xpath: %s", xpath)
            return False

        try:
            xpath = "//product[@productid='%s']/docset[@setid='%s']/builddocs/language[@lang='%s']/subdir" % (
                self.product, self.docset, self.lang)
            self.build_source_dir = os.path.join(
                self.local_repo_build_dir,
                self.tree.find(xpath).text)

        except AttributeError:
            self.build_source_dir = self.local_repo_build_dir

        if self.lifecycle == 'unpublished' and self.config['targets'][target]['internal'] != 'yes':
            logger.warning("Intentionally not building 'unpublished' docset '%s' of product '%s' for public target server '%s'.",
               self.docset, self.product, target)
            logger.warning("Set docset lifecycle value to 'beta'/'supported'/'unsupported' to make it appear publicly.")
            self.initialized = False
            return False

        self.deliverable_cache_base_dir = os.path.join(
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
        Iterate through deliverable elements in configuration and create
        instances of the Deliverable class for each.
        """
        if not self.initialized:
            return False

        # Clean up cache for the product now, so we're not confused later on
        # when it comes to building the navigational pages.
        deliverable_cache_dir = os.path.join(
            self.deliverable_cache_base_dir,
            self.build_instruction['target'],
            self.docset_relative_path,
        )
        try:
            shutil.rmtree(deliverable_cache_dir)
        except FileNotFoundError:
            pass

        logger.debug("Generating deliverables.")
        xpath = "//product[@productid='%s']/docset[@setid='%s']/builddocs/language[@lang='%s']/deliverable" % (
            self.product, self.docset, self.lang)
        for xml_deliverable in self.tree.findall(xpath):
            build_formats = xml_deliverable.find(".//format").attrib
            for build_format in build_formats:
                if build_formats[build_format] == "false":
                    continue
                subdeliverables = []
                for subdeliverable in xml_deliverable.findall("subdeliverable"):
                    subdeliverables.append(subdeliverable.text)
                deliverable = Deliverable(self,
                                          xml_deliverable.find(".//dc").text,
                                          (self.tmp_dir_bi,
                                          self.docset_relative_path),
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
