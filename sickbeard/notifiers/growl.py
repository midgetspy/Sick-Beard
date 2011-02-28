import socket
import sys

import sickbeard

from sickbeard import logger, common

from lib.growl import netgrowl

class GrowlNotifier:

    def test_notify(self, host, password):
        return self._sendGrowl("Test Growl", "Testing Growl settings from Sick Beard", "Test", host, password, force=True)

    def notify_snatch(self, ep_name):
        if sickbeard.GROWL_NOTIFY_ONSNATCH:
            self._sendGrowl(common.notifyStrings[common.NOTIFY_SNATCH], ep_name)

    def notify_download(self, ep_name):
        if sickbeard.GROWL_NOTIFY_ONDOWNLOAD:
            self._sendGrowl(common.notifyStrings[common.NOTIFY_DOWNLOAD], ep_name)

    def _send_growl(self, options,message=None):
    
        #Send Registration
        #register = gntp.GNTPRegister()
        #register.add_header('Application-Name',options['app'])
        #register.add_notification(options['name'],True)
        if options['debug']:print 'prepping register'
        register = netgrowl.GrowlRegistrationPacket(application=options['app'],password=options['password'])
        register.addNotification(options['name'],True)
    
        #if options['password']:
        #    register.set_password(options['password'])
    
        if options['debug']:print 'sending register'
        self._send(options['host'],options['port'],register.payload(),options['debug'])
    
        if options['debug']:print 'prepping notification'

        #Send Notification
        #notice = gntp.GNTPNotice()
        notice = netgrowl.GrowlNotificationPacket(application=options['app'],password=options['password'],
                notification=options['name'], title=options['title'],
                description=message, priority=options['priority'], sticky=options['sticky'])
    
        #Required
        #notice.add_header('Application-Name',options['app'])
        #notice.add_header('Notification-Name',options['name'])
        #notice.add_header('Notification-Title',options['title'])
    
        #if options['password']:
        #    notice.set_password(options['password'])
    
        #Optional
        #if options['sticky']:
        #    notice.add_header('Notification-Sticky',options['sticky'])
        #if options['priority']:
        #    notice.add_header('Notification-Priority',options['priority'])
        #if options['icon']:
        #    notice.add_header('Notification-Icon',options['icon'])
    
        #if message:
        #    notice.add_header('Notification-Text',message)

        #response = self._send(options['host'],options['port'],notice.encode(),options['debug'])
        #if isinstance(response,gntp.GNTPOK): return True
        #return False
        if options['debug']:print 'sending notification'
        response = self._send(options['host'],options['port'],notice.payload(),options['debug'])

        if options['debug']:print 'done'
        return True 

    def _send(self, host,port,data,debug=False):
        if debug: print '<Sending>\n',data,'\n</Sending>'
        addr = (host, port)
        s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        s.sendto(data, addr)

        
        #response = ''
        #s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #s.connect((host,port))
        #s.send(data)
        #response = gntp.parse_gntp(s.recv(1024))
        #s.close()
        s.close()
    
        #if debug: print '<Recieved>\n',response,'\n</Recieved>'

        return ''#response

    def _sendGrowl(self, title="Sick Beard Notification", message=None, name=None, host=None, password=None, force=False):
    
        if not sickbeard.USE_GROWL and not force:
            return False
    
        if name == None:
            name = title
    
        if host == None:
            hostParts = sickbeard.GROWL_HOST.split(':')
        else:
            hostParts = host.split(':')
    
        if len(hostParts) != 2 or hostParts[1] == '':
            port = netgrowl.GROWL_UDP_PORT
            #port = 23053
        else:
            port = int(hostParts[1])
    
        growlHosts = [(hostParts[0],port)]
    
        opts = {}
    
        opts['name'] = name
    
        opts['title'] = title
        opts['app'] = 'SickBeard'
    
        opts['sticky'] = False
        opts['priority'] = 0
        opts['debug'] = False
    
        if password == None:
            opts['password'] = sickbeard.GROWL_PASSWORD
        else:
            opts['password'] = password
    
        opts['icon'] = False
    
    
        for pc in growlHosts:
            opts['host'] = pc[0]
            opts['port'] = pc[1]
            logger.log(u"Sending growl to "+opts['host']+":"+str(opts['port'])+": "+message)
            try:
                return self._send_growl(opts, message)
            except socket.error, e:
                logger.log(u"Unable to send growl to "+opts['host']+":"+str(opts['port'])+": "+str(e).decode('utf-8'))
                return False

notifier = GrowlNotifier
