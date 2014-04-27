import json, os, re, MySQLdb
# from protocol import Protocol
from twisted.internet import protocol, reactor, inotify
from twisted.python import filepath
from shutil import rmtree
from datetime import datetime
from os.path import expanduser, getsize, isfile, join, exists
from _mysql_exceptions import IntegrityError
from collections import defaultdict

PORT = 2121
HOME = expanduser('~')

with open('password.txt') as f:
    db = MySQLdb.connect(host="dbm2.itc.virginia.edu", user="dlf3x", passwd=f.read().strip(), db="cs3240onedir")
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

    # def connectionLost(self):
    #     self.factory._protocols.remove(self)

    # def connectionMade(self):
    #     print 'Connected from ' + str(self.transport.getPeer().host)
    #     self.factory._protocols.append(self)
        
    def dataReceived(self, data):
        print 'received ' + str(data)
        received = filter(None, re.split('({.*?})', data))
        for i in xrange(len(received)):
            item = received[i]
            message = json.loads(item)
            if message['cmd'] == 'mv_from' and i + 1 < len(received) and json.loads(received[i+1])['cmd'] == 'mv_to':
                message2 = json.loads(received[i+1])
                i += 1
                self.dispatchMvFrom(message, message2)
            else:
                # print 'dispatching ' + message['cmd'] + ' on file ' + message['path']
                self.dispatch(message)

    def dispatchMvFrom(self, message1, message2):
        user = message1['user']
        path1 = message1['path']
        path2 = message2['path']
        absolute_path1 = getAbsolutePath(path1, user)
        absolute_path2 = getAbsolutePath(path2, user)
        if isfile(absolute_path1):
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
                print 'made ' + absolute_path
        else:
            print absolute_path + ' already exists'

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
            print 'dispatching ' + cmd + ' on ' + fpath.path
            self.dispatch(path, cmd, user)

    def dispatch(self, path, cmd, user):
        commands = {
            'create' : self._handleCreate,
            'create is_dir' : self._handleCreateDir,
            'delete' : self._handleDelete,
            'delete is_dir' : self._handleDeleteDir,
            # 'modify' : self._handleModify,
        }
        commands.get(cmd, lambda a, b: None)(path, user)

    def _handleCreate(self, path, user):
        data = json.dumps({
                'user' : user,
                'cmd' : 'touch',
                'path' : path,
            })
        # cursor.execute("SELECT * FROM file WHERE path = %s AND user_id = %s", (path, user))
        # if len(cursor.fetchall()) == 0:
        try:
            cursor.execute("INSERT INTO file VALUES (%s, %s, %s, %s)", (path, user, 0, 0))
            cursor.execute("INSERT INTO log VALUES (%s, %s, %s, %s)", (user, path, datetime.now(), 'create'))
        except IntegrityError:
            pass
        print 'There are ' + str(len(self._protocols)) + ' clients.'
        print self._protocols
        print user
        print self._protocols[user]
        for proto in self._protocols[user]:
            print 'Sending ' + str(data)
            proto.transport.write(data)

    def _handleCreateDir(self, path, user):
        data = json.dumps({
            'user' : user,
            'cmd' : 'mkdir',
            'path' : path,
            })
        # self._protocol.transport.write(data)

    def _handleDelete(self, path, user):
        data = json.dumps({
            'user' : user,
            'cmd' : 'rm',
            'path' : path,
            })
        cursor.execute("SELECT * FROM file WHERE path = %s AND user_id = %s", (path, user))
        if len(cursor.fetchall()) > 0:
            cursor.execute("DELETE FROM file WHERE path = %s AND user_id = %s", (path, user))
            cursor.execute("INSERT INTO log VALUES (%s, %s, %s, %s)", (user, path, datetime.now(), 'delete'))
            # self._protocol.transport.write(data)
        # self._protocol.transport.write(data)

    def _handleDeleteDir(self, path, user):
        data = json.dumps({
                'user' : user,
                'cmd' : 'rmdir',
                'path' : path,
            })
        absolute_path = getAbsolutePath(path, None)
        for (fpath, _, files) in os.walk(absolute_path):
            cursor.execute("SELECT * FROM file WHERE path = %s AND user_id = %s", (adjustPath(join(fpath, files[0])), user))
            if len(cursor.fetchall()) == 0:
                return
            for f in files:
                final_path = adjustPath(join(fpath, f))
                cursor.execute("DELETE FROM file WHERE path = %s AND user_id = %s", (final_path, user))
                cursor.execute("INSERT INTO log VALUES (%s, %s, %s, %s)", (user, final_path, datetime.now(), 'delete'))
        # self._protocol.transport.write(data)

def main():
    """Creates a factory and runs the reactor"""
    path = '{0}/CS3240'.format(HOME)
    factory = ServerFactory(path)
    reactor.listenTCP(PORT, factory)
    reactor.run()
        
if __name__ == "__main__":
    main()

db.close()