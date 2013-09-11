#!/usr/bin/env python

from __future__ import with_statement

from errno import EACCES
from sys import argv, exit
from threading import Lock

import os

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn


class Loopback(LoggingMixIn, Operations):
    def __init__(self, root):
        self.root = os.path.realpath(root)
        self.rwlock = Lock()

    def _resolvepath(self, path):
        """ Convert a local "absolute" path into a system path relative to our root """
        return os.path.join(self.root, os.path.relpath(path, start='/'))

    def __call__(self, op, *args):
        args = list(args)
        if op != 'symlink':
            # first arg is always a local path that should be resolved, except in the case of symlink.
            args[0] = self._resolvepath(args[0])
        if op in ('link', 'rename', 'symlink'):
            # second arg is a path to be resolved for link, rename, and symlink.
            args[1] = self._resolvepath(args[1])
        return super(Loopback, self).__call__(op, *args)

    def access(self, path, mode):
        if not os.access(path, mode):
            raise FuseOSError(EACCES)

    chmod = os.chmod
    chown = os.chown

    def create(self, path, mode):
        return os.open(path, os.O_WRONLY | os.O_CREAT, mode)

    def flush(self, path, fh):
        return os.fsync(fh)

    def fsync(self, path, datasync, fh):
        return os.fsync(fh)

    def getattr(self, path, fh=None):
        st = os.lstat(path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
            'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    getxattr = None
    link = os.link
    listxattr = None
    mkdir = os.mkdir
    mknod = os.mknod
    open = os.open

    def read(self, path, size, offset, fh):
        with self.rwlock:
            os.lseek(fh, offset, 0)
            return os.read(fh, size)

    def readdir(self, path, fh):
        return ['.', '..'] + os.listdir(path)

    readlink = os.readlink

    def release(self, path, fh):
        return os.close(fh)

    rename = os.rename
    rmdir = os.rmdir

    def statfs(self, path):
        stv = os.statvfs(path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    symlink = os.symlink

    def truncate(self, path, length, fh=None):
        with open(path, 'r+') as f:
            f.truncate(length)

    unlink = os.unlink
    utimens = os.utime

    def write(self, path, data, offset, fh):
        with self.rwlock:
            os.lseek(fh, offset, 0)
            return os.write(fh, data)


if __name__ == '__main__':
    if len(argv) != 3:
        print('usage: %s <root> <mountpoint>' % argv[0])
        exit(1)

    fuse = FUSE(Loopback(argv[1]), argv[2], foreground=True)
