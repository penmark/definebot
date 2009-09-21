from twisted.application import service
from twisted.words.protocols.jabber import jid
from wokkel.client import XMPPClient
from definebot import DefineBot

from conf import BOT_JID, BOT_PWD, BOT_SERVER, BOT_ROOM, BOT_NICK

application = service.Application('definebot')
xmppclient = XMPPClient(jid.internJID(BOT_JID), BOT_PWD)
xmppclient.logTraffic = True
mucbot = DefineBot(BOT_SERVER, BOT_ROOM, BOT_NICK)
mucbot.setHandlerParent(xmppclient)
xmppclient.setServiceParent(application)

