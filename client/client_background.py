import bcrypt, json, MySQLdb, re, sys
from os.path import expanduser
from twisted.internet import protocol, reactor, inotify
from twisted.python import filepath
from getpass import getpass

# Use global variables to maintain a connection to the database.
with open('password.txt') as f:
    db = MySQLdb.connect(host="dbm2.itc.virginia.edu", user="dlf3x", passwd=f.read().strip(), db="cs3240onedir")
db.autocommit(True)
cursor = db.cursor()

# Specify server address and port number.
HOST = '128.143.67.201'
PORT = 2121

class ClientFactory(protocol.ClientFactory):
    def __init__(self, path, user):
        self._path = filepath.FilePath(path)
        self._user = user
        self._protocol = protocol.Protocol()
        self._notifier = inotify.INotify()
        self._notifier.startReading()
        self._notifier.watch(self._path, autoAdd=True, callbacks=[self.onChange], recursive=True)

    def onChange(self, watch, fpath, mask):
        index = fpath.path.find('onedir')
        path = fpath.path[index:]
        cmd = ' '.join(inotify.humanReadableMask(mask))
        self.dispatch(path, cmd)

    def dispatch(self, path, cmd):
        commands = {
            'create' : self._handleCreate,
            'create is_dir' : self._handleCreateDir,
            'delete' : self._handleDelete,
            'delete is_dir' : self._handleDeleteDir
        }
        commands.get(cmd, lambda _: None)(path)

    def _handleCreate(self, path):
        data = json.dumps({
                'user' : self._user,
                'cmd' : 'touch',
                'path' : path,
            })
        self._protocol.transport.write(data)

    def _handleCreateDir(self, path):
        data = json.dumps({
                'user' : self._user,
                'cmd' : 'mkdir',
                'path' : path,
            })
        self._protocol.transport.write(data)

    def _handleDelete(self, path):
        data = json.dumps({
                'user' : self._user,
                'cmd' : 'rm',
                'path' : path,
            })
        self._protocol.transport.write(data)

    def _handleDeleteDir(self, path):
        data = json.dumps({
                'user' : self._user,
                'cmd' : 'rmdir',
                'path' : path,
            })
        self._protocol.transport.write(data)        

    def buildProtocol(self, addr):
        return self._protocol

    def clientConnectionLost(self, connector, reason):
        reactor.stop()
        sys.exit(1)

    def clientConnectionFailed(self, connector, reason):
        reactor.stop()
        sys.exit(1)

def is_valid(user, password):
    """Checks if an entered password matches a user's password in the database."""
    encoded = password.encode("utf-8")
    hashed = get_password(user)
    try:
        if bcrypt.hashpw(encoded, hashed) == hashed:
            return True
        else:
            print 'Error: incorrect password for user {0}'.format(user)
            return False
    except TypeError:
        return False

def get_password(user):
    """Queries the database for a user's password."""
    global cursor
    cursor.execute("SELECT password FROM account WHERE user_id = %s", (user,))
    try:
        return cursor.fetchone()[0]
    except TypeError:
        print "Error: user {0} not found in database.".format(user)

def main():
    # Prompt user for user ID and password before syncing.
    while True:
        user = raw_input('Please enter your user ID: ')
        password = getpass('Please enter your password: ')
        if is_valid(user, password):
            print 'Validated user ID and password. Starting sync.'
            break

    # Locate the user's onedir folder.
    home = expanduser('~')
    path = '{0}/onedir'.format(home)

    # Create a factory and run the reactor.
    factory = ClientFactory(path, user)
    reactor.connectTCP(HOST, PORT, factory)
    reactor.run()

if __name__ == "__main__":
    main()

db.close()