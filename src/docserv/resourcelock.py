import logging
import os
import threading

from docserv.functions import resource_to_filename

my_env = os.environ

logger = logging.getLogger('docserv')

LOCK_TYPES = ['git-remote', 'backup-dir']


class ResourceLock:
    """
    It is not safe to run multiple git commands on one repository
    at the same time. For example, running git pull in parallel
    in one repo breaks git. This can happen if build intructions
    for several languages are sent at the same time. Therefore
    we need to lock the usage of git repos down to only one thread
    at a time.
    """

    def __init__(self, lock_type, resource, thread_id, resource_locks,
      resource_lock_operation_lock):
        """
        lock_type -- whether to lock a Git remote ('git-remote') or a backup dir
            ('backup-dir')
        resource -- resource that is locked
        thread_id -- ID of thread calling this method
        resource_locks -- dict of all existing resource locks
        resource_lock_operation_lock -- lock that allows only a single
            resource lock operation at once
        """
        self.resource_locks = resource_locks
        self.resource_lock_operation_lock = resource_lock_operation_lock
        if lock_type in LOCK_TYPES:
            self.lock_type = lock_type
        else:
            self.lock_type = LOCK_TYPES[0]
            logger.warning("Thread %i: Reset unknown resource lock type \"%s\" to default type \"%s\".",
                        self.thread_id,
                        lock_type,
                        self.lock_type)
        self.resource = resource
        self.resource_lock_operation_lock.acquire()
        if [self.lock_type, self.resource] not in resource_locks:
            self.resource_locks[[self.lock_type, self.resource]] = threading.Lock()
        self.resource_lock_operation_lock.release()
        self.acquired = False
        self.thread_id = thread_id

    def acquire(self, blocking=True):
        if self.resource_locks[[self.lock_type, self.resource]].acquire(blocking):
            self.acquired = True
            logger.debug("Thread %i: Acquired lock for %s resource \"%s\".",
                         self.thread_id,
                         self.lock_type,
                         self.resource)
            return True
        return False

    def release(self):
        if self.acquired:
            self.resource_locks[[self.lock_type, self.resource]].release()
            self.acquired = False
            logger.debug("Thread %i: Released lock for %s resource \"%s\".",
                         self.thread_id,
                         self.lock_type,
                         self.resource)
        else:
            # I guess this should not happen. So, make this a warning.
            logger.warning("Thread %i: Could not release lock for %s resource \"%s\", because no lock was acquired for it.",
                         self.thread_id,
                         self.lock_type,
                         self.resource)
