"""
Git Store
TiddlyWeb store implementation using Git - based on the default text store, this
store uses Git to keep track of tiddler revisions
"""

from git import Repo
from git.exc import InvalidGitRepositoryError

from tiddlyweb.stores.text import Store as TextStore
from tiddlyweb.util import LockError, write_lock, write_unlock, \
        read_utf8_file, write_utf8_file


class Store(TextStore):

    def __init__(self, store_config=None, environ=None):
        super(Store, self).__init__(store_config, environ)
        try:
            self.repo = Repo(self._root)
        except InvalidGitRepositoryError:
            self.repo = Repo.init(self._root)

    def tiddler_get(self, tiddler):
        tiddler_filename = self._tiddler_base_filename(tiddler)
        tiddler = self._read_tiddler_file(tiddler, tiddler_filename)

        revision = self._commit_hash_for_file(tiddler_filename)
        tiddler.revision = revision

        return tiddler


    def _commit_hash_for_file(self, path):
        """
        Ask tree for the latest commit for this path.
        """
        commits = list(self.repo.iter_commits(paths=path, max_count=1))
        try:
            return commits[0].hexsha
        except IndexError:
            return '0'

    def tiddler_put(self, tiddler):
        tiddler_filename = self._tiddler_base_filename(tiddler)

        # the following section is copied almost verbatim from the text store
        # TODO: refactor the text store for granular reusability
        locked = 0
        lock_attempts = 0
        while not locked:
            try:
                lock_attempts = lock_attempts + 1
                write_lock(tiddler_filename)
                locked = 1
            except LockError, exc:
                if lock_attempts > 4:
                    raise StoreLockError(exc)
                time.sleep(.1)

        # Protect against incoming tiddlers that have revision
        # set. Since we are putting a new one, we want the system
        # to calculate.
        tiddler.revision = None

        self.serializer.object = tiddler
        write_utf8_file(tiddler_filename, self.serializer.to_string())
        write_unlock(tiddler_filename)

        host = self.environ['tiddlyweb.config']['server_host']
        host = '%s:%s' % (host['host'], host['port'])
        if host.endswith(':80'): # TODO: use proper URI parsing instead
            host = host[:-3]
        user = self.environ['tiddlyweb.usersign']['name']

# XXX can't figure out how to set author and committer
# teh internets suggest using os.environ, but doing so will mess
# up the _time_ on the commit, which is hilarious. Doing a raw
# commit (that is going into what index.commit does and replicating
# it here) is very cumbersome). More research required.
        author = 'user <%s@%s>' % (user, host)
        committer = 'tiddlyweb <tiddlyweb@%s>' % host
        message = 'tiddler %s:%s put' % (tiddler.bag, tiddler.title)

        relative_path = tiddler_filename.replace(self._root, '')[1:]
        index = self.repo.index
        index.add([relative_path])
        commit = index.commit(message)
        index.write()

        tiddler.revision = commit.hexsha
