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
import csv
import sys
import os
import argparse
import collections

def main():
    args = parseArguments()

    parser = DEParser(args.inputFilePath, args.outDirPath)
    parser.writeOut()


class DEParser(object):
    office_mapping = {
        'PRESIDENT': 'President',
        'UNITED STATES SENATOR': 'U.S. Senate',
        'REPRESENTATIVE IN CONGRESS': 'U.S. House',
        'GOVERNOR': 'Governor',
        'LIEUTENANT GOVERNOR': 'Lieutenant Governor',
        'ATTORNEY GENERAL': 'Attorney General',
        'STATE SENATOR': 'State Senate',
        'STATE REPRESENTATIVE': 'State Assembly'
    }

    def __init__(self, inputFilePath, outDirPath):
        self.inputFilePath = inputFilePath
        self.date = None
        self.outDirPath = outDirPath
        self.processed = []
        self.district_lookup = {}
        self.raw = []
        self.chunks = []
        self.election_type = None
        self.Chunk = collections.namedtuple('Chunk', 'office text')
        self.Result = collections.namedtuple('Result', 'county election_district office district party candidate election_day absentee votes')

        self.readIn()
        self.process()
        self.splitIntoChunks()
        self.readInDistricts() # Requires self.year to have been set during chunking
        self.process()

    def readIn(self):
        with open(self.inputFilePath, "r") as text_file:
            self.raw = text_file.read().splitlines()

    def readInDistricts(self):
        year = int(self.date[0:4])
        if year >= 2012 and year < 2022:
            districtsFile = "election_districts_2012-2022.csv"
        elif year >= 2002 and year < 2012:
            districtsFile = "election_districts_2002-2012.csv"

        with open(districtsFile, "rU") as lookup_file:
            for row in csv.DictReader(lookup_file):
                self.district_lookup[row['election_district']] = row['county']

    def splitIntoChunks(self):
        lastchunkstart = None
        self.chunks = []

        for i, row in enumerate(self.raw):
            # Does this line have the election type and date?
            m = re.match(r"^(\d\d\/\d\d\/\d\d) (Presidential )?(\w+) ;", row)
            if m:
                self.election_type = m.group(3).lower()
                self.date = "20{}{}{}".format(m.group(1)[6:8], m.group(1)[0:2], m.group(1)[3:5])

            elif row == ';':
                if lastchunkstart:
                    self.chunks.append(Chunk(self.raw[lastchunkstart:i-1]))

                lastchunkstart = i-1

        # After finishing, append the last chunk
        self.chunks.append(Chunk(self.raw[lastchunkstart:i]))

    def process(self):
        for chunk in filter(lambda c: c.recognizedOffice == True, self.chunks):
            header = []
            lastED = None

            for i, line in enumerate(chunk.resultLines):
                line = [c.strip() for c in line.split(';')]

                if line[0] == "District":
                    header = [] # Reset candidate header
                    nextLine = chunk.resultLines[i+1].split(';')

                    for j, cell in enumerate(line):
                        candidateName = cell.title()
                        if j <= len(nextLine) and candidateName and candidateName not in ['District', 'Total']:
                            header.append((candidateName, nextLine[j]))
                        else:
                            header.append(None)

                elif not line[0].strip():
                    pass # skip party and column header rows
                else:
                    for j, candidate in enumerate(header):
                        if candidate:
                            if line[0] == "RD Tot":
                                pass
                                # county = self.district_lookup[lastED]
                                # election_district = f"RD {lastED[3:5]} Total"
                            elif line[0] == "Cand Tot":
                                county = self.district_lookup[lastED]
                                election_district = "Total"
                            else:
                                lastED = line[0]
                                county = self.district_lookup[line[0]]
                                election_district = line[0]
                                                            # 'county election_district office district party candidate election_day absentee votes'
                            self.processed.append(self.Result(county, election_district, chunk.office, chunk.district, candidate[1], candidate[0], line[j], line[j+1], line[j+2]))


    def writeOut(self):
        filename = f"{self.date}__de__{self.election_type}__precinct.csv"
        with open(os.path.join(self.outDirPath, filename), 'w') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(self.Result._fields)

            for result in self.processed:
                writer.writerow(list(result))

class Chunk(object):
    def __init__(self, text):
        self.rawOffice = text[0].strip(';')
        self.office = None
        self.identifyOfficeAndDistrict()
        # self._candidates = None

        self.text = text

    def identifyOfficeAndDistrict(self):
        office_district = self.rawOffice.split(' DISTRICT ')
        if len(office_district) > 1:
            self.office, self.district = office_district
        else:
            self.district = None

        self.recognizedOffice = (self.office in DEParser.office_mapping)

        if self.recognizedOffice:
            self.office = DEParser.office_mapping[self.office]


    @property
    def resultLines(self):
        return self.text[2:]

def parseArguments():
    parser = argparse.ArgumentParser(description='Parse Delaware vote files into OpenElections format')
    parser.add_argument('inputFilePath', type=str,
                        help='path to the Delaware CSV file for a given election')
    parser.add_argument('outDirPath', type=str,
                        help='path to output the CSV file to')


    return parser.parse_args()


# Default function is main()
if __name__ == '__main__':
    main()
