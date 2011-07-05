
if __name__ == "__main__":
    import glob
    import unittest
    
    test_file_strings = [ x for x in glob.glob('*_tests.py') if x != __file__]
    module_strings = [str[0:len(str)-3] for str in test_file_strings]
    suites = [unittest.defaultTestLoader.loadTestsFromName(str) for str in module_strings]
    testSuite = unittest.TestSuite(suites)
    
    
    print "=================="
    print "STARTING - ALL TESTS"
    print "=================="
    print "this will include"
    for includedfiles in test_file_strings:
        print "- "+includedfiles
    
    
    text_runner = unittest.TextTestRunner().run(testSuite)
