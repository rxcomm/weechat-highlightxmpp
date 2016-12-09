# HighlightXMPP 0.5 for IRC. Requires WeeChat >= 0.3.0,
# Python >= 2.6, and sleekxmpp.
# Repo: https://github.com/jpeddicord/weechat-highlightxmpp
# 
# Copyright (c) 2009-2015 Jacob Peddicord <jacob@peddicord.net>
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#######
#
# You must configure this plugin before using:
#
#   JID messages are sent from:
#     /set plugins.var.python.highlightxmpp.jid someid@jabber.org
#   alternatively, to use a specific resource:
#     /set plugins.var.python.highlightxmpp.jid someid@jabber.org/resource
#
#   Password for the above JID:
#     /set plugins.var.python.highlightxmpp.password abcdef
#
#   JID messages are sent *to* (if not set, defaults to the same jid as above):
#     /set plugins.var.python.highlightxmpp.to myid@jabber.org
#
#######
#
#   The commands:
#     /hltimer <n>
#       will display timer status or set to <n> minutes. The initial setting
#       is 20 minutes. This timer will set the "enable" status on after <n>
#       minutes of inactivity on the keyboard. Setting <n> to 0 or off will
#       disable the timer.
#     /hl
#       will toggle the "enable" status on/off. The initial setting is off.
#     /hlon
#       will set the "enable" status on.
#     /hloff
#       will set the "enable" status off.
#     /help hltimer
#       will display help for the timer.
#
#   The configuration option: plugins.var.python.highlightxmpp.status_prnt
#   controls where the "enable" status messages are printed.
#     /set plugins.var.python.highlightxmpp.status_prnt "core"
#   will print to the core buffer and:
#     /set plugins.var.python.highlightxmpp.status_prnt ""
#   will print to the current buffer.
#
#######


import re
import sys
import weechat as w
import sleekxmpp

if sys.version_info < (3, 0):
    from sleekxmpp.util.misc_ops import setdefaultencoding
    setdefaultencoding('utf8')

info = (
    'highlightxmpp',
    'Jacob Peddicord <jacob@peddicord.net>',
    '0.5',
    'GPL3',
    "Relay highlighted & private IRC messages over XMPP (Jabber)",
    '',
    ''
)

settings = {
    'jid': '',
    'password': '',
    'to': '',
    'enable': 'off',
    'idletime': '20',
    'status_prnt': 'core',
}


# The timer functions are essentially a copy/paste from the weechat
# auto_away.py script https://weechat.org/scripts/source/auto_away.py.html/
#
## auto_away.py : A simple auto-away script for Weechat in Python
## Copyright (c) 2010 by Specimen <spinifer at gmail dot com>
##
## Inspired in yaaa.pl by jnbek
## A very special thanks to Nils G. for helping me out with this script
## ---------------------------------------------------------------------
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Thanks for that!


# Functions
def timer_hook_function():
    ''' Timer hook to check inactivity '''
    global timer_hook
    if val_idletime() > 0:
        timer_hook = w.hook_timer(10 * 1000, 60, 0, 'idle_chk', '')
    return w.WEECHAT_RC_OK


def val_idletime():
    ''' Test idletime value '''
    try:
        idletime_value = int(w.config_get_plugin('idletime'))
    except ValueError:
        idletime_value = 0
    return idletime_value


def idle_chk(data, remaining_calls):
    ''' Inactivity check, when to change highlightxmpp status to on'''
    global timer_hook
    if int(w.info_get('inactivity', '')) >= val_idletime() * 60:
        w.unhook(timer_hook)
        w.command('', '/hlon')
        input_hook_function()
    return w.WEECHAT_RC_OK


def input_hook_function():
    ''' Input hook to check for typing '''
    global input_hook
    input_hook = w.hook_signal('input_text_changed',
                               'typing_chk', '')
    return w.WEECHAT_RC_OK


def typing_chk(data, signal, signal_data):
    ''' Activity check, when to disable highlight status '''
    global input_hook
    w.unhook(input_hook)
    w.command('', '/hloff')
    timer_hook_function()
    return w.WEECHAT_RC_OK


# Command hook and config hook
def hltimer_cmd(data, buffer, args):
    ''' /hltimer command, what to do with the arguments '''
    if args:
        value = args.strip(' ').partition(' ')
        w.config_set_plugin('idletime', value[0])
    if val_idletime() > 0:
        w.prnt(w.current_buffer(),
               '%shighlightxmpp timer%s settings:\n'
               '   Time:    %s%s%s minute(s)\n'
               % (w.color('bold'), w.color('-bold'),
               w.color('bold'), w.config_get_plugin('idletime'),
               w.color('-bold')))
    else:
        w.prnt(w.current_buffer(),
               '%shighlightxmpp timer%s is disabled.\n'
               % (w.color('bold'), w.color('-bold')))
    return w.WEECHAT_RC_OK


def switch_chk(data, option, value):
    ''' Checks when idletime setting is changed '''
    global timer_hook, input_hook
    if timer_hook:
        w.unhook(timer_hook)
    if input_hook:
        w.unhook(input_hook)
    timer_hook_function()
    return w.WEECHAT_RC_OK


def print_chk(data, option, value):
    return w.WEECHAT_RC_OK
# End of timer functions


class SendMsgBot(sleekxmpp.ClientXMPP):
    def __init__(self, jid, password, recipient, message):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)
        self.jid = jid
        self.recipient = recipient
        self.msg = message
        self.add_event_handler('session_start', self.start, threaded=True)
    def start(self, event):
        self.send_presence()
        self.get_roster()
        self.send_message(mto=self.recipient,
                          mbody=self.msg,
                          mtype='chat')
        self.disconnect(wait=True)


def send_xmpp_hook(data, signal, message, trial=1):
    w.hook_process('func:send_xmpp', 10000, 'send_xmpp_cb',
                   message)
    return w.WEECHAT_RC_OK


def send_xmpp_cb(data, command, return_code, out, err):
    if return_code == w.WEECHAT_HOOK_PROCESS_ERROR:
        w.prnt('', 'Error with command \'%s\'' % command)
        return w.WEECHAT_RC_OK
    return w.WEECHAT_RC_OK


def send_xmpp(message):
    if w.config_get_plugin('enable') != 'on':
        return
    jid = w.config_get_plugin('jid')
    jid_to = w.config_get_plugin('to')
    if not jid_to:
        jid_to = jid
    password = w.config_get_plugin('password')
    if re.search('sec.*data', password):
        password=w.string_eval_expression(password, {}, {}, {})

    xmpp = SendMsgBot(jid, password, jid_to, message)
    #xmpp.use_proxy = True
    #xmpp.proxy_config = {'host': 'localhost','port': 8123
    #                     'username': 'x','password': 'x',}
    if not xmpp.connect():
        w.prnt('', 'Unable to connect to XMPP server.')
        return
    xmpp.process(block=True)
    return


def hlon_cb(data, buf, args):
    w.config_set_plugin('enable', 'on')
    if w.config_get_plugin('status_prnt') == 'core':
        buf = ''
    w.prnt(buf, '%shighlightxmpp status%s set to %s' % \
           (w.color('bold'),w.color('-bold'),w.config_get_plugin('enable')))
    return w.WEECHAT_RC_OK


def hloff_cb(data, buf, args):
    w.config_set_plugin('enable', 'off')
    if w.config_get_plugin('status_prnt') == 'core':
        buf = ''
    w.prnt(buf, '%shighlightxmpp status%s set to %s' % \
           (w.color('bold'),w.color('-bold'),w.config_get_plugin('enable')))
    return w.WEECHAT_RC_OK


def toggle_cb(data, buf, args):
    if w.config_get_plugin('enable') == 'on':
        w.config_set_plugin('enable', 'off')
    else:
        w.config_set_plugin('enable', 'on')
    if w.config_get_plugin('status_prnt') == 'core':
        buf = ''
    w.prnt(buf, '%shighlightxmpp status%s set to %s' % \
           (w.color('bold'),w.color('-bold'),w.config_get_plugin('enable')))
    return w.WEECHAT_RC_OK


# register with weechat
if w.register(*info):
    # add our settings
    for setting in settings:
        if not w.config_is_set_plugin(setting):
            w.config_set_plugin(setting, settings[setting])
    # and finally our hooks
    w.hook_signal('weechat_highlight', 'send_xmpp_hook', '')
    w.hook_signal('weechat_pv', 'send_xmpp_hook', '')
    w.hook_command('hl', 'toggle on/off status of highlightxmpp',
                   '', '', '', 'toggle_cb', '')
    w.hook_command('hlon', 'set status of highlightxmpp',
                   '', '', '', 'hlon_cb', '')
    w.hook_command('hloff', 'set status of highlightxmpp off',
                   '', '', '', 'hloff_cb', '')
    w.hook_command('hltimer',
                   'Set highlightxmpp timer status automatically after a period of '
                   'inactivity.',
                   '[time|off]',
                   '      time: minutes of inactivity to set highlightxmpp timer\n'
                   '       off: set highlightxmpp timer off (0 also sets off)\n'
                   '\n'
                   'Without any arguments prints the current settings.\n'
                   '\n'
                   'Examples:\n'
                   '\n'
                   '/hltimer 20\n'
                   'Sets highlightxmpp timer to 20 minutes'
                   '\n'
                   '/hltimer off\n'
                   '/hltimer 0\n'
                   'Disables highlightxmpp timer.\n',
                   '',
                   'hltimer_cmd', '')
    w.hook_config('plugins.var.python.highlightxmpp.idletime',
                  'switch_chk', '')
    w.hook_config('plugins.var.python.highlightxmpp.status_prnt',
                  'print_chk', '')

    version = w.info_get('version_number', '') or 0
    timer_hook = None
    input_hook = None

    timer_hook_function()
