#!/usr/bin/env python2
# coding: utf8
from pbar import ProgressBar
from optparse import OptionParser
from pipes import quote
import os
import re
import sys
import time

DEFAULT_BS = '1M'
DEFAULT_COLOR = 'blue'
DEFAULT_TIME_DELAY = 0.1
BAR_CHAR_FULL = '▣'
BAR_CHAR_EMPTY = '□'

class DDTaskFile:
    def __init__(self, cmdo, **kwargs):
        for name, value in kwargs.items():
            self.__dict__[name] = value
        self.speed = 0
        self.cmdo = cmdo

    def file(self):
        return os.path.split(self.to_path)[1];

    def run_process(self):
        try:
            os.remove('/tmp/ddres')
        except OSError, e:
            if e.errno == 2:
                pass
            else:
                raise e
        cmd = 'dd if={from_path} of={to_path} bs={bs} {dd} &> /tmp/ddres'.format(
            from_path=quote(self.from_path),
            to_path=quote(self.to_path),
            bs=self.cmdo.block_size,
            dd=self.cmdo.dd,
        )

        os.system(cmd)

    def prepare_directory(self):
        try:
            os.makedirs(os.path.split(self.to_path)[0])
        except OSError, e:
            if e.errno == 13:
                exit('Permission denied on destination!')
            elif e.errno == 17:
                pass
            else:
                raise e
            

    def run(self):
        self.prepare_directory()
        self.run_process()
        
        result = ''
        while not result.strip():
            result = open('/tmp/ddres').read()

        time.sleep(float(self.cmdo.delay))
        self.speed = result.split('\n')[2].split(' ')[-2:]

    def __unicode__(self):
        return 'Task (from_path={from_path}, to_path={to_path})'.format(
            from_path=self.from_path,
            to_path=self.to_path,
        )

class DDTask:
    def __init__(self, cmdo, path_from, path_to):
        self.path_from = os.path.abspath(path_from)
        if path_to[-1] == '/':
            self.path_to = os.path.abspath(path_to) + '/'
        else:
            self.path_to = os.path.abspath(path_to) + '/'

        self.cmdo = cmdo
        self.prepare_lists()

    def count(self):
        return len(self.flist)

    def prepare_lists(self):
        self.from_list = []
        self.to_list = []
        self.flist = []
        for path, flist in complete_file_list(self.path_from).items():
            for f in flist:
                from_path = os.path.join(path, f)
                if os.path.isdir(self.path_to) or self.path_to[-1] == '/':
                    to_path = os.path.join(
                        path.replace(os.path.split(self.path_from)[0], self.path_to), f
                    )
                else:
                    to_path = os.path.join(
                        path.replace(os.path.split(self.path_from)[0], self.path_to)
                    )

                self.flist.append(DDTaskFile(
                    self.cmdo,
                    from_path=from_path, 
                    to_path=to_path, 
                    base_path=path.replace(self.path_from, '')
                ))

    def run(self, output):
        i = 0
        for f in self.flist:
            output.put(task=self, counter=i, state='ft_started', f=f)
            f.run()
            output.put(task=self, counter=i, state='ft_finished', f=f)
            i += 1

class DDOutput:
    def __init__(self, cmdo):
        if cmdo.pbar_width:
            width = int(self.cmdo.pbar_width)
        else:
            width = None
        self.pbar = ProgressBar(cmdo.pbar_color, block=BAR_CHAR_FULL, empty=BAR_CHAR_EMPTY, width=width)
        self.cmdo = cmdo
        self.tmp = {}
        self.tmp['speed'] = ['', '']
    
    def put(self, **kwargs):
        if kwargs.get('f') and kwargs.get('state') == 'ft_finished':
            self.tmp['speed'] = kwargs.get('f').speed

        if (not self.cmdo.quiet) and (not self.cmdo.verbose):
            if self.cmdo.detailed:
                self.put_bar_extended(*kwargs.values())
            else:
                self.put_bar(*kwargs.values())

        elif (not self.cmdo.quiet) and (self.cmdo.verbose):
            self.put_verbose(*kwargs.values())

    def put_verbose(self, state, task, instance, counter):
        print '{c}/{ca} {state} \'{from_path}\' \'{to_path}\' {speed}'.format(
            c=counter+1,
            ca=task.count(),
            state=state,
            from_path=instance.from_path,
            to_path=instance.to_path,
            speed=''.join(self.tmp['speed'])
        )

    def put_bar(self, state, task, instance, counter):
        counter = counter+(state == 'ft_finished' and 1 or 0)
        percent = int(float(counter)/task.count()*100)

        self.pbar.render(percent, '100%\n[{c}/{ca}] {state} {f}'.format(
            c=counter,
            ca=task.count(),
            f=instance.file(),
            state=(state == 'ft_finished' and 'Finished' or 'Copying')
        ))

    def put_bar_extended(self, state, task, instance, counter):
        counter = counter+(state == 'ft_finished' and 1 or 0)
        percent = int(float(counter)/task.count()*100)

        self.pbar.render(percent, '100%\n[{c}/{ca}] {speed} {state} {basepath}/{f}'.format(
            c=counter,
            ca=task.count(),
            f=instance.file(),
            state=(state == 'ft_finished' and 'Finished' or 'Copying'),
            basepath=instance.base_path,
            speed=''.join(self.tmp['speed']),
        ))

def complete_file_list(path):
    if os.path.isfile(path):
        f = os.path.split(path)
        return {f[0]: [f[1]]}

    files = {} 
    for p, d, f in os.walk(path, followlinks=1):
        files[p] = f

    return files
    

if __name__ == '__main__':
    parser = OptionParser(epilog='version 0.105, http://github.com/shadowprince/ddcp/')
    parser.set_usage('ddcp SOURCE DESTINATION')
    parser.add_option('-b', '--block-size', default=DEFAULT_BS, help='block size for dd\'s bs')
    parser.add_option('-q', '--quiet', action='store_true', help='dont print progress to stdout')
    parser.add_option('-d', '--detailed', action='store_true', help='detailed output (with bar)')
    parser.add_option('-v', '--verbose', action='store_true', help='print system messages instead of progress bar')
    parser.add_option('-w', '--pbar-width', help='progressbar width')
    parser.add_option('-c', '--pbar-color', help='progressbar color', default=DEFAULT_COLOR)
    parser.add_option('-l', '--delay', help='time delay between dd sessions', default=DEFAULT_TIME_DELAY)
    parser.add_option('', '--dd', help='various dd arguments added to execution string', default='')
    (opt, args) = parser.parse_args()
    if len(args) == 0:
        parser.print_help()
        exit(0)

    out = DDOutput(opt)
    task = DDTask(
        opt,
        args[0],
        args[1],
    )
    task.run(out)
