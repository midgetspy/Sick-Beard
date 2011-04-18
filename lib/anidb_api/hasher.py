import hashlib
# http://www.radicand.org/blog/orz/2010/2/21/edonkey2000-hash-in-python/
def get_file_hash(filePath):
    """ Returns the ed2k hash of a given file."""

    md4 = hashlib.new('md4').copy

    def gen(f):
        while True:
            x = f.read(9728000)
            if x: yield x
            else: return

    def md4_hash(data):
        m = md4()
        m.update(data)
        return m

    with open(filePath, 'rb') as f:
        a = gen(f)
        hashes = [md4_hash(data).digest() for data in a]
        if len(hashes) == 1:
            return hashes[0].encode("hex")
        else: return md4_hash(reduce(lambda a,d: a + d, hashes, "")).hexdigest()
        
        
def get_file_size(path):
    f = open(path)
    size = len(f.read())
    f.close()
    return size