import getpass
from twisted.internet import inotify
from twisted.python import filepath
from twisted.internet import reactor



def notify(self, filepath, mask):
    print "event %s on %s" % (', '.join(inotify.humanReadableMask(mask)), filepath)
    
user = getpass.getuser()
#notifier = inotify.INotify(reactor)
notifier = inotify.INotify()
notifier.startReading()
notifier.watch(filepath.FilePath("/home/"+user+"/onedir"),autoAdd=True, callbacks=[notify], recursive=True)
reactor.run()
