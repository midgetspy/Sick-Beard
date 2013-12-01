import os, sys

import UnRAR2
from UnRAR2.rar_exceptions import *


def cleanup(dir='test'):
    for path, dirs, files in os.walk(dir):
        for fn in files:
            os.remove(os.path.join(path, fn))
        for dir in dirs:
            os.removedirs(os.path.join(path, dir))


# basic test
cleanup()
rarc = UnRAR2.RarFile('test.rar')
rarc.infolist()
assert rarc.comment == "This is a test."
for info in rarc.infoiter():
    saveinfo = info
    assert (str(info)=="""<RarInfo "test" in "test.rar">""")
    break
rarc.extract()
assert os.path.exists('test'+os.sep+'test.txt')
assert os.path.exists('test'+os.sep+'this.py')
del rarc
assert (str(saveinfo)=="""<RarInfo "test" in "[ARCHIVE_NO_LONGER_LOADED]">""")
cleanup()

# extract all the files in test.rar
cleanup()
UnRAR2.RarFile('test.rar').extract()
assert os.path.exists('test'+os.sep+'test.txt')
assert os.path.exists('test'+os.sep+'this.py')
cleanup()

# extract all the files in test.rar matching the wildcard *.txt
cleanup()
UnRAR2.RarFile('test.rar').extract('*.txt')
assert os.path.exists('test'+os.sep+'test.txt')
assert not os.path.exists('test'+os.sep+'this.py')
cleanup()


# check the name and size of each file, extracting small ones
cleanup()
archive = UnRAR2.RarFile('test.rar')
assert archive.comment == 'This is a test.'
archive.extract(lambda rarinfo: rarinfo.size <= 1024)
for rarinfo in archive.infoiter():
    if rarinfo.size <= 1024 and not rarinfo.isdir:
        assert rarinfo.size == os.stat(rarinfo.filename).st_size
assert file('test'+os.sep+'test.txt', 'rt').read() == 'This is only a test.'
assert not os.path.exists('test'+os.sep+'this.py')
cleanup()


# extract this.py, overriding it's destination
cleanup('test2')
archive = UnRAR2.RarFile('test.rar')
archive.extract('*.py', 'test2', False)
assert os.path.exists('test2'+os.sep+'this.py')
cleanup('test2')


# extract test.txt to memory
cleanup()
archive = UnRAR2.RarFile('test.rar')
entries = UnRAR2.RarFile('test.rar').read_files('*test.txt')
assert len(entries)==1
assert entries[0][0].filename.endswith('test.txt')
assert entries[0][1]=='This is only a test.'


# extract all the files in test.rar with overwriting
cleanup()
fo = open('test'+os.sep+'test.txt',"wt")
fo.write("blah")
fo.close()
UnRAR2.RarFile('test.rar').extract('*.txt')
assert open('test'+os.sep+'test.txt',"rt").read()!="blah"
cleanup()

# extract all the files in test.rar without overwriting
cleanup()
fo = open('test'+os.sep+'test.txt',"wt")
fo.write("blahblah")
fo.close()
UnRAR2.RarFile('test.rar').extract('*.txt', overwrite = False)
assert open('test'+os.sep+'test.txt',"rt").read()=="blahblah"
cleanup()

# list big file in an archive
list(UnRAR2.RarFile('test_nulls.rar').infoiter())

# extract files from an archive with protected files
cleanup()
rarc = UnRAR2.RarFile('test_protected_files.rar', password="protected")
rarc.extract()
assert os.path.exists('test'+os.sep+'top_secret_xxx_file.txt')
cleanup()
errored = False
try:
    UnRAR2.RarFile('test_protected_files.rar', password="proteqted").extract()
except IncorrectRARPassword:
    errored = True
assert not os.path.exists('test'+os.sep+'top_secret_xxx_file.txt')
assert errored
cleanup()

# extract files from an archive with protected headers
cleanup()
UnRAR2.RarFile('test_protected_headers.rar', password="secret").extract()
assert os.path.exists('test'+os.sep+'top_secret_xxx_file.txt')
cleanup()
errored = False
try:
    UnRAR2.RarFile('test_protected_headers.rar', password="seqret").extract()
except IncorrectRARPassword:
    errored = True
assert not os.path.exists('test'+os.sep+'top_secret_xxx_file.txt')
assert errored
cleanup()

# make sure docstring examples are working
import doctest
doctest.testmod(UnRAR2)

# update documentation
import pydoc
pydoc.writedoc(UnRAR2)

# cleanup
try:
    os.remove('__init__.pyc')
except:
    pass
