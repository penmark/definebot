# coding: utf-8
""" A simple xmpp bot based on  http://thetofu.livejournal.com/73544.html """
from twisted.internet import defer
from twisted.words.protocols.jabber import jid
from twisted.words.xish import domish
from twisted.python import log
from wokkel import muc
from wokkel.generic import parseXml
from datetime import datetime
import re, lastfm, sys


class DefineBot(muc.MUCClient):
    
    def __init__(self, server, room, nick, lastfm_api_key=None):
        muc.MUCClient.__init__(self)
        self.server   = server
        self.room     = room
        self.nick     = nick
        self.lastfm_api_key = lastfm_api_key
        self.room_jid = jid.internJID('%s@%s/%s' % (self.room, self.server, self.nick))

    def initialized(self):
        """The bot has connected to the xmpp server, now try to join the room.
        """
        self.join(self.server, self.room, self.nick).addCallback(self.initRoom)
        
    @defer.inlineCallbacks
    def initRoom(self, room):
        """Configure the room if we just created it.
        """
        if int(room.status) == muc.STATUS_CODE_CREATED:
            config_form = yield self.getConfigureForm(self.room_jid.userhost())
            # set config default
            config_result = yield self.configure(self.room_jid.userhost())

    def userJoinedRoom(self, room, user):
        pass

    def userLeftRoom(self, room, user):
        pass

    def receivedGroupChat(self, room, user, body):
        "TODO: write a better dispatcher..."
        # check if this message addresses the bot
        cmd = body
        if not cmd.startswith('!'):
            return
        commands = {'recent': {'command': self.cmd_recent, 
                               'args': lambda x : re.search(r'^(\w+)?$', x).groups()},
                    'testxml': {'command': self.cmd_testxml,
                                'args': lambda x : (x,)}}
        input = cmd[1:].split() # strip '!'
        cmd = input[0]
        if len(input) > 1:
            rest = ' '.join(input[1:]).strip()
        else:
            rest = ''
        log.msg('cmd: %s, rest: %s' % (cmd, rest))
        if cmd in commands:
            arghandler = commands[cmd]['args']
            command = commands[cmd]['command']
            try:
                args = arghandler(rest)
            except Exception, e:
                log.err('Failed to parse args')
                args = tuple()
            try:
                command(room, user, *args)
            except Exception, e:
                log.err('Failed to run command %s' % cmd)
        else:
            log.err('No such command: %s' % cmd)
                
    def cmd_recent(self, room, user, lfm_user='d3fine'):
        if not self.lastfm_api_key:
            log.msg('No Last.fm api key configured')
            return
        api = lastfm.Api(self.lastfm_api_key)
        lfm_user = api.get_user(lfm_user)
        holder = domish.Element((None, 'div'))
        holder.addElement('em', content='Tracks recently played by %s:' % lfm_user.name)
        holder.addElement('br')
        for track in lfm_user.recent_tracks:
            chart = holder.addElement('div')
            chart.addElement('a', content=track.artist.name)['href'] = track.artist.url
            chart.addContent(u' – ')
            chart.addElement('a', content=track.name)['href'] = track.url
            chart.addContent(u' (played on %s)' % track.played_on.isoformat(' '))
            chart.addElement('br')
#            chart.addRawXml(u'<a href="%s">%s</a> - <a href="%s">%s</a> (played on %s)<br/>' % (track.artist.url, 
#                                                                                track.artist.name#, 
#                                                                                track.url,
#                                                                                track.name,
#                                                                                track.played_on.isoformat(' ')))
        self.htmlGroupChat(self.room_jid, holder)
    
    def cmd_testxml(self, room, user, text=None):
        #message = domish.Element((None, 'message'))
        if text == None:
            text = u'Some text'
        span = domish.Element((None, 'span'))
        span.addContent(text)
        span['style'] = 'font-weight: bold'
        self.htmlGroupChat(self.room_jid, span, body=text)

    def htmlGroupChat(self, to, message, body=None, children=None):
        msg = HtmlGroupChat(to, message, body=body)
        self._sendMessage(msg, children=children)

class HtmlGroupChat(muc.GroupChat):
    """Add html capabilities to the groupchat element helper"""

    def __init__(self, to, xhtml, body=None, subject=None, frm=None):
        """xhtml is the raw xhtml body or a domish.Element tree"""
        muc.GroupChat.__init__(self, to, body, subject, frm)
        xhtmlroot = domish.Element(('http://jabber.org/protocol/xhtml-im', 'html'))
        xhtmlbody = xhtmlroot.addElement(('http://www.w3.org/1999/xhtml', 'body'))
        if isinstance(xhtml, domish.Element):
            xhtmlbody.addChild(xhtml)
        else:
            # assume raw xml string
            xhtmlbody.addRawXml(xhtml)
        self.addChild(xhtmlroot)

