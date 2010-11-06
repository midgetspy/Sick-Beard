import socket
import sys

import sickbeard

from sickbeard import logger

from lib.growl import gntp

def send_growl(options,message=None):

	#Send Registration
	register = gntp.GNTPRegister()
	register.add_header('Application-Name',options['app'])
	register.add_notification(options['name'],True)

	if options['password']:
		register.set_password(options['password'])

	_send(options['host'],options['port'],register.encode(),options['debug'])

	#Send Notification
	notice = gntp.GNTPNotice()

	#Required
	notice.add_header('Application-Name',options['app'])
	notice.add_header('Notification-Name',options['name'])
	notice.add_header('Notification-Title',options['title'])

	if options['password']:
		notice.set_password(options['password'])

	#Optional
	if options['sticky']:
		notice.add_header('Notification-Sticky',options['sticky'])
	if options['priority']:
		notice.add_header('Notification-Priority',options['priority'])
	if options['icon']:
		notice.add_header('Notification-Icon',options['icon'])

	if message:
		notice.add_header('Notification-Text',message)

	_send(options['host'],options['port'],notice.encode(),options['debug'])

def _send(host,port,data,debug=False):
	if debug: print '<Sending>\n',data,'\n</Sending>'

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((host,port))
	s.send(data)
	response = gntp.parse_gntp(s.recv(1024))
	s.close()

	if debug: print '<Recieved>\n',response,'\n</Recieved>'

def sendGrowl(title="Sick Beard Notification", message=None, name=None, host=None, password=None):

	if not sickbeard.USE_GROWL:
		return False

	if name == None:
		name = title

	if host == None:
		hostParts = sickbeard.GROWL_HOST.split(':')
	else:
		hostParts = host.split(':')

	if len(hostParts) != 2 or hostParts[1] == '':
		port = 23053
	else:
		port = int(hostParts[1])

	growlHosts = [(hostParts[0],port)]

	opts = {}

	opts['name'] = name

	opts['title'] = title
	opts['app'] = 'SickBeard'

	opts['sticky'] = None
	opts['priority'] = None
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
			send_growl(opts, message)
		except socket.error, e:
			logger.log(u"Unable to send growl to "+opts['host']+":"+str(opts['port'])+": "+str(e).decode('utf-8'))
