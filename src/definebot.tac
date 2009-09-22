from twisted.application import service
from twisted.words.protocols.jabber import jid
from wokkel.client import XMPPClient
from definebot import DefineBot

# create a conf.py in this directory and set these variables
from conf import BOT_JID, BOT_PWD, BOT_SERVER, BOT_ROOM, BOT_NICK, LASTFM_API_KEY

application = service.Application('definebot')
xmppclient = XMPPClient(jid.internJID(BOT_JID), BOT_PWD)
xmppclient.logTraffic = True
mucbot = DefineBot(BOT_SERVER, BOT_ROOM, BOT_NICK, LASTFM_API_KEY)
mucbot.setHandlerParent(xmppclient)
xmppclient.setServiceParent(application)

