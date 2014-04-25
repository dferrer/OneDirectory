import json, os, re
from twisted.internet import protocol, reactor, inotify
from twisted.python import filepath
from exceptions import OSError
from shutil import rmtree

PORT = 2121
HOME = os.path.expanduser('~')

class ServerProtocol(protocol.Protocol):
    def connectionMade(self):
        print 'Connected from ' + str(self.transport.getPeer().host)
        
    def dataReceived(self, data):
        print 'received ' + str(data)
        received = filter(None, re.split('({.*?})', data))
        for item in received:
            message = json.loads(item)
            self.dispatch(message)

    def dispatch(self, message):
        user = message['user']
        cmd = message['cmd']
        commands = {
            'create account' : self._handleCreateAccount,
            'touch' : self._handleTouch,
            'mkdir' : self._handleMkdir,
            'rm' : self._handleRm,
            'rmdir' : self._handleRmdir,
        }
        commands.get(cmd, lambda _: None)(message, user)

    def _handleTouch(self, message, user):
        path = message['path']
        absolute_path = '{0}/CS3240/{1}/{2}'.format(HOME, user, path)
        with open(absolute_path, 'a'):
            os.utime(absolute_path, None)

    def _handleCreateAccount(self, message, user):
        os.makedirs('{0}/CS3240/{1}/onedir'.format(HOME, user))

    def _handleMkdir(self, message, user):
        path = message['path']
        absolute_path = '{0}/CS3240/{1}/{2}'.format(HOME, user, path)
        os.mkdir(absolute_path)

    def _handleRm(self, message, user):
        path = message['path']
        absolute_path = '{0}/CS3240/{1}/{2}'.format(HOME, user, path)
        try:
            os.remove(absolute_path)
        except OSError:
            pass
            
    def _handleRmdir(self, message, user):
        path = message['path']
        absolute_path = '{0}/CS3240/{1}/{2}'.format(HOME, user, path)
        rmtree(absolute_path)

    # def handle_login(self,message):
    #     user = message['user']
    #     print user + ' logged in.'
    #     return_message = '%s successfully logged in.' % str(user)
    #     self.transport.write(return_message)
    
    # def handle_logout(self,message):
    #     user = message['user']
    #     print user + ' logged out.'
    #     return_message = '%s successfully logged out.' % str(user)
    #     self.transport.write(return_message)

    # def handle_syncOn(self,message): #FINISH by bringing client up to date
    #     user = message['user']
    #     print user + 'is synchronizing.'
    #     return_message = '%s is now auto synchronizing' % str(user)
    #     self.transport.write(return_message)
    
    # def handle_syncOff(self,message):
    #     user = message['user']
    #     print user + 'stopped synchronizing.'
    #     return_message = '%s has stopped  auto synchronizing' % str(user)
    #     self.transport.write(return_message)
    
class ServerFactory(protocol.ServerFactory):
    def __init__(self, path):
        self._path = filepath.FilePath(path)
        self._protocol = ServerProtocol()
        self._notifier = inotify.INotify()
        self._notifier.startReading()
        self._notifier.watch(self._path, autoAdd=True, callbacks=[self.onChange], recursive=True)

    def buildProtocol(self, addr):
        return self._protocol

    def onChange(self, watch, fpath, mask):
        index = fpath.path.find('onedir')
        path = fpath.path[index:]
        user = re.search('CS3240/(.*)/onedir', fpath).group(1)
        cmd = ' '.join(inotify.humanReadableMask(mask))
        self.dispatch(path, cmd, user)

    def dispatch(self, path, cmd, user):
        commands = {
            # 'create' : self._handleCreate,
            'create is_dir' : self._handleCreateDir,
            'delete' : self._handleDelete,
        }
        commands.get(cmd, lambda _: None)(path, user)

    def _handleCreateDir(self, path, user):
        data = json.dumps({
            'user' : user,
            'cmd' : 'mkdir',
            'path' : path,
            })
        self._protocol.transport.write(data)

    def _handleDelete(self, path, user):
        data = json.dumps({
            'user' : user,
            'cmd' : 'rm',
            'path' : path,
            })
        self._protocol.transport.write(data)

def main():
    """Creates a factory and runs the reactor"""
    path = '{0}/CS3240/onedir'.format(HOME)
    factory = ServerFactory(path)
    reactor.listenTCP(PORT, factory)
    reactor.run()
        
if __name__ == "__main__":
    main()