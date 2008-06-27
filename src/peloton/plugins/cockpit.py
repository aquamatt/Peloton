# $Id: cockpit.py 122 2008-04-11 08:22:28Z mp $
#
# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Provide a remote control console via SSH. """

from peloton.plugins import PelotonPlugin
from peloton.coreio import PelotonManagementInterface
from peloton.exceptions import PluginError

from twisted.application import service, strports
from twisted.cred import checkers, portal
from twisted.conch import manhole, manhole_ssh, recvline, checkers as conchc
from twisted.conch.insults import insults
from twisted.internet import protocol, reactor
from twisted.internet.error import CannotListenError

class Cockpit(PelotonPlugin):
    """ Provides a control console accessible via SSH. 
    
Intended that this is a more controlled, higher level interface than
the PelotonShell.

Definitely work in progress... this is just at the demo level."""

    def initialise(self):
        # create an interface, pull out all 'public_*' methods
        # into our namespace, striping the prefix
        psc = PelotonManagementInterface(self.kernel)
        publicMethods =  [i for i in dir(psc) if i.startswith('public_')]
        self.namespace={}
        for m in publicMethods:
            self.namespace[m[7:]] = getattr(psc, m)
        
        self.cockpit = PasswordCockpit(int(self.config.port),
                                   **{self.config.username:self.config.password})
    def start(self):
        try:
            self.cockpit.startService()
            self.logger.info("Cockpit plugin initialised")
        except CannotListenError:
            raise PluginError("Cockpit cannot listen on port %d" % self.config.port)
        
    def _stopped(self, *args, **kargs):
        self.logger.info("Cockpit plugin stopped")
        
    def stop(self):
        self.logger.info("Cockpit plugin stopping")
        d = self.cockpit.stopService()
        d.addCallback(self._stopped)

class CockpitProtocol(recvline.HistoricRecvLine):
    def __init__(self, user):
        self.user = user

    def connectionMade(self):
        recvline.HistoricRecvLine.connectionMade(self)
        self.terminal.write("Peloton Cockpit")
        self.terminal.nextLine( )
        self.do_help( )
        self.showPrompt( )
        reactor.callLater(0.1,self._init)

    def _init(self):
        self.terminal.reset( )
        self.terminal.write("Peloton Cockpit")
        self.terminal.nextLine()
        self.terminal.write("---------------")
        self.terminal.nextLine()
        self.terminal.write("type 'help' for command list.")
        self.terminal.nextLine()
        self.showPrompt()

    def showPrompt(self):
        self.terminal.write("peloton> ")

    def getCommandFunc(self, cmd):
        return getattr(self, 'do_' + cmd, None)

    def lineReceived(self, line):
        line = line.strip( )
        if line:
            cmdAndArgs = line.split( )
            cmd = cmdAndArgs[0]
            args = cmdAndArgs[1:]
            func = self.getCommandFunc(cmd)
            if func:
                try:
                    func(*args)
                except Exception, e:
                    self.terminal.write("Error: %s" % e)
                    self.terminal.nextLine( )
            else:
                self.terminal.write("No such command.")
                self.terminal.nextLine( )
        self.showPrompt( )

    def do_help(self, cmd=''):
        "Get help on a command. Usage: help command"
        if cmd:
            func = self.getCommandFunc(cmd)
            if func:
                self.terminal.write(func.__doc__)
                self.terminal.nextLine( )
                return
        publicMethods = filter(
            lambda funcname: funcname.startswith('do_'), dir(self))
        commands = [cmd.replace('do_', '', 1) for cmd in publicMethods]
        self.terminal.write("Commands: " + " ".join(commands))
        self.terminal.nextLine( )
    def do_echo(self, *args):
        "Echo a string. Usage: echo my line of text"
        self.terminal.write(" ".join(args))
        self.terminal.nextLine( )
    def do_whoami(self):
        "Prints your user name. Usage: whoami"
        self.terminal.write(self.user.username)
        self.terminal.nextLine( )
    def do_quit(self):
        "Ends your session. Usage: quit"
        self.terminal.write("Thanks for playing!")
        self.terminal.nextLine( )
        self.terminal.loseConnection( )
    def do_clear(self):
        "Clears the screen. Usage: clear"
        self.terminal.reset( )

class BaseCockpit(service.MultiService):
    def __init__(self, port, checker):
        """
        @type port: string or int
        @param port: what port should the Cockpit listen on? This is a
        strports specification string, like 'tcp:12345' or
        'tcp:12345:interface=127.0.0.1'. Bare integers are treated as a
        simple tcp port.

        @type checker: an object providing the
        L{twisted.cred.checkers.ICredentialsChecker} interface
        @param checker: if provided, this checker is used to authenticate the
        client instead of using the username/password scheme. You must either
        provide a username/password or a Checker. Some useful values are::
            import twisted.cred.checkers as credc
            import twisted.conch.checkers as conchc
            c = credc.AllowAnonymousAccess # completely open
            c = credc.FilePasswordDB(passwd_filename) # file of name:passwd
            c = conchc.UNIXPasswordDatabase # getpwnam() (probably /etc/passwd)
        """

        service.MultiService.__init__(self)
        if type(port) is int:
            port = "tcp:%d" % port
        self.port = port # for comparison later
        self.checker = checker # to maybe compare later

        def makeProtocol():
            p = insults.ServerProtocol(CockpitProtocol, self)
            return p

        r = manhole_ssh.TerminalRealm()
        r.chainedProtocolFactory = makeProtocol
        p = portal.Portal(r, [self.checker])
        f = manhole_ssh.ConchFactory(p)
        s = strports.service(self.port, f)
        s.setServiceParent(self)

    def startService(self):
        service.MultiService.startService(self)

class PasswordCockpit(BaseCockpit):
    """This Cockpit accepts encrypted (ssh) connections, and requires a
    username and password to authorize access.
    """

    def __init__(self, port, **users):
        """
        @type port: string or int
        @param port: what port should the Manhole listen on? This is a
        strports specification string, like 'tcp:12345' or
        'tcp:12345:interface=127.0.0.1'. Bare integers are treated as a
        simple tcp port.
        
        Supply one or more username=password keyword arguments.
        """

        c = checkers.InMemoryUsernamePasswordDatabaseDontUse(**users)

        BaseCockpit.__init__(self, port, c)