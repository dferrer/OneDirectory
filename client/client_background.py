from twisted.internet import protocol, reactor
import sys

HOST = '128.143.67.201'
PORT = 2121

class TSClntProtocol(protocol.Protocol):
    def sendData(self):
        """
        Our own method, does NOT override anything in base class.
        Get data from keyboard and send to the server.
        """
        data = raw_input('Enter JSON of command: ')
        if data:
            self.transport.write(str(data))
        else:
            self.transport.loseConnection() # if no data input, close connection

    def connectionMade(self):
        """ what we'll do when connection first made """
        self.sendData()

    def dataReceived(self, data):
        """ what we'll do when our client receives data """
        print "client received: ", data
        self.sendData()  # let's repeat: get more data to send to server

class TSClntFactory(protocol.ClientFactory):
    protocol = TSClntProtocol
    # next, set methods to be called when connection lost or fails
    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
        reactor.stop()
    # clientConnectionLost = clientConnectionFailed = \
    #     lambda self, connector, reason: reactor.stop()  # version from book
    #     # lambda self, connector, reason: handleLostFailed(reason)

    # # Heck, I had this working with the code just above this, so you didn't need
    # # the lamba.  But then I broke it.  Will post a new version with a fix.
    # def handleLostFailed1(self, reason):
    #     print 'Connection closed, lost or failed.  Reason:', reason
    #     reactor.stop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        HOST = sys.argv[1]
    print "Connecting to (HOST, PORT): ", (HOST, PORT)

    reactor.connectTCP(HOST, PORT, TSClntFactory())
    reactor.run()