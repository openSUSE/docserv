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

# Variables
from .common import BIN_DIR, CACHE_DIR, CONF_DIR, SHARE_DIR
from .deliverable import Deliverable
from .functions import feedback_message, resource_to_filename
# from .log import logger
from .repolock import RepoLock
from .navigation import render_and_save
from .util import run

logger = logging.getLogger(__name__)


class BuildInstructionHandler:
    """
    This object is created when a new build request
    is coming in via the API. This object parses the
    incoming request and with the help of the XML
    configuration creates a set of Deliverables.
    """

    def __init__(self, build_instruction, config, stitch_tmp_dir, gitLocks, gitLocksLock, thread_id):
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
        # A dict taken from the JSON file passed to the Jinja
        # template
        self.context = {}  # NOT USED CURRENTLY!

        self.cleanup_done = False
        self.cleanup_lock = threading.Lock()

        self.stitch_tmp_dir = stitch_tmp_dir

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
            # only execute these if there is a <builddocs> section for the BI
            if self.build_docs:
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
        Example: /tmp/docserv_deliverable_caasp_2_en-us_12e312d3/en-us/caasp/2
        """
        prefix = "docserv_deliverable_{}_{}_{}_".format(self.product, self.docset, self.lang)
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

        # overall status:
        # 1. initialization failed -> "fail"
        # 2. initialization succeeded + product has no deliverables -> "success"
        # 3. all deliverables succeeded -> "success"
        # 4. one or more deliverables failed -> "fail"
        bi_overall_status = 'success'
        if not self.initialized:
            bi_overall_status = 'fail'
        else:
            for deliverable in self.deliverables.keys():
                if self.deliverables[deliverable]['status'] == 'fail':
                    bi_overall_status = 'fail'
                    logger.debug("Deliverable failed: %s => %s",
                                 deliverable, item
                                 )
                    break

        logger.debug("Cleaning up after %s (%s)", json.dumps(self.build_instruction['id']), bi_overall_status)

        commands = {}
        n = 0

        target = self.build_instruction['target']
        if bi_overall_status == 'success':
            backup_path = self.config['targets'][target]['backup_path']
            backup_docset_relative_path = os.path.join(backup_path, self.docset_relative_path)

            if hasattr(self, 'tmp_bi_path') and os.listdir(self.tmp_bi_path):

                # create zip archive
                n += 1
                commands[n] = {}
                zip_name = "{}-{}-{}.zip".format(self.product, self.docset, self.lang)
                zip_formats = self.config['targets'][target]['zip_formats'].replace(" ",",")
                create_archive_cmd = '%s --input-path %s --output-path %s --zip-formats %s --cache-path %s --relative-output-path %s --product %s --docset %s --language %s' % (
                    os.path.join(BIN_DIR, 'docserv-create-archive'),
                    self.tmp_bi_path,
                    os.path.join(self.tmp_bi_path, zip_name),
                    zip_formats,
                    os.path.join(self.deliverable_cache_base_dir, target),
                    os.path.join(self.docset_relative_path, zip_name),
                    self.product,
                    self.docset,
                    self.lang)
                commands[n]['cmd'] = create_archive_cmd

            tmp_dir_nav = tempfile.mkdtemp(prefix="docserv_navigation_")
            if self.navigation == 'linked' or self.navigation == 'hidden':
                # (re-)generate navigation page
                n += 1
                commands[n] = {}
                """
                commands[n]['cmd'] = (# The space after each line is important:
                                      "docserv-build-navigation "
                                      # 1
                                      "%s "
                                      # 2
                                      "--product=\"%s\" "
                                      # 3
                                      "--docset=\"%s\" "
                                      # 4
                                      "--stitched-config=\"%s\" "
                                      # 5
                                      "--ui-languages=\"%s\" "
                                      # 6
                                      "--site-sections=\"%s\" "
                                      # 7
                                      "--default-site-section=\"%s\" "
                                      # 8
                                      "--default-ui-language=\"%s\" "
                                      # 9
                                      "%s "
                                      # 10
                                      "--cache-dir=\"%s\" "
                                      # 11
                                      "--template-dir=\"%s\" "
                                      # 12
                                      "--jinja-template-dir=\"%s\" "
                                      # 13
                                      "--output-dir=\"%s\" "
                                      # 14
                                      "--base-path=\"%s\" %s"
                                      ) % (
                    # 1
                    "--internal-mode" if self.config['targets'][target]['internal'] == "yes" else "",
                    # 2
                    self.build_instruction['product'],
                    # 3
                    self.build_instruction['docset'],
                    # 4
                    self.stitch_tmp_file,
                    # 5
                    self.config['targets'][target]['languages'],
                    # 6
                    self.config['targets'][target]['site_sections'],
                    # 7
                    self.config['targets'][target]['default_site_section'],
                    # 8
                    self.config['targets'][target]['default_lang'],
                    # 9
                    "--omit-lang-path=\"%s\"" % self.config['targets'][target]['default_lang'] if
                                self.config['targets'][target]['omit_default_lang_path'] == "yes" else "",
                    # 10
                    os.path.join(self.deliverable_cache_base_dir, target),
                    # 11
                    self.config['targets'][target]['template_dir'],
                    # 12
                    self.config['targets'][target]['jinja_template_dir'],
                    # 13
                    tmp_dir_nav,
                    # 14
                    self.config['targets'][target]['server_base_path'],
                    "--fragment-dir=\"%s\" --fragment-l10n-dir=\"%s\"" % (
                            self.config['targets'][target]['fragment_dir'],
                            self.config['targets'][target]['fragment_l10n_dir']) if
                        self.config['targets'][target]['enable_ssi_fragments'] == "yes" else "",
                )
                """
                cfg = self.config['targets'][target]
                commands[n]['cmd'] = render_and_save  # (env, template, output, context)
                commands[n]['args'] = (
                    # env
                    cfg['jinja_env'],
                    # template name
                    cfg['jinja_template_home'],
                    # output
                    tmp_dir_nav,
                    # context:
                    self,
                )


            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "rsync -r %s/ %s" % (
              self.config['targets'][target]['server_root_files'], tmp_dir_nav)

            # remove contents of backup path for current build instruction
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "rm -rf %s" % (backup_docset_relative_path)

            # ideally, we'd copy in one fell swoop, but I guess two separate
            # commands do work too..?
            if hasattr(self, 'tmp_bi_path') and os.listdir(self.tmp_bi_path):

                # copy temp build instruction directory to backup path;
                # we only do that for products that are unpublished/beta/supported,
                # unsupported products only get an archive
                n += 1
                commands[n] = {}
                if self.lifecycle != 'unsupported':
                    commands[n]['cmd'] = "rsync -lr %s/ %s" % (self.tmp_dir_bi, backup_path)
                else:
                    # recreate directory
                    commands[n]['cmd'] = "mkdir -p %s" % (backup_docset_relative_path)
                    # copy zip archive to directory created above
                    n += 1
                    commands[n] = {}
                    commands[n]['cmd'] = "cp %s %s" % (os.path.join(self.tmp_bi_path, zip_name), backup_docset_relative_path)

            # rsync navigational pages dir to backup path
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "rsync -lr %s/ %s" % (
                tmp_dir_nav, backup_path)

            # remove temp directory for navigation page
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "echo rm -rf %s" % tmp_dir_nav
            commands[n]['execute_after_error'] = True

        if hasattr(self, 'tmp_bi_path'):
            # remove temp build instruction directory
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "echo rm -rf %s" % self.tmp_dir_bi
            commands[n]['execute_after_error'] = True

        if hasattr(self, 'local_repo_build_dir'):
            # build target directory
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "echo rm -rf %s" % self.local_repo_build_dir
            commands[n]['execute_after_error'] = True

        # rsync local backup path with web server target path
        if (bi_overall_status == 'success' and
            self.config['targets'][target]['enable_target_sync'] == 'yes'):
            target_path = self.config['targets'][target]['target_path']
            n += 1
            commands[n] = {}
            commands[n]['cmd'] = "rsync --exclude-from '%s' --delete-after -lr %s/ %s" % (
                os.path.join(SHARE_DIR, 'rsync', 'rsync_excludes.txt'),
                backup_path,
                target_path,
            )

        if not commands:
            self.cleanup_done = True
            self.cleanup_lock.release()
            return

        previous_error = False
        for i in range(1, n + 1):
            # Distinguish between a shell call and a function call
            cmd = commands[i]['cmd']
            execute_after_error = commands[i].get('execute_after_error', False)

            if callable(cmd):
                # cmd is a function
                args = commands[i].get('args', tuple())
                previous_error = cmd(*args)
            else:
                previous_error = self.call_command(cmd, execute_after_error)

        self.cleanup_done = True
        self.cleanup_lock.release()

    def call_command(self, cmd: str, execute_after_error: bool=False) -> bool:
        logger.debug("Cleaning up %s, %s", self.build_instruction['id'], cmd)

        rc, out, err = run(cmd)
        previous_error = False
        if rc:
            logger.warning("Cleanup failed! Unexpected return value %i for '%s'",
                           rc, cmd)
            self.mail(cmd, out, err)
            previous_error = True

        return previous_error


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
        if not hasattr(self, 'remote_repo'):
            self.remote_repo = "(none)"
        if not hasattr(self, 'branch'):
            self.branch = "(none)"

        msg = """Cheerio!

Docserv² failed to execute a command during the following build instruction:

Product:        %s
Docset:         %s
Language:       %s
Target Server:  %s

Repository:     %s
Branch:         %s


These are the details:

=== Failed Command ===

%s


=== stdout ===

%s


=== stderr ===

%s
""" % (
            self.build_instruction['product'],
            self.build_instruction['docset'],
            self.build_instruction['lang'],
            self.build_instruction['target'],
            self.remote_repo,
            self.branch,
            command,
            out,
            err
        )
        to = ', '.join(self.maintainers)
        subject = ("[docserv²] Failed to execute command (%s/%s, %s)" % (
            self.build_instruction['product'],
            self.build_instruction['docset'],
            self.build_instruction['lang']))
        send_mail = False
        if self.config['server']['enable_mail'] == 'yes':
            send_mail = True
        feedback_message(msg, subject, to, send_mail)

    def read_conf_dir(self):
        """
        Use the docserv-stitch command to stitch all single XML configuration
        files to a big config file. Then parse it and extract required information
        for the current build instruction.
        """
        target = self.build_instruction['target']
        try:
            if not self.config['targets'][target]['active'] == "yes":
                logger.debug("Target %s not active.", target)
                return False
        except KeyError:
            logger.debug("Target %s does not exist.", target)
            return False

        self.stitch_tmp_file = os.path.join(self.stitch_tmp_dir,
            ('productconfig_simplified_%s.xml' % target))
        logger.debug("Stitching XML config directory to %s",
                     self.stitch_tmp_file)
        cmd = ('%s --simplify --revalidate-only '
               '--valid-languages="%s" '
               '--valid-site-sections="%s" '
               '%s %s'
               ) % (
            os.path.join(BIN_DIR, 'docserv-stitch'),
            self.config['server']['valid_languages'],
            self.config['targets'][target]['site_sections'],
            self.config['targets'][target]['config_dir'],
            self.stitch_tmp_file,
            )
        logger.debug("Stitching command: %s", cmd)
        rc, self.out, self.err = run(cmd)
        if not rc:
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
            self.tree.xpath("//product[@productid='%s']/docset[@setid='%s']" % (self.product, self.docset))[0]
        except (AttributeError, IndexError):
            logger.warning("%s/%s is not configured. Cancelling build instruction." % (self.product, self.docset))
            self.initialized = False
            return False

        valid_languages_split = self.config['server']['valid_languages'].split(' ')
        if not self.lang in valid_languages_split:
            logger.warning( "Language %s is not valid. "
                            "This configuration allows the following language codes: %s. "
                            "Cancelling build instruction." %
                            (self.lang,
                             self.config['server']['valid_languages']))
            self.initialized = False
            return False

        try:
            xpath = "//product[@productid='%s']/maintainers/contact" % (
                self.product)
            self.maintainers = []
            contacts = self.tree.findall(xpath)
            for contact in contacts:
                self.maintainers.append(contact.text)
            xpath = "//product[@productid='%s']/docset[@setid='%s']/@lifecycle" % (
                self.product, self.docset)
            self.lifecycle = str(self.tree.xpath(xpath)[0])
        except (AttributeError, IndexError):
            logger.warning("Failed to parse xpath: %s", xpath)
            self.initialized = False
            return False

        # check if there is any buildable documentation in the language
        # requested -- it's possible that there only are internal/external
        # sections but there is no builddocs section (or none for the language
        # in question).
        self.build_docs = True
        xpath = "//product[@productid='%s']/docset[@setid='%s']/builddocs/language[@lang='%s']" % (
            self.product, self.docset, self.lang)
        if len(self.tree.xpath(xpath)) == 0:
            logger.debug("No buildable documentation for %s/%s/%s. Will update navigation only." % (
                self.product, self.docset, self.lang))
            self.build_docs = False

        try:
            xpath = "//product[@productid='%s']/docset[@setid='%s']/@navigation" % (
                self.product, self.docset)
            self.navigation = str(self.tree.xpath(xpath)[0])
        except (AttributeError, IndexError):
            self.navigation = 'linked'

        if self.build_docs:
            try:
                xpath = "//product[@productid='%s']/docset[@setid='%s']/builddocs/language[@lang='%s']/branch" % (
                    self.product, self.docset, self.lang)
                self.branch = self.tree.find(xpath).text

                xpath = "//product[@productid='%s']/docset[@setid='%s']/builddocs/git/@remote" % (
                    self.product, self.docset)
                self.remote_repo = str(self.tree.xpath(xpath)[0])
            except AttributeError:
                logger.warning("Failed to parse xpath: %s", xpath)
                return False

            try:
                xpath = "//product[@productid='%s']/docset[@setid='%s']/builddocs/buildcontainer/@image" % (
                    self.product, self.docset)
                self.build_container = str(self.tree.xpath(xpath)[0])
            except (AttributeError, IndexError):
                self.build_container = False

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

        # for a few commands below, we assume a default remote named "origin"
        default_branch="origin"
        commands = {}
        # clone locally cached repository, does nothing if exists
        n = 0
        local_repo_cache_dir = os.path.join(
            self.config['server']['repo_dir'], resource_to_filename(self.remote_repo))
        commands[n] = {}
        commands[n]['cmd'] = "git clone \'%s\' \'%s\'" % (
            self.remote_repo, local_repo_cache_dir)
        commands[n]['ret_val'] = None

        # fetch default remote for locally cached repo
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "git -C \'%s\' fetch --prune \'%s\'" % (local_repo_cache_dir, default_branch)
        commands[n]['ret_val'] = 0

        # check out the required branch
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "git -C \'%s\' checkout \'%s\'" % (
            local_repo_cache_dir, self.branch)
        commands[n]['ret_val'] = 0

        # reset the local branch, to be able to deal with force-pushes etc.
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "git -C \'%s\' reset --hard \'%s/%s\'" % (
            local_repo_cache_dir, default_branch, self.branch)
        commands[n]['ret_val'] = 0

        # Create local copy in temp build dir
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "git clone --single-branch --branch \'%s\' \'%s\' \'%s\'" % (
            self.branch, local_repo_cache_dir, self.local_repo_build_dir)
        commands[n]['ret_val'] = 0

        # The lock on the Git repo needs to be acquired early, otherwise a
        # competing BI may lead to us intermittently checking out a different
        # branch and thus failing to include the most recent changes in our
        # the single-branch repo we clone at the end.
        self.git_lock.acquire()
        for i in range(0, n + 1):
            cmd = shlex.split(commands[i]['cmd'])
            logger.debug("Thread %i: %s", thread_id, commands[i]['cmd'])
            s = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = s.communicate()
            if commands[i]['ret_val'] is not None and not commands[i]['ret_val'] == int(s.returncode):
                logger.warning("Build failed! Unexpected return value %i for '%s'",
                               s.returncode, commands[i]['cmd'])
                self.mail(commands[i]['cmd'], out.decode(
                    'utf-8'), err.decode('utf-8'))
                self.initialized = False
                self.git_lock.release()
                return False
        self.git_lock.release()

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
            dc = xml_deliverable.find(".//dc").text
            build_formats = xml_deliverable.find(".//format").attrib
            try:
                source_dir = os.path.join(
                    self.build_source_dir,
                    xml_deliverable.find(".//subdir").text)
            except AttributeError:
                source_dir = self.build_source_dir

            for build_format in build_formats:
                if build_formats[build_format] == "false":
                    continue
                subdeliverables = []
                for subdeliverable in xml_deliverable.findall("subdeliverable"):
                    subdeliverables.append(subdeliverable.text)

                xslt_params = []
                for param in xml_deliverable.findall("param"):
                    xslt_params.append("%s='%s'" % (param.xpath("./@name")[0], param.text))

                deliverable = Deliverable(self,
                                          dc,
                                          (source_dir,
                                          self.tmp_dir_bi,
                                          self.docset_relative_path),
                                          build_format,
                                          subdeliverables,
                                          xslt_params,
                                          self.build_container,
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
