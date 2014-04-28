import json, os, re, MySQLdb
from twisted.internet import protocol, reactor, inotify
from twisted.python import filepath
from shutil import rmtree
from os.path import expanduser, getsize, isfile, join, exists
from _mysql_exceptions import IntegrityError
from collections import defaultdict

with open('hidden.txt') as f:
    data = f.read().splitlines()
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
    return '{0}/CS3240/{1}/{2}'.format(HOME, user, path)

class ServerProtocol(protocol.Protocol):
    def __init__(self, factory):
        self.factory = factory

    def dataReceived(self, data):
        received = filter(None, re.split('({.*?})', data))
        for i in xrange(len(received)):
            item = received[i]
            message = json.loads(item)
            if message['cmd'] == 'mv_from' and i + 1 < len(received) and json.loads(received[i+1])['cmd'] == 'mv_to':
                message2 = json.loads(received[i+1])
                i += 1
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
            'create account' : self._handleCreateAccount,
            'touch' : self._handleTouch,
            'mkdir' : self._handleMkdir,
            'rm' : self._handleRm,
            'rmdir' : self._handleRmdir,
            'mv_from' : self._handleRm,
            'connect' : self._handleConnect,
        }
        commands.get(cmd, lambda a, b: None)(message, user)

    def _handleConnect(self, message, user):
        self.factory._protocols[user].append(self)

    def _handleTouch(self, message, user):
        path = message['path']
        absolute_path = getAbsolutePath(path, user)
        if not isfile(absolute_path):
            with open(absolute_path, 'a'):
                os.utime(absolute_path, None)

    def _handleCreateAccount(self, message, user):
        absolute_path = '{0}/CS3240/{1}/onedir'.format(HOME, user)
        if not exists(absolute_path):
            os.makedirs(absolute_path)

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
    
class ServerFactory(protocol.ServerFactory):
    def __init__(self, path):
        self._path = filepath.FilePath(path)
        self._notifier = inotify.INotify()
        self._protocols = defaultdict(lambda: [])

    def startFactory(self):
        self._notifier.startReading()
        self._notifier.watch(self._path, autoAdd=True, callbacks=[self.onChange], recursive=True)

    def buildProtocol(self, addr):
        return ServerProtocol(self)

    def onChange(self, watch, fpath, mask):
        index = fpath.path.find('onedir')
        path = fpath.path[index:]
        match = re.search('CS3240/(.*)/onedir', fpath.path)
        if match:
            user = match.group(1)
            cmd = ' '.join(inotify.humanReadableMask(mask))
            self.dispatch(path, cmd, user)

    def dispatch(self, path, cmd, user):
        commands = {
            'create' : (self._handleCreate, 'touch'),
            'create is_dir' : (self._sendData, 'mkdir'),
            'delete' : (self._handleDelete, 'rm'),
            'delete is_dir' : (self._handleDeleteDir, 'rmdir'),
            'moved_from' : (self._sendData, 'mv_from'),
            # 'moved_from is_dir' : (self._handleMovedFromDir, ),
            'moved_to' : (self._handleMovedTo, 'mv_to'),
            # 'moved_to is_dir' : (self._handleMovedToDir, ),
            'modify' : (self._handleModify, 'get'),
        }
        (execute, msg) = commands.get(cmd, (None, None))
        if execute:
            data = json.dumps({
                'cmd' : msg,
                'user' : user,
                'path' : path,
                })
            execute(data, path, user)
            # for proto in self._protocols[user]:
                # proto.transport.write(data)


    def _handleCreate(self, data, path, user):
        cursor.execute("INSERT IGNORE INTO file VALUES (%s, %s, %s)", (path, user, 0))
        cursor.execute("INSERT IGNORE INTO log (user_id, path, action) VALUES (%s, %s, %s)", (user, path, 'create'))
        for proto in self._protocols[user]:
            proto.transport.write(data)

    def _handleDelete(self, data, path, user):
        exclude = r'^onedir/(\d+)|(.*(swp|swn|swo|swx|tmp))$'
        if not re.match(exclude, path):
            cursor.execute("DELETE IGNORE FROM file WHERE path = %s AND user_id = %s", (path, user))
            cursor.execute("INSERT IGNORE INTO log (user_id, path, action) VALUES (%s, %s, %s)", (user, path, 'delete'))
            for proto in self._protocols[user]:
                proto.transport.write(data)

    def _handleDeleteDir(self, data, path, user):
        absolute_path = getAbsolutePath(path, user)
        for (fpath, _, files) in os.walk(absolute_path):
            for f in files:
                final_path = adjustPath(join(fpath, f))
                cursor.execute("DELETE IGNORE FROM file WHERE path = %s AND user_id = %s", (final_path, user))
                cursor.execute("INSERT IGNORE INTO log (user_id, path, action) VALUES (%s, %s, %s)", (user, final_path, 'delete'))
        for proto in self._protocols[user]:
            proto.transport.write(data)

    def _handleMovedTo(self, data, path, user):
        for proto in self._protocols[user]:
            proto.transport.write(data)

    def _handleModify(self, data, path, user):
        size = getsize(getAbsolutePath(path, user))
        try:
            cursor.execute("UPDATE file SET size = %s WHERE path = %s AND user_id = %s", (size, path, user))
            cursor.execute("INSERT INTO log (user_id, path, action) VALUES (%s, %s, %s)", (user, path, 'modify'))
        except IntegrityError:
            return
        for proto in self._protocols[user]:
            proto.transport.write(data)

    def _sendData(self, data, path, user):
        for proto in self._protocols[user]:
            proto.transport.write(data)

def main():
    """Creates a factory and runs the reactor"""
    path = '{0}/CS3240'.format(HOME)
    factory = ServerFactory(path)
    reactor.listenTCP(PORT, factory)
    reactor.run()
        
if __name__ == "__main__":
    main()

db.close()