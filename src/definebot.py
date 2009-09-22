# coding: utf-8
""" A simple xmpp bot based on  http://thetofu.livejournal.com/73544.html """
from twisted.internet import defer
from twisted.words.protocols.jabber import jid
from twisted.words.xish import domish
from twisted.python import log
from wokkel import muc
from wokkel.generic import parseXml
from datetime import datetime
import re


class DefineBot(muc.MUCClient):
    
    def __init__(self, server, room, nick, lastfm_api_key=None):
        muc.MUCClient.__init__(self)
        self.server   = server
        self.room     = room
        self.nick     = nick
        try:
            import lastfm
            self.lfm_api = lastfm.Api(lastfm_api_key)
        except ImportError:
            log.err('Failed to import Last.fm api library, last.fm commands '
                    'will not be available.')
            self.lfm_api = None
        self.room_jid = jid.internJID('%s@%s/%s' % (self.room, self.server, self.nick))
    
    def connectionInitialized(self):
        muc.MUCClient.connectionInitialized(self)
        self.xmlstream.addObserver(muc.MESSAGE + "[@type='chat']", self._onPrivateChat)
    
    def _onPrivateChat(self, msg):
        if not msg.body:
            return
        body = unicode(msg.body)
        room_jid = jid.internJID(msg.getAttribute('from', ''))
        room = self._getRoom(room_jid)
        user = room.getUser(room_jid.resource)
        log.msg(user.nick, room.entity_id, body)
        self.receivedPrivateChat(room, user, body)

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
    
    def dispatch(self, room, user, body):
        commands = [BotCommand('recent', self.cmd_recent, 
                               r'recent\s*(?P<lfm_user>\w+)?$'),
                    BotCommand('testxml', self.cmd_testxml, 
                               r'testxml\s*(?P<text>.*)$')]
        result = None
        for cmd in commands:
            args = cmd.match(body)
            if args:
                try:
                    result = cmd.execute(room, user, args)
                except Exception, e:
                    result = str(e)
        return result
    
    def receivedPrivateChat(self, room, user, body):
        result = self.dispatch(room, user, body)
        if not result:
            result = 'So you think %s is cool?' % body
        jid = '%s@%s/%s' % (room.name, room.server, user.nick)
        self.htmlChat(jid, result)
            
        
    def receivedGroupChat(self, room, user, body):
        # check if this message addresses the bot
        if not body.startswith('!'):
            return
        result = self.dispatch(room, user, body)
        if not result:
            result = 'Whoa nelly'
        self.htmlGroupChat(self.room_jid, result)
                
    def cmd_recent(self, room, user, lfm_user='d3fine'):
        if not self.lfm_api:
            log.msg('Last.fm api not configured')
            return
        lfm_user = self.lfm_api.get_user(lfm_user)
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
        return holder
        
    def cmd_testxml(self, room, user, text=None):
        #message = domish.Element((None, 'message'))
        if text == None:
            text = u'Some text'
        span = domish.Element((None, 'span'))
        span.addContent(text)
        span['style'] = 'font-weight: bold'
        return span

    def htmlGroupChat(self, to, message, body=None, children=None):
        msg = HtmlGroupChat(to, message, body=body)
        self._sendMessage(msg, children=children)
    
    def htmlChat(self, room_jid, message, body=None, children=None):
        msg = HtmlPrivateChat(room_jid, message, children)
        self._sendMessage(msg, children=children)
        
class BotCommand(object):
    def __init__(self, name, command, regexp):
        self.name = name
        self.regexp = re.compile(regexp)
        self.command = command
    
    def execute(self, room, user, args):
        if 'cmd' in args: del args['cmd']
        return self.command(room, user, **args)
        
    def match(self, argstr):
        m = self.regexp.search(argstr)
        if m:
            return m.groupdict()
        return None

NS_XHTML_IM = 'http://jabber.org/protocol/xhtml-im'
NS_XHTML = 'http://www.w3.org/1999/xhtml'


class HtmlGroupChat(muc.GroupChat):
    """Add html capabilities to the groupchat element helper"""

    def __init__(self, to, xhtml, body=None, subject=None, frm=None):
        """xhtml is the raw xhtml body or a domish.Element tree"""
        muc.GroupChat.__init__(self, to, body, subject, frm)
        xhtmlroot = domish.Element((NS_XHTML_IM, 'html'))
        xhtmlbody = xhtmlroot.addElement((NS_XHTML, 'body'))
        if isinstance(xhtml, domish.Element):
            xhtmlbody.addChild(xhtml)
        else:
            # assume raw xml string
            xhtmlbody.addRawXml(xhtml)
        self.addChild(xhtmlroot)


class HtmlPrivateChat(muc.PrivateChat):
    """Add html capabilities to the privatchat element helper"""

    def __init__(self, to, xhtml, body=None, frm=None):
        """xhtml is the raw xhtml body or a domish.Element tree"""
        muc.PrivateChat.__init__(self, to, body, frm)
        xhtmlroot = domish.Element((NS_XHTML_IM, 'html'))
        xhtmlbody = xhtmlroot.addElement((NS_XHTML, 'body'))
        if isinstance(xhtml, domish.Element):
            xhtmlbody.addChild(xhtml)
        else:
            # assume raw xml string
            xhtmlbody.addRawXml(xhtml)
        self.addChild(xhtmlroot)
