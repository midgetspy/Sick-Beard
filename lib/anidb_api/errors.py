
class AniDBError(Exception):
	pass

class AniDBIncorrectParameterError(AniDBError):
	pass

class AniDBCommandTimeoutError(AniDBError):
	pass

class AniDBMustAuthError(AniDBError):
	pass
	
class AniDBPacketCorruptedError(AniDBError):
	pass
