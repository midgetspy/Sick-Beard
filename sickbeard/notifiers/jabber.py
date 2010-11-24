#!/usr/bin/python

import sickbeard
import lib.xmpp as xmpp

from sickbeard import logger

def sendJabber(message):
    sendJabberMessage(sickbeard.JABBER_USERNAME, sickbeard.JABBER_PASSWORD, sickbeard.JABBER_SERVER, sickbeard.JABBER_PORT, sickbeard.JABBER_RECIPIENT, message)

def sendJabberMessage(username, password, server, port, recipient, message):
    #Make sure port is a number
    port = int(port)
    
    #Get the username and domain
    (user, domain) = username.split("@")
    
    logger.log("[Jabber] Connecting " + user + "@" + domain + " (" + password +") at " + server + ":" + str(port))
    
    try:
        #Create a new client, to debug xmpp;
        #cnx = xmpp.Client(domain)   
        cnx = xmpp.Client(domain, debug=[])
        
        #Connect to the server
        serverport=(server, port)
        cnx.connect(serverport)
    except Exception as inst:
        logger.log("[Jabber] Error during Jabber connection, make sure the server is correct!")
        logger.log("[Jabber] " + inst)
        return "Error during Jabber connection, make sure the server is correct!"
    
    #Authenticate user
    if cnx.auth(user, password, 'Sickbeard Notifier') is not None:
        #Send Message
        logger.log("[Jabber] Sending message '" + message + "' to " + recipient)
        try:
            cnx.send(xmpp.Message(recipient, message))
        except Exception as inst:
            logger.log(inst, logger.ERROR)
        return "Message sent successfully!"
    else:
        logger.log("[Jabber] Authentication Failed")
        return "Failed to authenticate! Please make sure the username, domain & password are correct!"

