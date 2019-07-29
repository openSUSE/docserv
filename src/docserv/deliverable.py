import hashlib
import logging
import os
import shlex
import subprocess
import tempfile
import time
# FIXME: switch to LXML
from xml.etree import ElementTree, cElementTree

from docserv.functions import mail, resource_to_filename
from docserv.repolock import RepoLock

logger = logging.getLogger('docserv')

BIN_DIR = os.getenv('DOCSERV_BIN_DIR', "/usr/bin/")
CONF_DIR = os.getenv('DOCSERV_CONFIG_DIR', "/etc/docserv/")
SHARE_DIR = os.getenv('DOCSERV_SHARE_DIR', "/usr/share/docserv/")
CACHE_DIR = os.getenv('DOCSERV_CACHE_DIR', "/var/cache/docserv/")


class Deliverable:
    """
    This class represents deliverable-elements in the XML configuration
    (config.d directory) during builds. A build instruction generates
    one of these objects.
    """

    def __init__(self, parent, dc_file, dir_struct_paths, build_format, subdeliverables):
        self.title = None
        self.dc_hash = None
        self.path = None
        self.status = "building"
        self.successful_build_commit = None
        self.last_build_attempt_commit = None
        self.root_id = None  # False if no root id exists
        self.cleanup_done = False

        self.tmp_dir_bi, self.docset_relative_path = dir_struct_paths
        self.parent = parent  # Reference to the parent BuildInstructionHandler
        self.dc_file = dc_file
        self.build_format = build_format
        self.subdeliverables = subdeliverables
        self.id = self.generate_id()
        self.prev_state()
        logger.debug("Queued deliverable %s -- %s of %s:%s/%s/%s/%s for BI %s",
                     self.id,
                     self.build_format,
                     self.parent.build_instruction['target'],
                     self.parent.build_instruction['lang'],
                     self.parent.build_instruction['docset'],
                     self.parent.build_instruction['product'],
                     self.dc_file,
                     self.parent.build_instruction['id']
                     )

    def prev_state(self):
        """
        Get previous commit hashes.
        """
        if self.id in self.parent.deliverables.keys():
            self.successful_build_commit = self.parent.deliverables[
                self.id]['successful_build_commit']
            self.last_build_attempt_commit = self.parent.deliverables[
                self.id]['last_build_attempt_commit']

    def dict(self):
        value = {
            'build_format': self.build_format,
            'dc': self.dc_file,
            'status': self.status,
            'title': self.title,
            'path': self.path,
            'successful_build_commit': self.successful_build_commit,
            'last_build_attempt_commit': self.last_build_attempt_commit,
            'subdeliverables': self.subdeliverables,
        }
        return value

    def generate_id(self):
        """
        Generate an ID (hash) from a unique tuple of parameters.
        """
        return hashlib.md5((self.parent.build_instruction['target'] +
                            self.parent.build_instruction['docset'] +
                            self.parent.build_instruction['lang'] +
                            self.parent.build_instruction['product'] +
                            self.dc_file +
                            self.build_format).encode('utf-8')
                           ).hexdigest()[:9]

    def run(self, thread_id):
        """
        Create a dict of commands that build the document.
        """
        with self.parent.deliverables_open_lock:
            self.parent.deliverables[self.id]['last_build_attempt_commit'] = self.parent.build_instruction['commit']
        logger.info("Building deliverable %s (%s, %s) for BI %s. Commit: %s",
                    self.id,
                    self.dc_file,
                    self.build_format,
                    self.parent.build_instruction['id'],
                    self.parent.deliverables[self.id]['last_build_attempt_commit'],
                    )
        #
        # The following lines of code define all bash commands that
        # are required to build and publish the deliverable.
        # This includes preparation of the target directories and
        # clean up after the build is finished.
        #
        commands = {}

        # Write XSLT parameters to temp file
        n = 0
        xslt_params_file = tempfile.mkstemp(prefix="docserv_xslt_", text=True)
        xslt_params = ""
        commands[n] = {}
        commands[n]['cmd'] = "echo \"%s\" > %s" % (xslt_params,
                                                   xslt_params_file[1])

        # Write daps parameters to temp file
        n += 1
        daps_params_file = tempfile.mkstemp(prefix="docserv_daps_", text=True)
        remarks = self.parent.config['targets'][self.parent.build_instruction['target']]['remarks']
        draft = self.parent.config['targets'][self.parent.build_instruction['target']]['draft']
        meta = self.parent.config['targets'][self.parent.build_instruction['target']]['meta']
        daps_params = " ".join([
            "--remarks" if (remarks == "true" or remarks == "1") else "",
            "--draft" if (draft ==
                          "true" or draft == "1") else "",
            "--meta" if (meta ==
                         "true" or meta == "1") else ""
        ])
        commands[n] = {}
        commands[n]['cmd'] = "echo \"%s\" > %s" % (daps_params,
                                                   daps_params_file[1])

        # Run daps in the docker container, copy results to a
        # build target directory
        n += 1
        tmp_dir_docker = tempfile.mkdtemp(prefix="docserv_out_")
        commands[n] = {}
        commands[n]['cmd'] = "d2d_runner --create-bigfile=1 --auto-validate=1 --container-update=1 --xslt-param-file=%s --daps-param-file=%s --out=%s --in=%s --formats=%s %s" % (
            xslt_params_file[1],
            daps_params_file[1],
            tmp_dir_docker,
            self.parent.build_source_dir,
            self.build_format,
            self.dc_file
        )

        # Create correct directory structure
        self.deliverable_relative_path = os.path.join(
            self.docset_relative_path,
            self.build_format
        )
        if self.build_format in ['html', 'single-html']:
            self.deliverable_relative_path = os.path.join(
                self.deliverable_relative_path,
                self.dc_file.replace('DC-', '')
            )
        tmp_build_full_path = os.path.join(
            self.tmp_dir_bi,
            self.deliverable_relative_path
        )
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "/usr/bin/mkdir -p %s" % (tmp_build_full_path)

        # Copy wanted files to temp build instruction directory
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "rsync -lr __FILELIST__  %s" % (tmp_build_full_path)
        commands[n]['pre_cmd_hook'] = 'parse_d2d_filelist'
        commands[n]['tmp_dir_docker'] = tmp_dir_docker

        # create directory for Deliverable cache file
        self.deliverable_cache_dir = os.path.join(
            self.parent.deliverable_cache_base_dir,
            self.parent.build_instruction['target'],
            self.docset_relative_path,
            self.build_format,
        )
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "mkdir -p %s" % self.deliverable_cache_dir
        commands[n]['tmp_dir_docker'] = tmp_dir_docker
        # get root id from bigfile
        commands[n]['pre_cmd_hook'] = 'extract_root_id'
        # write configuration for overview page
        commands[n]['post_cmd_hook'] = 'write_deliverable_cache'

        # remove daps parameter file
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "rm %s" % (daps_params_file[1])

        # remove xslt parameter file
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "rm %s" % (xslt_params_file[1])

        # remove docker output directory
        n += 1
        commands[n] = {}
        commands[n]['cmd'] = "rm -rf %s" % (tmp_dir_docker)

        #
        # Now iterate through all commands and execute them
        #
        self.iterate_commands(commands, n, thread_id)

    def iterate_commands(self, commands, n, thread_id):
        """
        Iterate through a dict containing commands. Also execute
        post and pre execution hooks.
        """
        for i in range(0, n + 1):
            if 'pre_cmd_hook' in commands[i]:
                commands[i] = getattr(self, commands[i]['pre_cmd_hook'])(
                    commands[i], thread_id)
                if commands[i] == False:
                    return self.finish(False)

            result = self.execute(commands[i], thread_id)
            if not result:  # abort if one command failed
                return self.finish(False)

            if 'post_cmd_hook' in commands[i]:
                if not getattr(self, commands[i]['post_cmd_hook'])(commands[i], thread_id):
                    return self.finish(False)

        return self.finish(result)

    def execute(self, command, thread_id):
        """
        Execute single commands and check return value.
        """
        cmd = shlex.split(command['cmd'])
        logger.debug("Thread %i: %s" % (thread_id, command))
        s = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        self.out, self.err = s.communicate()

        if int(s.returncode) != 0:
            self.failed_command = command['cmd']
            logger.warning("Thread %i: Build failed! Unexpected return value %i for '%s'",
                           thread_id, s.returncode, command['cmd'])
            logger.warning("Thread %i STDOUT: %s", thread_id,
                           self.out.decode('utf-8'))
            logger.warning("Thread %i STDERR: %s", thread_id,
                           self.err.decode('utf-8'))
            self.mail()
            return False
        return True

    def finish(self, result):
        """
        Clean up when deliverable is finished, independent of success.
        """
        with self.parent.deliverables_open_lock:
            if result:
                self.parent.deliverables[self.id]['status'] = "success"
            else:
                self.parent.deliverables[self.id]['status'] = "fail"
        with self.parent.deliverables_building_lock:
            self.parent.deliverables_building.remove(self.id)
        if result:
            with self.parent.deliverables_open_lock:
                self.parent.deliverables[self.id]['successful_build_commit'] = self.parent.build_instruction['commit']
        return result

    def mail(self):
        """
        Mail for failed builds.
        """
        msg = """Sorry. docserv² failed to build deliverable:
Repo/Branch: %s %s
DC-File: %s %s
Format: %s
Language: %s

=== Deliverable ===
%s

=== Build instruction ===
%s

=== Failed command ===
%s

=== STDOUT ===
%s

=== STDERR ===
%s
""" % (
            self.parent.remote_repo,
            self.parent.branch,
            self.parent.build_source_dir,
            self.dc_file,
            self.build_format,
            self.parent.build_instruction['lang'],
            self.dict(),
            self.parent.build_instruction,
            self.failed_command,
            self.out.decode('utf-8'),
            self.err.decode('utf-8'),
        )
        to = ', '.join(self.parent.maintainers)
        subject = "[docserv²] Failed building %s for %s " % (
            self.build_format, self.dc_file)
        mail(msg, subject, to)

    def parse_d2d_filelist(self, command, thread_id):
        """
        Parse the returned filelist from daps2docker. This file contains
        a list of built documents.
        """
        # currently only read from file logic
        f = open(os.path.join(command['tmp_dir_docker'], 'filelist'), 'r')
        for line in f:
            line = line.strip()
            if '_bigfile.xml' not in line and line != "":
                self.d2d_out_dir = line
                self.path = os.path.join(self.deliverable_relative_path,
                                        line.split('/')[-1])
        logger.debug("Deliverable build results: %s", self.d2d_out_dir)
        command['cmd'] = command['cmd'].replace(
            '__FILELIST__', self.d2d_out_dir)
        return command

    def extract_root_id(self, command, thread_id):
        """
        Extract the ROOT ID from the DC file. Then extract the title
        from the DocBook XML big file. If ROOT IDs for subdeliverables
        are defined, extract titles for them as well.
        """
        # extract root id from DC file and then title from bigfile
        dc_path = os.path.join(self.parent.build_source_dir, self.dc_file)
        with open(dc_path) as f:
            import re
            for line in f:
                #pylint: disable=W1401
                m = re.search(
                    '^\s*ROOTID\s*=\s*[\"\']?([^\"\']+)[\"\']?.*', line.strip())
                if m:
                    self.root_id = m.group(1)
                    break
        xmlstarlet = {}
        xmlstarlet['ret_val'] = 0
        dchash = {}
        dchash['ret_val'] = 0
        if self.root_id:
            bigfile = self.root_id
            logger.debug("Found ROOTID for %s: %s", self.id, self.root_id)
            bigfile_path = (os.path.join(
                command['tmp_dir_docker'], '.tmp', '%s_bigfile.xml' % bigfile))
            xpath = ("(//*[@*[local-name(.)='id']='{ID}']/*[contains(local-name(.),'info')]/*[local-name(.)='title']|"
                     "//*[@*[local-name(.)='id']='{ID}']/*[local-name(.)='title'])[1]"
                     ).format(ID=self.root_id)
            xmlstarlet['cmd'] = "xmlstarlet sel -t -v \"%s\" %s" % (
                xpath, bigfile_path)
        else:
            bigfile = self.dc_file.replace('DC-', '')
            logger.debug(
                "No ROOTID found for %s, using DC file name: %s", self.id, self.dc_file)
            bigfile_path = (os.path.join(
                command['tmp_dir_docker'], '.tmp', '%s_bigfile.xml' % bigfile))
            xpath = "(/*/*[contains(local-name(.),'info')]/*[local-name(.)='title']|/*/*[local-name(.)='title'])[1]"
            xmlstarlet['cmd'] = "xmlstarlet sel -t -v \"%s\" %s" % (
                xpath, bigfile_path)
        result = self.execute(xmlstarlet, thread_id)
        if not result:
            return False
        self.title = self.out.decode('utf-8')
        dchash['cmd'] = "%s %s" % (os.path.join(BIN_DIR, 'docserv-dchash'), dc_path)
        result = self.execute(dchash, thread_id)
        if not result:
            return False
        self.dc_hash = self.out.decode('utf-8')
        self.subdeliverable_titles = {}
        self.subdeliverable_hashes = {}
        for subdeliverable in self.subdeliverables:
            xpath = "(//*[@*[local-name(.)='id']='%s']/*[contains(local-name(.),'info')]/*[local-name(.)='title']|//*[@*[local-name(.)='id']='%s']/*[local-name(.)='title'])[1]" % (
                subdeliverable, subdeliverable)
            xmlstarlet['cmd'] = "xmlstarlet sel -t -v \"%s\" %s" % (
                xpath, bigfile_path)
            xmlstarlet['ret_val'] = 0
            result = self.execute(xmlstarlet, thread_id)
            if not result:
                return False
            self.subdeliverable_titles[subdeliverable] = self.out.decode(
                'utf-8')
            dchash['ret_val'] = 0
            dchash['cmd'] = "%s %s %s" % (os.path.join(BIN_DIR, 'docserv-dchash'), dc_path, subdeliverable)
            result = self.execute(dchash, thread_id)
            if not result:
                return False
            self.subdeliverable_hashes[subdeliverable] = self.out.decode('utf-8')
        with self.parent.deliverables_open_lock:
            self.parent.deliverables[self.id]['title'] = self.title
            self.parent.deliverables[self.id]['path'] = self.path
        return command

    def write_deliverable_cache(self, command, thread_id):
        """
        Create an XML file that contains the deliverable information
        including path and title. This is required for the
        'docserv-build-navigation' command.
        """
        root = cElementTree.Element("document",
                                    lang=self.parent.build_instruction['lang'],
                                    productid=self.parent.build_instruction['product'],
                                    setid=self.parent.build_instruction['docset'],
                                    dc=self.dc_file,
                                    cachedate=str(time.time()))
        cElementTree.SubElement(
            root, "commit").text = self.parent.deliverables[self.id]['last_build_attempt_commit']
        cElementTree.SubElement(
            root, "path", format=self.build_format).text = self.path

        # If there are subdeliverables, we are probably in a set and we don't
        # really need to bother linking to the set page.
        if not self.subdeliverables:
            if self.root_id is not None:
                root_id = self.root_id
            else:
                root_id = ""
            cElementTree.SubElement(
                root, "title", rootid=root_id, hash=self.dc_hash).text = self.title

        for subdeliverable in self.subdeliverables:
            cElementTree.SubElement(
                root, "title", rootid=subdeliverable,
                hash=self.subdeliverable_hashes[subdeliverable]).text = self.subdeliverable_titles[subdeliverable]
        tree = cElementTree.ElementTree(root)
        tree.write(os.path.join(
            self.deliverable_cache_dir, "%s.xml" % self.dc_file))
        return command
