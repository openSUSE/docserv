from datetime import datetime
import hashlib
import json
import logging
from logging.config import fileConfig
import multiprocessing
import os
import queue


import sys
import threading
import tempfile
import time
from configparser import ConfigParser as configparser

from jinja2 import TemplateNotFound

from .common import BIN_DIR, CACHE_DIR, CONF_DIR, DOCSERV_CODE_DIR, SHARE_DIR, PROJECT_DIR
from .bih import BuildInstructionHandler
from .deliverable import Deliverable
from .functions import print_help
from .rest import RESTServer, ThreadedRESTServer
from .navigation import init_jinja_template
from .util import run, replace_placeholders


logger = logging.getLogger(__name__)

class DocservState:
    config = {}

    ###################################################
    #   The following section contains all dicts and  #
    #   queues that keep track of stuff to be built   #
    ###################################################
    #
    # 1. "queue" for build instructions from REST API
    #
    scheduled_build_instruction = {}
    scheduled_build_instruction_lock = threading.Lock()

    #
    # 2. When an item form the scheduled_build_instruction dict
    #    is taken up for processing, its information needs
    #    to be updated from the configuration. During that phase
    #    it remains in the scheduled_build_instructions dict but
    #    its key is added to the updating_build_instruction list.
    #    This also uses the scheduled_build_instruction_lock.
    updating_build_instruction = []

    #
    # 3.1 A dict that contains all BuildInstructionHandlers.
    #     This is the state in which documents are being
    #     build.
    #
    bih_dict = {}
    bih_dict_lock = threading.Lock()

    #
    # 3.2 A queue that contains BUILD_INSTRUCTION_ID. With the ID
    #     the workers will retrieve a Deliverable and build it.
    #
    bih_queue = queue.Queue()

    #
    # 4. When a BuildInstructionHandler is finished, its
    #    status is dumped into a dict and kept for the future.
    #
    past_builds = {}
    past_builds_lock = threading.Lock()

    # Access to git repositories must be controlled.
    # gitLocks is a dict of repoLock instances.
    gitLocks = {}
    gitLocksLock = threading.Lock()

    def __str__(self):
        return json.dumps(self.dict())

    def __repr__(self):
        return self.dict()

    def dict(self):
        """
        Create a list of all build instructions, queued, current and past.
        This is usually used to return the status on the REST API.
        """
        retval = []
        with self.scheduled_build_instruction_lock:
            for key in self.scheduled_build_instruction:
                try:
                    retval.append(self.scheduled_build_instruction[key])
                except AttributeError:
                    pass
        with self.bih_dict_lock:
            for key in self.bih_dict:
                try:
                    retval.append(self.bih_dict[key].dict())
                except AttributeError:
                    pass
        for key in self.past_builds:
            retval.append(self.past_builds[key])
        return retval

    def generate_id(self, build_instruction):
        """
        Generate a unique ID for a build instruction by hashing
        its values.
        """
        return hashlib.md5((build_instruction['target'] +
                            build_instruction['docset'] +
                            build_instruction['lang'] +
                            build_instruction['product']).encode('utf-8')
                           ).hexdigest()[:9]

    def queue_build_instruction(self, build_instruction):
        """
        Puts newly arrived build instructions in a dict that queues
        build instructions.
        """
        retval = False
        build_instruction['id'] = self.generate_id(build_instruction)
        if build_instruction['id'] in self.past_builds.keys():
            with self.past_builds_lock:
                build_instruction = self.past_builds.pop(
                    build_instruction['id'])
        with self.bih_dict_lock:
            if build_instruction['id'] not in self.bih_dict:
                with self.scheduled_build_instruction_lock:
                    if build_instruction['id'] not in self.scheduled_build_instruction:
                        self.scheduled_build_instruction[build_instruction['id']
                                                         ] = build_instruction
                        retval = True
        return retval

    def get_scheduled_build_instruction(self):
        """
        Get a build instruction that has been queued after input on
        the REST API.
        """
        with self.scheduled_build_instruction_lock:
            for key in self.scheduled_build_instruction:
                if key not in self.updating_build_instruction:
                    self.updating_build_instruction.append(key)
                    return self.scheduled_build_instruction[key]
        return None

    def remove_scheduled_build_instruction(self, build_instruction_id):
        """
        Remove a build instruction from the queued dictionary. This
        usually means that a BuildInstructionHandler was created and
        documents are being built.
        """
        with self.scheduled_build_instruction_lock:
            self.updating_build_instruction.remove(build_instruction_id)
            self.scheduled_build_instruction.pop(build_instruction_id)

    def abort_build_instruction(self, build_instruction_id):
        """
        If the initialization of the BuildInstructionHandler fails,
        move the build instruction to the past_builds dict and remove
        it from the queued build instructions.
        """
        logger.info("Aborting build instruction %s", build_instruction_id)
        with self.scheduled_build_instruction_lock:
            self.updating_build_instruction.remove(build_instruction_id)
            build_instruction = self.scheduled_build_instruction.pop(
                build_instruction_id, None)
        if build_instruction is None:
            with self.bih_dict_lock:
                build_instruction = self.bih_dict.pop(
                    build_instruction_id).dict()
        if build_instruction is not None:
            with self.past_builds_lock:
                self.past_builds[build_instruction_id] = build_instruction

    def finish_build_instruction(self, build_instruction_id):
        """
        After all deliverables are finished, dump a dict of the
        BuildInstructionHandler into the past_builds dict.
        """
        logger.info("Finished build instruction %s", build_instruction_id)
        self.bih_dict[build_instruction_id].cleanup()
        with self.bih_dict_lock:
            build_instruction = self.bih_dict.pop(build_instruction_id)
        with self.past_builds_lock:
            self.past_builds[build_instruction_id] = build_instruction.dict()

    def get_deliverable(self, thread_id):
        """
        Get an ID from the bih_queue (currently building BIHs). With that
        get a deliverable from the BIH itself. If no more deliverables are
        available, the BIH is finished.
        """
        try:
            build_instruction_id = self.bih_queue.get(False)
        except queue.Empty:
            return None
        else:
            deliverable = self.bih_dict[build_instruction_id].get_deliverable()
            if deliverable == 'done':
                self.finish_build_instruction(build_instruction_id)
                deliverable = None
            else:  # build instruction is not yet finished, put its ID back on the queue
                self.bih_queue.put(build_instruction_id)
        return deliverable

    def save_state(self):
        """
        Save status to JSON file.
        The JSON file usually resides in /var/cache/docserv/[SERVER_NAME].json
        """
        f = open(os.path.join(CACHE_DIR, self.config['server']['name'] + '.json'), "w")
        f.write(json.dumps(self.dict()))

    def load_state(self):
        """
        Load status from JSON file.
        The JSON file usually resides in /var/cache/docserv/[SERVER_NAME].json
        """
        filepath = os.path.join(CACHE_DIR, self.config['server']['name'] + '.json')
        if os.path.isfile(filepath):
            file = open(filepath, "r")
            try:
                state = json.loads(file.read())
            except json.decoder.JSONDecodeError:
                return False
            for build_instruction in state:
                if ('building' in build_instruction and len(build_instruction['building']) > 0) or ('open' in build_instruction and len(build_instruction['open']) > 0):
                    self.queue_build_instruction(build_instruction)
                else:
                    self.past_builds[build_instruction['id']
                                     ] = build_instruction
            logger.info("Read previous state %s", filepath)
            return True
        return False

    def parse_build_instruction(self, thread_id):
        build_instruction = self.get_scheduled_build_instruction()
        # logger.debug("parse_build_instruction: tmp_dir=%s", self.stitch_tmp_dir)
        if build_instruction is not None:
            myBIH = BuildInstructionHandler(
                build_instruction,
                self.config,
                self.stitch_tmp_dir, self.gitLocks, self.gitLocksLock, thread_id)
            # If the initialization failed, immediately delete the BuildInstructionHandler
            if myBIH.initialized == False:
                self.abort_build_instruction(build_instruction['id'])
                return
            if myBIH.build_docs:
                myBIH.generate_deliverables()
            self.remove_scheduled_build_instruction(build_instruction['id'])
            with self.bih_dict_lock:
                self.bih_dict[build_instruction['id']] = myBIH
            self.bih_queue.put(build_instruction['id'])


class DocservConfig:
    """
    Class for handling the .ini configuration file.
    """

    def parse_config(self, argv):
        """Parsing Docserv config file"""
        logger.debug("Parsing Docserv file")
        #def join_conf_dir(path):
        #    # Turn relative paths to absolute paths, depending on the
        #    # location of the INI (or rather CONF_DIR which by its definition
        #    # is the location of the INI).
        #    return path if os.path.isabs(path) else os.path.join(CONF_DIR, path)

        config = configparser()
        if len(argv) == 1:
            self.config_file = "my-site"
        else:
            self.config_file = argv[1]

        self.config_path=os.path.join(CONF_DIR, self.config_file + '.ini')
        logger.info("Reading Docserv INI %r...", self.config_path)
        config.read(self.config_path)
        self.config = {}
        try:
            self.config['server'] = {}
            servername = self.config['server']['name'] = self.config_file
            self.config['server']['loglevel'] = int(
                config['server']['loglevel'])
            self.config['server']['host'] = config['server']['host']
            self.config['server']['port'] = int(config['server']['port'])
            self.config['server']['enable_mail'] = config['server']['enable_mail']
            self.config['server']['repo_dir'] = replace_placeholders(
                config['server']['repo_dir'],
                "",
                servername)
            self.config['server']['temp_repo_dir'] = replace_placeholders(
                config['server']['temp_repo_dir'],
                "",
                servername)
            self.config['server']['valid_languages'] = config['server']['valid_languages']
            if config['server']['max_threads'] == 'max':
                self.config['server']['max_threads'] = multiprocessing.cpu_count()
            else:
                self.config['server']['max_threads'] = int(config['server']['max_threads'])
            self.config['targets'] = {}

            for section in config.sections():
                if not str(section).startswith("target_"):
                    continue

                sec = config[section]
                secname = sec['name']
                logger.debug("Found target=%s", secname)

                self.config['targets'][secname] = {}
                self.config['targets'][secname]['name'] = sec
                self.config['targets'][secname]['template_dir'] = replace_placeholders(
                    sec['template_dir'],
                    secname,
                    servername)
                # Jinja directories
                jinja_context_dir = replace_placeholders(
                    sec['jinja_context_dir'],
                    secname,
                    servername)
                self.config['targets'][secname]['jinja_context_dir'] = jinja_context_dir
                jinja_template_dir = replace_placeholders(
                    sec['jinja_template_dir'],
                    secname,
                    servername)
                self.config['targets'][secname]['jinja_template_dir'] = jinja_template_dir
                logger.debug("  For target=%s using jinja_template_dir=%s", secname, jinja_template_dir)

                self.config['targets'][secname]['jinja_env'] = init_jinja_template(
                    self.config['targets'][secname]['jinja_template_dir']
                )
                self.config['targets'][secname]['jinjacontext_home'] = replace_placeholders(
                    sec['jinjacontext_home'],
                    secname,
                    servername)
                # Jinja Templates
                self.config['targets'][secname]['jinja_template_home'] = replace_placeholders(
                    sec['jinja_template_home'],
                    secname,
                    servername)
                self.config['targets'][secname]['jinja_template_index'] = sec['jinja_template_index']
                self.config['targets'][secname]['jinja_template_trd'] = sec['jinja_template_trd']
                #
                self.config['targets'][secname]['active'] = sec['active']
                self.config['targets'][secname]['draft'] = sec['draft']
                self.config['targets'][secname]['remarks'] = sec['remarks']
                self.config['targets'][secname]['meta'] = sec['meta']
                self.config['targets'][secname]['default_xslt_params'] = replace_placeholders(
                    sec['default_xslt_params'],
                    secname,
                    servername)
                self.config['targets'][secname]['enable_target_sync'] = sec['enable_target_sync']
                if sec['enable_target_sync'] == 'yes':
                    self.config['targets'][secname]['target_path'] = sec['target_path']
                self.config['targets'][secname]['backup_path'] = replace_placeholders(
                    sec['backup_path'],
                    secname,
                    servername)
                config_dir = replace_placeholders(
                    sec['config_dir'],
                    secname,
                    servername)
                self.config['targets'][secname]['config_dir'] = config_dir
                logger.debug("  For target=%s using config_dir=%s", secname, config_dir)
                self.config['targets'][secname]['languages'] = sec['languages']
                self.config['targets'][secname]['default_lang'] = sec['default_lang']
                self.config['targets'][secname]['omit_default_lang_path'] = sec['omit_default_lang_path']
                self.config['targets'][secname]['internal'] = sec['internal']
                self.config['targets'][secname]['zip_formats'] = sec['zip_formats']
                self.config['targets'][secname]['server_base_path'] = sec['server_base_path']
                self.config['targets'][secname]['canonical_url_domain'] = sec['canonical_url_domain']
                srfiles = replace_placeholders(
                    sec['server_root_files'],
                    secname,
                    servername)
                self.config['targets'][secname]['server_root_files'] = srfiles
                logger.debug("  For target=%s using server-root-files=%s", secname, srfiles)


                self.config['targets'][secname]['enable_ssi_fragments'] = sec['enable_ssi_fragments']
                if sec['enable_ssi_fragments'] == 'yes':
                    self.config['targets'][secname]['fragment_dir'] = replace_placeholders(
                        sec['fragment_dir'],
                        secname,
                        servername)
                    self.config['targets'][secname]['fragment_l10n_dir'] = replace_placeholders(
                        sec['fragment_l10n_dir'],
                        secname,
                        servername)
                # FIXME: I guess this is not the prettiest way to handle
                # optional values (but it works for now)
                self.config['targets'][secname]['build_container'] = False
                if 'build_container' in list(sec.keys()):
                    self.config['targets'][secname]['build_container'] = sec['build_container']

                self.config['targets'][secname]['site_sections'] = sec['site_sections']
                self.config['targets'][secname]['default_site_section'] = sec['default_site_section']

        except KeyError as error:
            logger.warning(
                "Invalid configuration file, missing configuration key %s. Exiting.", error)
            sys.exit(1)

        logger.debug("Successfully finished processing Docserv INI")


class Docserv(DocservState, DocservConfig):
    """
    This class creates worker threads and starts the REST API.
    """
    end_all = queue.Queue()

    def __init__(self, argv):
        self.parse_config(argv)
        LOGLEVELS = {0: logging.WARNING,
                     1: logging.INFO,
                     2: logging.DEBUG,
                     }
        logger.setLevel(LOGLEVELS[self.config['server']['loglevel']])
        self.load_state()

    def start(self):
        """
        Create worker and REST API threads.
        """

        if self.config['server']['max_threads'] > multiprocessing.cpu_count():
            self.config['server']['max_threads'] = multiprocessing.cpu_count()
            logger.info("Reducing number of build threads to avoid using more threads than there are cores.")

        logger.info("Will use %i build threads.", self.config['server']['max_threads'])

        try:
            # After starting docserv, make sure to stitch as the first thing,
            # this increases startup time but means that as long as the config
            # does not change, we don't have to do another complete validation
            # self.stitch_tmp_dir = tempfile.mkdtemp(prefix='docserv_stitch_')
            current_date = datetime.now().strftime('%Y-%m-%d')
            self.stitch_tmp_dir = f"/tmp/docserv_stitch_{current_date}"
            os.makedirs(self.stitch_tmp_dir, exist_ok=True)

            # Notably, the config dir can be different for different targets.
            # So, stitch for each.
            for target in self.config['targets']:
                stitch_tmp_file = os.path.join(self.stitch_tmp_dir,
                    ('productconfig_simplified_%s.xml' % target))
                # Largely copypasta from bih.py cuz I dunno how to share stuff
                logger.debug("Stitching XML config directory to %s",
                             stitch_tmp_file)
                # Don't use --revalidate-only parameter: after starting we
                # really want to make sure that the config is alright.
                cmd = ('%s --simplify '
                       '--valid-languages="%s" '
                       '--valid-site-sections="%s" '
                       '%s %s') % (
                    os.path.join(BIN_DIR, 'docserv-stitch'),
                    self.config['server']['valid_languages'],
                    self.config['targets'][target]['site_sections'],
                    self.config["targets"][target]['config_dir'],
                    stitch_tmp_file)
                logger.debug("Stitching command: %s", cmd)
                rc, self.out, self.err = run(cmd)
                if rc == 0:
                    logger.debug("Stitching of %s successful",
                                 self.config['targets'][target]['config_dir'])
                else:
                    logger.warning("Stitching of %s failed!",
                                   self.config['targets'][target]['config_dir'])
                    logger.warning("Stitching STDOUT: %s", self.out.decode('utf-8'))
                    logger.warning("Stitching STDERR: %s", self.err.decode('utf-8'))
                # End copypasta

            thread_receive = threading.Thread(target=self.listen)
            thread_receive.start()
            workers = []
            for i in range(0, min([os.cpu_count(), self.config['server']['max_threads']])):
                logger.info("Starting build thread %i", i)
                worker = threading.Thread(target=self.worker,
                                          name=f"worker-{i}",
                                          args=(i,))
                worker.start()
                workers.append(worker)
            # to have a clean shutdown, wait for all threads to finish
            thread_receive.join()
        except KeyboardInterrupt:
            self.exit()
        for worker in workers:
            worker.join()
        self.rest.shutdown()
        self.save_state()

    def exit(self):
        logger.warning(
            "Received SIGINT. Telling all threads to end. Please wait.")
        self.end_all.put("now")

    def worker(self, thread_id):
        while(True):
            # 1. parse input from rest api and put the instance of the doc class on the currently building queue
            self.parse_build_instruction(thread_id)

            # 2. get doc from currently_building queue and then a deliverable from doc.
            #    after that, put doc back on the currently building queue. unless it was
            #    the last deliverable.
            deliverable = self.get_deliverable(thread_id)
            if deliverable is not None:
                deliverable.run(thread_id)

            # 3. end thread if sigint
            if not self.end_all.empty():
                return True

            # 4. wait for a short while, then repeat
            time.sleep(0.1)

            # Thread 0 is frequently saving the state
            if thread_id == 0:
                self.save_state()

    def listen(self):
        server_address = (self.config['server']['host'], int(
            self.config['server']['port']))
        self.rest = ThreadedRESTServer(server_address, RESTServer, self)
        self.rest.serve_forever()
        return True


def read_logging(inifile: str):
    "Read log INI file"
    fileConfig(inifile, disable_existing_loggers=True)


def main():
    """Entry point for Docserv"""
    if "--help" in sys.argv or "-h" in sys.argv:
        print_help()
        return 1

    # First read/configure default logger
    # If the user provides a different logging config, it will
    # overwrite the default logger config
    read_logging(os.path.join(DOCSERV_CODE_DIR, "logging.ini"))

    # Try to extract the user logger config file (INI format)
    loginifile = sys.argv[2:]
    loginifile = None if not loginifile else loginifile[0]

    if loginifile:
        try:
            read_logging(loginifile)
            sys.argv.pop()

        except FileNotFoundError as err:
            # Used for Python >=3.12, we raise it again
            raise

        except KeyError:
            # For Python <3.12, only KeyError is raised with
            # KeyError: 'formatters'.
            # Ignore the error and provide the correct message
            raise FileNotFoundError(f"Could not find {loginifile}.")

    logger.info("Starting Docserv...")
    try:
        docserv = Docserv(sys.argv)
        docserv.start()
    except FileNotFoundError as err:
        logger.exception("Some resource couldn't be find %s", err)
        return 100
    except TemplateNotFound as err:
        logger.exception("Jinja template error %s", err)
        return 200
    except KeyboardInterrupt:
        logger.info("Docserv interrupted by user.")
        # docserv.exit()

    return 0


# sys.exit(main())
