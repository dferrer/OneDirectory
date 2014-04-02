from twisted.internet import protocol, reactor
import os
import json

PORT = 2121
HOME = os.path.expanduser('~')

class ServerProtocol(protocol.Protocol):
    def connectionMade(self):
        print 'Connected from ' + str(self.transport.getPeer().host)

    def dataReceived(self, data):
        print 'Received: ' + str(data)
        message = json.loads(data)
        cmd = message['cmd']
        if cmd == 'create account':
            self.handle_create_account(message)
        elif cmd == 'update password':
            self.handle_update_password(message)

    def handle_create_account(self, message):
        user =  message['user']
        password = message['password']
        os.makedirs(HOME + '/CS3240/' + user + '/onedir')
        print 'Account created for ' + user
        return_message = 'Created account for %s on server.' % str(user)
        self.transport.write(return_message)

    def handle_update_password(self, message):
        user = message['user']
        print 'Password updated for ' + user
        self.transport.write('flag')

if __name__ == "__main__":
    factory = protocol.Factory()
    factory.protocol = ServerProtocol
    print 'Waiting for connection on PORT: ' + str(PORT)
    reactor.listenTCP(PORT, factory)
    reactor.run()