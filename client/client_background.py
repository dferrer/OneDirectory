import bcrypt, json, MySQLdb, os, pysftp, re, sys
from os.path import expanduser, getsize, join
from twisted.internet import protocol, reactor, inotify
from twisted.python import filepath
from getpass import getpass
from datetime import datetime

# Use global variables to maintain a connection to the database.
with open('password.txt') as f:
    db = MySQLdb.connect(host="dbm2.itc.virginia.edu", user="dlf3x", passwd=f.read().strip(), db="cs3240onedir")
db.autocommit(True)
cursor = db.cursor()

# Specify server address and port number.
HOST = '128.143.67.201'
PORT = 2121

def adjustPath(path):
    index = path.find('onedir')
    return path[index:]

def getAbsolutePath(path):
    home = expanduser('~')
    return '{0}/{1}'.format(home, path)

def getServerPath(user, path):
    return '/home/dlf3x/CS3240/{0}/{1}'.format(user, path)

def connect():
    """Connects to the server using a local password file."""
    with open('server.txt') as f:
        data = f.read().splitlines()
        return pysftp.Connection(host=data[0], username=data[1], password=data[2])

# def download(server, remote_path, local_path):
#     """Downloads a file from the server."""
#     server.get(remote_path, local_path)

# def upload(server, remote_path, local_path):
#     """Uploads a file to the server."""
#     server.put(local_path, remote_path)


# make a function to execute SQL queries

class ClientFactory(protocol.ClientFactory):
    def __init__(self, path, user):
        self._path = filepath.FilePath(path)
        self._user = user
        self._protocol = protocol.Protocol()
        self._notifier = inotify.INotify()
        # reactor.callInThread(self._connection = connect())

    def startFactory(self):
        self._connection = connect()
        self._notifier.startReading()
        self._notifier.watch(self._path, autoAdd=True, callbacks=[self.onChange], recursive=True)

    def onChange(self, watch, fpath, mask):
        path = adjustPath(fpath.path)
        cmd = ' '.join(inotify.humanReadableMask(mask))
        self.dispatch(path, cmd)

    def dispatch(self, path, cmd):
        commands = {
            'create' : self._handleCreate,
            'create is_dir' : self._handleCreateDir,
            'delete' : self._handleDelete,
            'delete is_dir' : self._handleDeleteDir,
            'modify' : self._handleModify,
        }
        commands.get(cmd, lambda _: None)(path)

    def _handleCreate(self, path):
        data = json.dumps({
                'user' : self._user,
                'cmd' : 'touch',
                'path' : path,
            })
        cursor.execute("INSERT INTO file VALUES (%s, %s, %s)", (path, self._user, 0))
        cursor.execute("INSERT INTO log VALUES (%s, %s, %s, %s)", (self._user, path, datetime.now(), 'create'))
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
        cursor.execute("DELETE FROM file WHERE path = %s AND user_id = %s", (path, self._user))
        cursor.execute("INSERT INTO log VALUES (%s, %s, %s, %s)", (self._user, path, datetime.now(), 'delete'))
        self._protocol.transport.write(data)

    def _handleDeleteDir(self, path):
        data = json.dumps({
                'user' : self._user,
                'cmd' : 'rmdir',
                'path' : path,
            })
        absolute_path = getAbsolutePath(path)
        for (fpath, _, files) in os.walk(absolute_path):
            for f in files:
                final_path = adjustPath(join(fpath, f))
                cursor.execute("DELETE FROM file WHERE path = %s AND user_id = %s", (final_path, self._user))
                cursor.execute("INSERT INTO log VALUES (%s, %s, %s, %s)", (self._user, final_path, datetime.now(), 'delete'))
        self._protocol.transport.write(data)

    def _handleModify(self, path):
        absolute_path = getAbsolutePath(path)
        server_path = getServerPath(self._user, path)
        cursor.execute("INSERT INTO log VALUES (%s, %s, %s, %s", (self._user, path, datetime.now(), 'modify'))
        self._connection.put(absolute_path, server_path)

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