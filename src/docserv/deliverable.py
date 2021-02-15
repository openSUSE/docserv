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

    def __init__(self, parent, dc_file, dir_struct_paths, build_format, subdeliverables, xslt_params):
        self.title = None
        self.dc_hash = None
        self.path = None
        self.status = "building"
        self.successful_build_commit = None
        self.last_build_attempt_commit = None
        self.root_id = None  # False if no root id exists
        self.pdf_name = None # False if no PDFNAME value exists in DC file
        self.cleanup_done = False

        self.tmp_dir_bi, self.docset_relative_path = dir_struct_paths
        self.parent = parent  # Reference to the parent BuildInstructionHandler
        self.dc_file = dc_file
        self.build_format = build_format
        self.subdeliverables = subdeliverables
        self.xslt_params = xslt_params
        self.id = self.generate_id()
        self.prev_state()
        self.target_config = self.parent.config['targets'][self.parent.build_instruction['target']]
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
        os.close(xslt_params_file[0])
        default_xslt_params = self.parent.config['targets'][self.parent.build_instruction['target']]['default_xslt_params']
        xslt_params = ""
        if len(self.xslt_params) > 0:
            xslt_params = "\n".join(self.xslt_params)
        # The EPUB stylesheets might support this one too, but we don't want it
        # in there, so make sure to run this only for HTML & single-HTML.
        if self.build_format in ['html', 'single-html']:
            canonical_prefix = "%s%s" % (   self.target_config['canonical_url_domain'],
                                            self.target_config['server_base_path'])
            # We intentionally do not use os.path.join here, because Web
            # addresses always use forward slashes
            canonical_path = "%s%s%s" %(canonical_prefix,
                "%s/" % self.parent.build_instruction['lang'] if (
                            self.target_config['omit_default_lang_path'] != "yes" or
                            self.parent.build_instruction['lang'] != self.target_config['default_lang']) else "",
                '/'.join([
                self.parent.build_instruction['product'],
                self.parent.build_instruction['docset'],
                self.build_format,
                self.dc_file.replace('DC-', '')])
            )
            xslt_params += "\ncanonical-url-base=%s" % (canonical_path)
        # Special default value to prevent odd errors
        if xslt_params == "":
            xslt_params = "--"
        commands[n] = {}
        commands[n]['cmd'] = "docserv-write-param-file %s \"%s\" %s" % (xslt_params_file[1], xslt_params, default_xslt_params)

        # Write daps parameters to temp file
        n += 1
        daps_params_file = tempfile.mkstemp(prefix="docserv_daps_", text=True)
        os.close(daps_params_file[0])
        remarks = self.parent.config['targets'][self.parent.build_instruction['target']]['remarks']
        draft = self.parent.config['targets'][self.parent.build_instruction['target']]['draft']
        meta = self.parent.config['targets'][self.parent.build_instruction['target']]['meta']
        daps_params = "\n".join([
            "--remarks" if remarks == "yes" else "",
            "--draft" if (draft == "yes" or
                          self.parent.lifecycle == "beta" or
                          self.parent.lifecycle == "unpublished") else "",
            "--meta" if meta == "yes" else ""
        ])
        commands[n] = {}
        commands[n]['cmd'] = "docserv-write-param-file %s \"%s\"" % (daps_params_file[1], daps_params)

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
        msg = """Cheerio!

Docserv² failed to build the following deliverable:

Product:        %s
Docset:         %s
Language:       %s
Target Server:  %s

Repository:     %s
Branch:         %s
Commit:         %s

DC File:        %s
Format:         %s


These are the details:

=== Failed Command ===

%s


=== stdout ===

%s


=== stderr ===

%s
""" % (
            self.parent.build_instruction['product'],
            self.parent.build_instruction['docset'],
            self.parent.build_instruction['lang'],
            self.parent.build_instruction['target'],
            self.parent.remote_repo,
            self.parent.branch,
            self.parent.build_instruction['commit'],
            self.dc_file,
            self.build_format,
            self.failed_command,
            self.out.decode('utf-8'),
            self.err.decode('utf-8'),
        )
        to = ', '.join(self.parent.maintainers)
        subject = "[docserv²] Failed to build %s (%s, %s/%s, %s)" % (
            self.dc_file,
            self.build_format,
            self.parent.build_instruction['product'],
            self.parent.build_instruction['docset'],
            self.parent.build_instruction['lang'])
        mail(msg, subject, to)

    def parse_d2d_filelist(self, command, thread_id):
        """
        Parse the returned filelist from daps2docker. This file contains
        a list of built documents.
        """
        # currently only read from file logic
        try:
            f = open(os.path.join(command['tmp_dir_docker'], 'filelist'), 'r')
            for line in f:
                line = line.strip()
                if '_bigfile.xml' not in line and line != "":
                    self.d2d_out_dir = line
                    # If you build HTML, you get back a directory, d2d puts a /
                    # at the end of the path in all cases (apparently)
                    #   /path/to/directory/html/suse-openstack-cloud-all/
                    # Running .split[-1] over that line gets you an empty string
                    # and that is expected -- only for PDFs/EPUBs do we want to
                    # keep the last part of the URL here.
                    self.path = os.path.join(self.deliverable_relative_path,
                                            line.split('/')[-1])
        except FileNotFoundError:
            return False
        # Under some circumstances, we get empty file lists. In which case it's
        # probably better to declare the build failed.
        try:
            logger.debug("Deliverable build results: %s", self.d2d_out_dir)
            command['cmd'] = command['cmd'].replace(
                '__FILELIST__', self.d2d_out_dir)
            return command
        except AttributeError:
            return False

    def extract_root_id(self, command, thread_id):
        """
        Extract the ROOT ID from the DC file. Then extract the title
        from the DocBook XML big file. If ROOT IDs for subdeliverables
        are defined, extract titles for them as well.
        """
        # extract root id from DC file and then title from bigfile

        # FIXME: It seems unnecessary to guess the bigfile's name from the DC
        # file itself -- daps2docker creates a filelist that already includes
        # the correct bigfile name, no guessing involved.
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
            # PDFNAME parameter trumps ROOTID and DC file name
            for line in f:
                #pylint: disable=W1401
                m = re.search(
                    '^\s*PDFNAME\s*=\s*[\"\']?([^\"\']+)[\"\']?.*', line.strip())
                if m:
                    self.pdf_name = m.group(1)
                    break
        xmlstarlet = {}
        xmlstarlet['ret_val'] = 0
        dchash = {}
        dchash['ret_val'] = 0

        bigfile = self.dc_file.replace('DC-', '')
        if self.pdf_name:
            logger.debug("Found PDFNAME for %s", self.id)
            bigfile = self.pdf_name
        elif self.root_id:
            bigfile = self.root_id
        bigfile_path = (os.path.join(
            command['tmp_dir_docker'], '.tmp', '%s_bigfile.xml' % bigfile))

        if self.root_id:
            logger.debug("Found ROOTID for %s: %s", self.id, self.root_id)
            xpath = ("(//*[@*[local-name(.)='id']='{ID}']/*[contains(local-name(.),'info')]/*[local-name(.)='title']|"
                     "//*[@*[local-name(.)='id']='{ID}']/*[local-name(.)='title'])[1]"
                     ).format(ID=self.root_id)
            xmlstarlet['cmd'] = "xmlstarlet sel -t -v \"%s\" %s" % (
                xpath, bigfile_path)
        else:
            logger.debug(
                "No ROOTID found for %s, using DC file name: %s", self.id, self.dc_file)
            xpath = "(/*/*[contains(local-name(.),'info')]/*[local-name(.)='title']|/*/*[local-name(.)='title'])[1]"
            xmlstarlet['cmd'] = "xmlstarlet sel -t -v \"%s\" %s" % (
                xpath, bigfile_path)
        result = self.execute(xmlstarlet, thread_id)
        if not result:
            return False
        self.title = self.out.decode('utf-8').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
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

        # If the product is unsupported, we don't copy the output files as
        # such, we only copy a zip archive of the output files, thus we don't
        # need to worry about the document titles
        if self.parent.lifecycle == "unsupported":
            return command

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
