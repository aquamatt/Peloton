# Copyright (c) 2007-2008 ReThought Limited and Peloton Contributors
# All Rights Reserved
# See LICENSE for details
""" Provides classes through which the logger can post messages onto an IRC
channel. Code copied and modified from examples on the Twisted Matrix
tutorial site. See:

http://twistedmatrix.com/projects/core/documentation/howto/clients.html

"""
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol
from twisted.internet.task import LoopingCall
from twisted.internet.defer import DeferredQueue

# system imports
import time, sys


class LogBot(irc.IRCClient):
    """A logging IRC bot."""
    
    def __getNick(self):
        return self.factory.nickname
        
    nickname = property(__getNick)
    buffer = []
    SIGNEDON = False
    
    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.queueListen()

    def connectionLost(self, reason):
        print("%s" % reason)
        self.SIGNEDON = False
        irc.IRCClient.connectionLost(self, reason)

    # callbacks for events
    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)
        self.SIGNEDON = True
        self.clearBuffer()
        
    def clearBuffer(self):
        while self.buffer:
            self.factory.messageQueue.put(self.buffer.pop(0))

    def sendMessage(self, msg="It's full of stars"):
        if not self.SIGNEDON:
            self.buffer.append(msg)
        else:
            self.say(self.factory.channel, msg, length = 1024)
        # reactor.callLater(1, self.queueListen) # throttled
        self.queueListen()

    def queueListen(self):
        d = self.factory.messageQueue.get()
        d.addCallback(self.sendMessage)
        d.addErrback(self.postError)

    def postError(self, err):
        print err

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.factory.messageQueue.put("Peloton logger connected")

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        pass

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        pass

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        pass


class LogBotFactory(protocol.ClientFactory):
    """A factory for LogBots.

    A new protocol instance will be created each time we connect to the server.
    """

    # the class of the protocol to build when new connection is made
    protocol = LogBot

    def __init__(self, channel, nickname):
        self.channel = channel
        self.nickname = nickname
        self.messageQueue = DeferredQueue()

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print("Connection failed: %s" % reason)
        reactor.stop()

    def postMessage(self, msg):
        reactor.callFromThread(self.messageQueue.put, msg)

def connectIRC(host, port, channel, nick):
    f = LogBotFactory(channel, nick)
    reactor.connectTCP(host, port, f)
    return f.postMessage

if __name__ == '__main__':
    # create factory protocol and application
    f = connectIRC("192.168.25.32", 6667, "#peloton", "Peloton")
    reactor.callLater(5, f, "Hello from me!")
    # run bot
    reactor.run()

