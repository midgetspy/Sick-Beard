import json

import requests

from .device import Device
from .contact import Contact

class PushBullet(object):

    DEVICES_URL = "https://api.pushbullet.com/v2/devices"
    CONTACTS_URL = "https://api.pushbullet.com/v2/contacts"
    ME_URL = "https://api.pushbullet.com/v2/users/me"
    PUSH_URL = "https://api.pushbullet.com/v2/pushes"
    UPLOAD_REQUEST_URL = "https://api.pushbullet.com/v2/upload-request"


    def __init__(self, api_key):
        self.api_key = api_key
        self._json_header = {'Content-Type': 'application/json'}

        self._session = requests.Session()
        self._session.auth = (self.api_key, "")
        self._session.headers.update(self._json_header)

        self.refresh()

    def _load_devices(self):
        self.devices = []

        resp = self._session.get(self.DEVICES_URL)
        resp_dict = resp.json()
        device_list = resp_dict.get("devices", [])

        for device_info in device_list:
            d = Device(self, device_info)
            self.devices.append(d)

    def _load_contacts(self):
        self.contacts = []

        resp = self._session.get(self.CONTACTS_URL)
        resp_dict = resp.json()
        contacts_list = resp_dict.get("contacts", [])

        for contact_info in contacts_list:
            c = Contact(self, contact_info)
            self.contacts.append(c)

    def _load_user_info(self):
        r = self._session.get(self.ME_URL)
        if r.status_code == requests.codes.ok:
            self.user_info = r.json()
        else:
            self.user_info = {}

    def new_device(self, nickname):
        data = {"nickname": nickname, "type": "stream"}
        r = self._session.post(self.DEVICES_URL, data=json.dumps(data))
        if r.status_code == requests.codes.ok:
            new_device = Device(self, r.json())
            self.devices.append(new_device)
            return True, new_device
        else:
            return False, None

    def new_contact(self, name, email):
        data = {"name": nickname, "email": email}
        r = self._session.post(self.CONTACTS_URL, data=json.dumps(data))
        if r.status_code == requests.codes.ok:
            new_contact = Contact(self, r.json())
            self.contacts.append(new_contact)
            return True, new_contact
        else:
            return False, None

    def edit_device(self, device, nickname=None, model=None, manufacturer=None):
        data = {"nickname": nickname}
        iden = device.device_iden
        r = self._session.post("{}/{}".format(self.DEVICES_URL, iden), data=json.dumps(data))
        if r.status_code == requests.codes.ok:
            new_device = Device(self, r.json())
            self.devices[self.devices.index(device)] = new_device
            return True, new_device
        else:
            return False, device

    def edit_contact(self, contact, name):
        data = {"name": name}
        iden = contact.iden
        r = self._session.post("{}/{}".format(self.CONTACTS_URL, iden),
                                data=json.dumps(data))
        if r.status_code == requests.codes.ok:
            new_contact = Contact(self, r.json())
            self.contacts[self.contacts.index(contact)] = new_contact
            return True, new_contact
        else:
            return False, contact

    def remove_device(self, device):
        iden = device.device_iden
        r = self._session.delete("{}/{}".format(self.DEVICES_URL, iden))
        if r.status_code == requests.codes.ok:
            self.devices.remove(device)
            return True, r.json()
        else:
            return False, r.json()

    def remove_contact(self, contact):
        iden = contact.iden
        r = self._session.delete("{}/{}".format(self.CONTACTS_URL, iden))
        if r.status_code == requests.codes.ok:
            self.contacts.remove(contact)
            return True, r.json()
        else:
            return False, r.json()

    def get_pushes(self, modified_after=None):
        data = {"modified_after": modified_after}
        r = self._session.get(self.PUSH_URL, params=data) 

        if r.status_code == requests.codes.ok:
            return True, r.json().get("pushes")
        else:
            return False, r.json()

    def dismiss_push(self, iden):
        data = {"dismissed": True}
        r = self._session.post("{}/{}".format(self.PUSH_URL, iden), data=json.dumps(data))
 
        if r.status_code == requests.codes.ok:
            return True, r.json()
        else:
            return False, r.json()  

    def delete_push(self, iden):
        r = self._session.delete("{}/{}".format(self.PUSH_URL, iden))
 
        if r.status_code == requests.codes.ok:
            return True, r.json()
        else:
            return False, r.json()

    def push_file(self, file_name, file_url, file_type, body=None, device=None, contact=None):
        data = {"type": "file", "file_type": file_type, "file_url": file_url, "file_name": file_name}
        if body:
            data["body"] = body

        if device:
            data["device_iden"] = device.device_iden
        elif contact:
            data["email"] = contact.email
    
        return self._push(data)

    def push_note(self, title, body, device=None, contact=None):
        data = {"type": "note", "title": title, "body": body}
        if device:
            data["device_iden"] = device.device_iden
        elif contact:
            data["email"] = contact.email

        return self._push(data)

    def push_address(self, name, address, device=None, contact=None):
        data = {"type": "address", "name": name, "address": address}
        if device:
            data["device_iden"] = device.device_iden
        elif contact:
            data["email"] = contact.email

        return self._push(data)

    def push_list(self, title, items, device=None, contact=None):
        data = {"type": "list", "title": title, "items": items}
        if device:
            data["device_iden"] = device.device_iden
        elif contact:
            data["email"] = contact.email

        return self._push(data)

    def push_link(self, title, url, body=None, device=None, contact=None):
        data = {"type": "link", "title": title, "url": url, "body": body}

        if device:
            data["device_iden"] = device.device_iden
        elif contact:
            data["email"] = contact.email

        return self._push(data)

    def _push(self, data):
        r = self._session.post(self.PUSH_URL, data=json.dumps(data))

        if r.status_code == requests.codes.ok:
            return True, r.json()
        else:
            return False, r.json()

    def refresh(self):
        self._load_devices()
        self._load_contacts()
        self._load_user_info()
