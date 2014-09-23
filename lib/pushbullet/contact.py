from .device import Device

class Contact(Device):

	def __init__(self, account, contact_info):
		self._account = account
		self.iden = contact_info.get("iden")

		for attr in ("push_token", "name", "status"
					 "created", "modified", "email",
					 "email_normalized", "active"):
			setattr(self, attr, contact_info.get(attr))

	def _push(self, data):
		data["email"] = self.email
		return self._account._push(data)

	def __str__(self):
		return "Contact('{}' <{}>)".format(self.name, self.email_normalized)
