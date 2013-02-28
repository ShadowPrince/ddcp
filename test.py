from optparse import OptionParser
from hashlib import md5
import unittest
import ddcp
import os
import shutil

class GeneralTest(unittest.TestCase):
    def get_args(self, line):
        (opt, args) = ddcp.get_optparser().parse_args(line)
        return (opt, args)

    def setUp(self):
        self.ddtask = {} 
        self.test = {
            'f2f': 'README test/_README',
            'f2d': 'README test/',
            'd2d': 'test test/_test',
        }
        for name, x in self.test.items():
            op = x.split(' ')
            op.append('-q')
            (opt, args) = self.get_args(op) 
            self.ddtask[name] = (ddcp.DDTask(
                opt, args
            ))
        self.ddout = ddcp.DDOutput(opt)

        shutil.rmtree('test')
        os.makedirs('test')
        with open('test/testfile', 'w') as f:
            f.write('313720d0bbd0b5d1822c203920d0bcd0b5d181d18fd186d0b5d0b2')

    def test_f2f(self):
        self.ddtask['f2f'].run(self.ddout)
        self.assertMD5(
            'README', 'test/_README',
        )

    def md5file(self, f):
        return md5(open(f).read()).hexdigest()

    def assertMD5(self, f1, f2):
        self.assertEqual(
            self.md5file(f1),
            self.md5file(f2),
        )

    def test_f2d(self):
        self.ddtask['f2d'].run(self.ddout)
        self.assertMD5(
            'README', 'test/README'
        )

    def test_d2d(self):
        os.makedirs('test/directory')
        with open('test/directory/file', 'w') as f:
            f.write('7361792068656c6c6f20746f206d79206c6974746c6520667269656e64')

        self.ddtask['d2d'].run(self.ddout)
        self.assertMD5(
            'test/directory/file', 'test/_test/directory/file'
        )

if __name__ == '__main__':
    unittest.main()
