import bcrypt, json, MySQLdb, os, pysftp, sys, time, getpass
from twisted.internet import reactor, protocol
from twisted.internet import inotify
from twisted.python import filepath

HOST = '128.143.67.201'
PORT = 2121

class TmpTell(protocol.Protocol):
    def __init__(self, factory):
        print "calling %s.%s" % (self.__class__.__name__, sys._getframe().f_code.co_name)
        self.factory = factory

    def announceNewFile(self, path, mask):
        print "calling %s.%s" % (self.__class__.__name__, sys._getframe().f_code.co_name)
        filepath = str(path)
        filepath = filepath[filepath.index("(")+1:filepath.rindex(")")-1]
        data = json.dumps({
                'cmd' : 'file_change',
                'mask' : ', '.join(inotify.humanReadableMask(mask)),
                'path' : filepath
                })
        self.transport.write(data)
    
    def connectionMade(self):
        print "connected"

    def connectionLost(self, reason):
        print "calling %s.%s" % (self.__class__.__name__, sys._getframe().f_code.co_name)


class TmpTellClientFactory(protocol.ClientFactory):
    def __init__(self, path):
        print "calling %s.%s" % (self.__class__.__name__, sys._getframe().f_code.co_name)
        self.watch_path = filepath.FilePath(path)
        self.notifier = inotify.INotify()

    def startFactory(self):
        print "calling %s.%s" % (self.__class__.__name__, sys._getframe().f_code.co_name)
        self.notifier.startReading()
        self.notifier.watch(self.watch_path, 
                            mask=(inotify.IN_MODIFY | inotify.IN_CREATE | inotify.IN_DELETE |
                                  inotify.IN_UNMOUNT | inotify.IN_MOVED_FROM | inotify.IN_MOVED_TO),
                            autoAdd=True, callbacks=[self.notify], recursive=True)
    def startedConnecting(self, connector):
        print "calling %s.%s" % (self.__class__.__name__, sys._getframe().f_code.co_name)

    def buildProtocol(self, addr):
        print "calling %s.%s" % (self.__class__.__name__, sys._getframe().f_code.co_name)
        self.protocol = TmpTell(factory=self)
        return self.protocol

    def notify(self, watch_obj, filepath, mask):
        print "calling %s.%s" % (self.__class__.__name__, sys._getframe().f_code.co_name)
        self.protocol.announceNewFile(filepath, mask)

    def clientConnectionLost(self, connector, reason):
        print "calling %s.%s" % (self.__class__.__name__, sys._getframe().f_code.co_name)

    def clientConnectionFailed(self, connector, reason):
        print "calling %s.%s" % (self.__class__.__name__, sys._getframe().f_code.co_name)

if __name__ == "__main__":
    factory = TmpTellClientFactory('/home/'+getpass.getuser()+'/onedir')
    #factory.protocol = TmpTell(factory=factory)
    reactor.connectTCP(HOST, PORT, factory)
    reactor.run()
