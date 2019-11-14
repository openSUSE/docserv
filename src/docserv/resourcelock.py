import logging
import os
import threading

from docserv.functions import resource_to_filename

my_env = os.environ

logger = logging.getLogger('docserv')


class ResourceLock:
    """
    It is not safe to run multiple git commands on one repository
    at the same time. For example, running git pull in parallel
    in one repo breaks git. This can happen if build intructions
    for several languages are sent at the same time. Therefore
    we need to lock the usage of git repos down to only one thread
    at a time.
    """

    def __init__(self, repo_dir, thread_id, resource_locks,
      resource_lock_operation_lock):
        """
        repo_dir -- path to a repository
        thread_id -- ID of thread calling this method
        resource_locks -- dict of all existing resource locks
        resource_lock_operation_lock -- lock that allows only a single
            resource lock operation at once
        """
        self.resource_locks = resource_locks
        self.resource_lock_operation_lock = resource_lock_operation_lock
        self.resource_name = resource_to_filename(repo_dir)
        self.resource_lock_operation_lock.acquire()
        if self.resource_name not in resource_locks:
            self.resource_locks[self.resource_name] = threading.Lock()
        self.resource_lock_operation_lock.release()
        self.acquired = False
        self.thread_id = thread_id

    def acquire(self, blocking=True):
        if self.resource_locks[self.resource_name].acquire(blocking):
            self.acquired = True
            logger.debug("Thread %i: Acquired resource lock %s.",
                         self.thread_id,
                         self.resource_name)
            return True
        return False

    def release(self):
        if self.acquired:
            self.resource_locks[self.resource_name].release()
            self.acquired = False
            logger.debug("Thread %i: Released resource lock %s.",
                         self.thread_id,
                         self.resource_name)
