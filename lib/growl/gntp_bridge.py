from gntp import *
import urllib
if sys.version_info >= (2, 7, 9):
	import ssl
import Growl

def register_send(self):
	'''
	Resend a GNTP Register message to Growl running on a local OSX Machine
	'''
	print 'Sending Local Registration'
	
	#Local growls only need a list of strings
	notifications=[]
	defaultNotifications = []
	for notice in self.notifications:
		notifications.append(notice['Notification-Name'])
		if notice.get('Notification-Enabled',True):
			defaultNotifications.append(notice['Notification-Name'])
	
	appIcon = get_resource(self,'Application-Icon')
	
	growl = Growl.GrowlNotifier(
		applicationName			= self.headers['Application-Name'],
		notifications			= notifications,
		defaultNotifications	= defaultNotifications,
		applicationIcon			= appIcon,
	)
	growl.register()
	return self.encode()
	
def notice_send(self):
	'''
	Resend a GNTP Notify message to Growl running on a local OSX Machine
	'''
	print 'Sending Local Notification'
	growl = Growl.GrowlNotifier(
		applicationName			= self.headers['Application-Name'],
		notifications			= [self.headers['Notification-Name']]
	)
	
	noticeIcon = get_resource(self,'Notification-Icon')
	
	growl.notify(
		noteType = self.headers['Notification-Name'],
		title = self.headers['Notification-Title'],
		description=self.headers.get('Notification-Text',''),
		icon=noticeIcon
	)
	return self.encode()

def get_resource(self,key):
	try:
		resource = self.headers.get(key,'')
		if resource.startswith('x-growl-resource://'):
			resource = resource.split('://')
			return self.resources.get(resource[1])['Data']
		elif resource.startswith('http'):
			resource = resource.replace(' ', '%20')
			if sys.version_info >= (2, 7, 9):
				icon = urllib.urlopen(resource, context=ssl._create_unverified_context())
			else:
				icon = urllib.urlopen(resource)
			return icon.read()
		else:
			return None
	except Exception,e:
		print e
		return None

GNTPRegister.send = register_send
GNTPNotice.send = notice_send
