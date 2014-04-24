import sys
from os.path import expanduser
from twisted.internet import protocol, reactor, inotify
from twisted.python import filepath

# Specify server address and port number.
HOST = '128.143.67.201'
PORT = 2121

class ClientProtocol(protocol.Protocol):
    def __init__(self, factory):
        self._factory = factory

    def connectionMade(self):
        print 'Connected to server'

    def dataReceived(self, data):
        print 'Received {0}'.format(data)

class ClientFactory(protocol.ClientFactory):
    def __init__(self, path):
        self._path = filepath.FilePath(path)
        self._protocol = ClientProtocol(self)
        self._notifier = inotify.INotify()
        self._notifier.startReading()
        self._notifier.watch(self._path, autoAdd=True, callbacks=[self.onChange], recursive=True)

    def onChange(self, watch, fpath, mask):
        path = fpath.path
        index = path.find('onedir')
        data = json.dumps({
            'cmd' : 'inotify_cmd',
            'mask' : ', '.join(inotify.humanReadableMask(mask)),
            'path' : path[index:]
            })
        self._protocol.transport.write(str(data))

    def buildProtocol(self, addr):
        return self._protocol

    def startedConnecting(self, connector):
        print 'Connected to {0}:{1}'.format(HOST,PORT)

    def clientConnectionLost(self, connector, reason):
        print 'Lost connection: {0}'.format(reason)
        reactor.stop()
        sys.exit(1)

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed: {0}'.format(reason)
        reactor.stop()
        sys.exit(1)

def main():
    # Locate the user's onedir folder.
    home = expanduser('~')
    path = '{0}/onedir'.format(home)

    # Create a factory and run the reactor.
    factory = ClientFactory(path)
    reactor.connectTCP(HOST, PORT, factory)
    reactor.run()

if __name__ == "__main__":
    main()
