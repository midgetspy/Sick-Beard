from config import Config
config = Config.instance()
from history import History
history = History.instance()
from jsonrpc import Server, MultiCall, Fault
from jsonrpc import ProtocolError, loads, dumps
