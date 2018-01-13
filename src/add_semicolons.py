#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

# The MIT License (MIT)
# Copyright (c) 2018 OpenElections
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all 
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
# SOFTWARE.

import re
import argparse

def main():
    args = parseArguments()

    processor = OldDEProcessor(args.inputFilePath)

def parseArguments():
    parser = argparse.ArgumentParser(description='Add semicolons to old Deleware election results text files')
    parser.add_argument('inputFilePath', type=str,
                        help='path to an old Delaware election results text file')

    return parser.parse_args()

class OldDEProcessor(object):
    def __init__(self, path):
    	self.path = path

    	self.process()

    def process(self):
    	with open(self.path, 'r') as file:
    		lines = file.readlines()
    		for index, line in enumerate(lines):
    			chars = list(line.rstrip())

    			if len(chars):
	    			# ED-RD results lines
	    			if re.match('\d', chars[0]) or re.match('(RD Tot|Cand Tot)', line):
	    				# columns
	    				cols = line[10:].split() # split columns after the first one
	    				cols.insert(0, line[0:10]) # re-add the first column, which may contain a space
	    				chars = list(';'.join(cols))

	    			elif re.match('\s+M/C', line):
	    				for i in [10, 17, 25, 32, 39, 45, 52, 59, 65, 72, 79, 86, 92, 99]:
	    					if len(chars) > i and chars[i] == ' ':
	    						chars[i] = ';'

	    			# Candidate and Party lines
	    			elif re.match('District', line) or (index > 0 and re.match('District', lines[index-1])):
	    				for i in [10, 18, 31, 51, 71, 91]:
	    					if len(chars) > i:
	    						if i <= 18:
	    							chars[i] = ';'
		    					else:
		    						chars[i:i+3] = list(';;;')


    			print(''.join(chars)+';')



# Default function is main()
if __name__ == '__main__':
    main()
