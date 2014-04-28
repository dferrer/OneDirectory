import json, MySQLdb, os, pysftp, re, sys
from os.path import expanduser, getsize, join, isfile, exists
from twisted.internet import protocol, reactor, inotify
from twisted.python import filepath
from shutil import rmtree

with open('hidden.txt') as f:
    data = f.read().splitlines()
    HOST = data[0]
    PORT = int(data[1])
    USERNAME = data[2]
    PASSWORD = data[3]
    DBHOST = data[4]
    DBNAME = data[5]

HOME = expanduser('~')
db = MySQLdb.connect(host=DBHOST, user=USERNAME, passwd=PASSWORD, db=DBNAME)
db.autocommit(True)
cursor = db.cursor()

def adjustPath(path):
    index = path.find('onedir')
    return path[index:]

def getAbsolutePath(path, user):
    return '{0}/{1}'.format(HOME, path)

def getServerPath(user, path):
    return '/home/{0}/CS3240/{1}/{2}'.format(USERNAME, user, path)

def connect():
    return pysftp.Connection(host=HOST, username=USERNAME, password=PASSWORD)

class ClientProtocol(protocol.Protocol):
    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        data = json.dumps({
                'cmd' : 'connect',
                'user' : self.factory._user,
            })
        self.transport.write(data)

    def dataReceived(self, data):
        cursor.execute("SELECT auto_sync FROM account WHERE user_id = %s", (self.factory._user,))
        if cursor.fetchone()[0] == 1:
            received = filter(None, re.split('({.*?})', data))
            for i in xrange(len(received)):
                item = received[i]
                message = json.loads(item)
                if message['cmd'] == 'mv_from' and i + 1 < len(received) and json.loads(received[i+1])['cmd'] == 'mv_to':
                    message2 = json.loads(received[i+1])
                    # i += 1
                    self.dispatchMvFrom(message, message2)
                else:
                    self.dispatch(message)

    def dispatchMvFrom(self, message1, message2):
        user = message1['user']
        path1 = message1['path']
        path2 = message2['path']
        absolute_path1 = getAbsolutePath(path1, user)
        absolute_path2 = getAbsolutePath(path2, user)
        if isfile(absolute_path1) and not absolute_path2[-1] == '~':
            os.rename(absolute_path1, absolute_path2)

    def dispatch(self, message):
        user = message['user']
        cmd = message['cmd']
        commands = {
            'touch' : self._handleTouch,
            'mkdir' : self._handleMkdir,
            'rm' : self._handleRm,
            'rmdir' : self._handleRmdir,
            'mv_from' : self._handleRm,
            'mv_to' : self._handleGet,
            'get' : self._handleGet,
        }
        commands.get(cmd, lambda _: None)(message, user)

    def _handleGet(self, message, user):
        path = message['path']
        local_path = getAbsolutePath(path, user)
        remote_path = getServerPath(user, path)
        self.factory._connection.get(remote_path, local_path)

    def _handleTouch(self, message, user):
        path = message['path']
        absolute_path = getAbsolutePath(path, user)
        if not isfile(absolute_path):
            with open(absolute_path, 'a'):
                os.utime(absolute_path, None)

    def _handleMkdir(self, message, user):
        path = message['path']
        absolute_path = getAbsolutePath(path, user)
        if not exists(absolute_path):
            os.mkdir(absolute_path)

    def _handleRm(self, message, user):
        path = message['path']
        absolute_path = getAbsolutePath(path, user)
        if isfile(absolute_path):
            os.remove(absolute_path)
            
    def _handleRmdir(self, message, user):
        path = message['path']
        absolute_path = getAbsolutePath(path, user)
        if exists(absolute_path):
            rmtree(absolute_path)

class ClientFactory(protocol.ClientFactory):
    def __init__(self, path, user):
        self._path = filepath.FilePath(path)
        self._user = user
        self._protocol = ClientProtocol(self)
        self._notifier = inotify.INotify()

    def startFactory(self):
        self._connection = connect()
        self._notifier.startReading()
        self._notifier.watch(self._path, autoAdd=True, callbacks=[self.onChange], recursive=True)

    def onChange(self, watch, fpath, mask):
        cursor.execute("SELECT auto_sync FROM account WHERE user_id = %s", (self._user,))
        if cursor.fetchone()[0] == 1:
            path = adjustPath(fpath.path)
            cmd = ' '.join(inotify.humanReadableMask(mask))
            self.dispatch(path, cmd)

    def dispatch(self, path, cmd):
        commands = {
            'create' : (self._handleCreate, 'touch'),
            'create is_dir' : (self._sendData, 'mkdir'),
            'delete' : (self._handleDelete, 'rm'),
            'delete is_dir' : (self._handleDeleteDir, 'rmdir'),
            'moved_from' : (self._sendData, 'mv_from'),
            'moved_to' : (self._handleMovedTo, 'mv_to'),
            'modify' : (self._handleModify, ''),
        }
        (execute, msg) = commands.get(cmd, (None, None))
        if execute:
            data = json.dumps({
                'cmd' : msg,
                'user' : self._user,
                'path' : path,
                })
            execute(path, data)

    def _handleCreate(self, path, data):
        exclude = r'^onedir/(\d+)|(.*(swp|swn|swo|swx|tmp))$'
        if not re.match(exclude, path):
            cursor.execute("INSERT IGNORE INTO file VALUES (%s, %s, %s)", (path, self._user, 0))
            cursor.execute("INSERT IGNORE INTO log (user_id, path, action) VALUES (%s, %s, %s)", (self._user, path, 'create'))
            self._protocol.transport.write(data)

    def _handleDelete(self, path, data):
            cursor.execute("DELETE IGNORE FROM file WHERE path = %s AND user_id = %s", (path, self._user))
            cursor.execute("INSERT IGNORE INTO log (user_id, path, action) VALUES (%s, %s, %s)", (self._user, path, 'delete'))
            self._protocol.transport.write(data)

    def _handleDeleteDir(self, path, data):
        absolute_path = getAbsolutePath(path, self._user)
        for (fpath, _, files) in os.walk(absolute_path):
            for f in files:
                final_path = adjustPath(join(fpath, f))
                cursor.execute("DELETE IGNORE FROM file WHERE path = %s AND user_id = %s", (final_path, self._user))
                cursor.execute("INSERT IGNORE INTO log (user_id, path, action) VALUES (%s, %s, %s)", (self._user, final_path, 'delete'))
        self._protocol.transport.write(data)

    def _handleModify(self, path, data):
        exclude = r'^onedir/(\d+)|(.*(swp|swn|swo|swx|tmp))$'
        if not re.match(exclude, path):
            absolute_path = getAbsolutePath(path, self._user)
            server_path = getServerPath(self._user, path)
            size = getsize(absolute_path)
            cursor.execute("UPDATE IGNORE file SET size = %s WHERE path = %s AND user_id = %s", (size, path, self._user))
            cursor.execute("INSERT IGNORE INTO log (user_id, path, action) VALUES (%s, %s, %s)", (self._user, path, 'modify'))
            self._connection.put(absolute_path, server_path)

    def _handleMovedTo(self, path, data):
        absolute_path = getAbsolutePath(path, self._user)
        server_path = getServerPath(self._user, path)
        self._connection.put(absolute_path, server_path)

    def _sendData(self, path, data):
        self._protocol.transport.write(data)

    def buildProtocol(self, addr):
        return self._protocol

    def clientConnectionLost(self, connector, reason):
        reactor.stop()
        sys.exit(1)

    def clientConnectionFailed(self, connector, reason):
        reactor.stop()
        sys.exit(1)

def main():
    user = sys.argv[1]
    path = '{0}/onedir'.format(HOME)
    factory = ClientFactory(path, user)
    reactor.connectTCP(HOST, PORT, factory)
    reactor.run()

if __name__ == "__main__":
    main()

db.close()
