from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from os.path import expanduser

if __name__ == '__main__':
    # Instantiate a dummy authorizer
    authorizer = DummyAuthorizer()

    # Define a new user having full r/w permissions
    home = expanduser('~')
    onedir = home + '/onedir/'
    authorizer.add_user(username='test', password='12345', homedir=onedir, perm='elradfmwM')

    # Instantiate FTP handler class
    handler = FTPHandler
    handler.authorizer = authorizer

    # Define a customized banner (string returned when client connects)
    handler.banner = "pyftpdlib based ftpd ready."

    # Instantiate FTP server class and listen on localhost:2121
    address = ('', 2121)
    server = FTPServer(address, handler)

    # set a limit for connections
    server.max_cons = 256
    server.max_cons_per_ip = 5

    # start ftp server
    server.serve_forever()
