class Device(object):

	def __init__(self, account, device_info):
		self._account = account
		self.device_iden = device_info.get("iden")

		for attr in ("push_token", "app_version",
					 "android_sdk_version", "fingerprint",
					 "active", "nickname","manufacturer",
					 "type","created", "modified",
					 "android_version", "model", "pushable"):
			setattr(self, attr, device_info.get(attr))

	def push_note(self, title, body):
		data = {"type": "note", "title": title, "body": body}
		return self._push(data)

	def push_address(self, name, address):
		data = {"type": "address", "name": name, "address": address}
		return self._push(data)

	def push_list(self, title, items):
		data = {"type": "list", "title": title, "items": items}
		return self._push(data)

	def push_link(self, title, url, body=None):
		data = {"type": "link", "title": title, "url": url, "body": body}
		return self._push(data)

	def push_file(self, file_name, file_url, file_type, body=None):
		return self._account.push_file(file_name, file_url, file_type, body, device=self)

	def _push(self, data):
		data["device_iden"] = self.device_iden
		return self._account._push(data)

	def __str__(self):
		return "Device('{}')".format(self.nickname or ("{} {}".format(self.manufacturer or self.model)))

	def __repr__(self):
		return self.__str__()
