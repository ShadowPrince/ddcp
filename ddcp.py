#!/usr/bin/env python2
# coding: utf8
# ddcp.py

from pbar import ProgressBar
from optparse import OptionParser
from pipes import quote
import os
import re
import sys
import time

"""
Settings
Some available trough CLI
"""
DEFAULT_BS = '1M'
DEFAULT_TIME_DELAY = 0.1
BAR_CHAR_FULL = '▣'
BAR_CHAR_EMPTY = '□'
BAR_WIDTH = None
BAR_COLOR = 'blue'
####
VERSION = 0.109

"""
Class for file

Run's dd process, prepares directories for it
"""
class DDTaskFile:
    def __init__(self, cmdo, **kwargs):
        for name, value in kwargs.items():
            self.__dict__[name] = value
        self.speed = 0
        self.cmdo = cmdo

    """
    Get filename
    """
    def file(self):
        return os.path.split(self.to_path)[1];

    """
    Run dd process
    """
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

    """
    Prepare directories for file
    """
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
            
    """
    Main function, that starts the copying
    """
    def run(self):
        if self.cmdo.test:
            self.speed = 'TEST_RUN'
            return
        self.prepare_directory()
        self.run_process()
        
        result = ''
        while not result.strip():
            try:
                result = open('/tmp/ddres').read()
            except IOError, e:
                if e.errno == 2:
                    exit('dd process don`t run correctly!')
                else:
                    raise e

        os.remove('/tmp/ddres')
        time.sleep(float(self.cmdo.time_delay))
        try:
            self.speed = result.split('\n')[2].split(' ')[-2:]
        except IndexError, e:
            print result
            exit('dd result not correct!')

    """
    String representation for -v(erbose) output
    """
    def __unicode__(self):
        return 'Task (from_path={from_path}, to_path={to_path})'.format(
            from_path=self.from_path,
            to_path=self.to_path,
        )


"""
Class for task
"""
class DDTask:
    def __init__(self, cmdo, paths):
        path_to = paths.pop()
        if path_to[-1] == '/':
            self.path_to = os.path.abspath(path_to) + '/'
        else:
            self.path_to = os.path.abspath(path_to)

        self.path_from = []
        for p in paths:
            self.path_from.append(os.path.abspath(p))

        self.cmdo = cmdo

    """
    Count files
    """
    def count(self):
        return len(self.flist)

    """
    Is destination path should be directory
    """
    def is_dest_dir(self): 
        return (
            os.path.isdir(self.path_to) 
            or 
            self.path_to[-1] == '/'
            or 
            len(self.path_from) > 1
        )
        
    """
    Prepare list of DDTaskFile's for basepath
    """
    def prepare_list(self, basepath):
        fl = complete_file_list(basepath)
        for path in fl:
            if self.is_dest_dir() or os.path.isdir(basepath):
                if os.path.isfile(basepath):
                    f = os.path.split(basepath)[-1]
                    to_path = os.path.join(
                        path.replace(basepath, self.path_to), f 
                    )
                else:
                    to_path = os.path.join(
                        path.replace(basepath, self.path_to)
                    )
            else:
                to_path = self.path_to 

            self.flist.append( DDTaskFile(
                self.cmdo,
                from_path=path, 
                to_path=to_path, 
                base_path=path.replace(path, '')
            ) )

    """
    Prepare list's for all arguments
    """
    def prepare_lists(self):
        self.from_list = []
        self.to_list = []
        self.flist = []
        
        for p in self.path_from:
            self.prepare_list(p)

    """
    Main function, runs task
    """
    def run(self, output):
        self.prepare_lists()
        i = 0
        for f in self.flist:
            output.put(task=self, counter=i, state='ft_started', f=f)
            f.run()
            output.put(task=self, counter=i, state='ft_finished', f=f)
            i += 1
        output.finished(self)


"""
Class for output
"""
class DDOutput:
    def __init__(self, cmdo):
        self.pbar = ProgressBar(BAR_COLOR, block=BAR_CHAR_FULL, empty=BAR_CHAR_EMPTY, width=BAR_WIDTH)
        self.cmdo = cmdo
        self.tmp = {}
        self.tmp['speed'] = ['', '']
    
    """
    Update progress
    """
    def put(self, **kwargs):
        if kwargs.get('f') and kwargs.get('state') == 'ft_finished':
            self.tmp['speed'] = kwargs.get('f').speed

        if self.cmdo.quiet:
            pass
        elif self.cmdo.verbose:
            self.put_verbose(*kwargs.values())
        else:
            if self.cmdo.detailed:
                self.put_bar_extended(*kwargs.values())
            else:
                self.put_bar(*kwargs.values())

    """
    Print -v(erbose) 
    """
    def put_verbose(self, state, task, instance, counter):
        print '{c}/{ca} {state} \'{from_path}\' \'{to_path}\' {speed}'.format(
            c=counter+1,
            ca=task.count(),
            state=state,
            from_path=instance.from_path,
            to_path=instance.to_path,
            speed=''.join(self.tmp['speed'])
        )

    """
    Print bar
    """
    def put_bar(self, state, task, instance, counter):
        counter = counter+(state == 'ft_finished' and 1 or 0)
        percent = int(float(counter)/task.count()*100)

        self.pbar.render(percent, '100%\n[{c}/{ca}] {state} {f}'.format(
            c=counter,
            ca=task.count(),
            f=instance.file(),
            state=(state == 'ft_finished' and 'Finished' or 'Copying')
        ))

    """
    Print -d(etailed) bar
    """
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

    """
    Called when task finished, sends notify 
    """
    def finished(self, task):
        if not self.cmdo.quiet:
            os.system('notify-send %s' % quote('ddcp finished task (%s)' % task.count()))


"""
Get complete files list of a path
"""
def complete_file_list(path):
    if os.path.isfile(path):
        return [path]

    paths = [] 
    for p, d, files in os.walk(path, followlinks=1):
        for f in files:
            paths.append(os.path.join(p, f))

    return paths 
    
"""
Make and return optparser
"""
def get_optparser():
    parser = OptionParser(epilog='version %s, http://github.com/shadowprince/ddcp/' % VERSION)
    parser.set_usage('ddcp SOURCE... DESTINATION')
    parser.add_option('-b', '--block-size', 
            default=DEFAULT_BS, 
            help='block size for dd\'s bs, default = %s' % DEFAULT_BS
            )

    parser.add_option('-q', '--quiet', 
            action='store_true', 
            help='dont print progress to stdout default = false'
            )
    parser.add_option('-d', '--detailed', 
            action='store_true', 
            help='detailed output (with bar), default = false'
            )
    parser.add_option('-v', '--verbose', 
            action='store_true', 
            help='print system messages instead of progress bar, default = false'
            )

    parser.add_option('-t', '--time-delay', 
            help='time delay between dd sessions, default = %s' % DEFAULT_TIME_DELAY, 
            default=DEFAULT_TIME_DELAY
            )

    parser.add_option('', '--test', 
            help='dont run dd command, default = false', action='store_true'
            )
    parser.add_option('', '--dd', 
            help='various dd arguments added to execution string, default = blank', 
            default=''
            )

    return parser


if __name__ == '__main__':
    parser = get_optparser()
    (opt, args) = parser.parse_args()
    if len(args) == 0:
        parser.print_help()
        exit(0)

    out = DDOutput(opt)
    task = DDTask(
        opt,
        args,
    )
    task.run(out)
