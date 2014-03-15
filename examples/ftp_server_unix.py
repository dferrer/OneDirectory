from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
from pyftpdlib.authorizers import UnixAuthorizer
from pyftpdlib.filesystems import UnixFilesystem

if __name__ == "__main__":
    authorizer = UnixAuthorizer(require_valid_shell=False) # anonymous_user="root", allowed_users=["dylan"]
    handler = FTPHandler
    handler.authorizer = authorizer
    handler.abstracted_fs = UnixFilesystem
    server = FTPServer(('', 2121), handler)
    server.serve_forever()
