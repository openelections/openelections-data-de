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
        self.splitIntoChunks()
        print(f'Creating file for election on {self.date}')
        self.readInDistricts()
        self.process()

    def readIn(self):
        with open(self.inputFilePath, "r") as text_file:
            self.raw = text_file.read().splitlines()

    def readInDistricts(self):
        districtsFile = None
        
        if self.date > "20120424" and self.date <= "20221108":
            districtsFile = "election_districts_2012-2022.csv"
        elif self.date > "20021105" and self.date <= "20120424":
            districtsFile = "election_districts_2002-2012.csv"

        print(f"Using ED file {districtsFile}")

        if districtsFile:
            with open(districtsFile, "rU") as lookup_file:
                for row in csv.DictReader(lookup_file):
                    self.district_lookup[row['election_district']] = row['county']
        else:
            self.district_lookup = {}

    def splitIntoChunks(self):
        lastchunkstart = None
        self.chunks = []

        for i, row in enumerate(self.raw):
            # Does this line have the election type and date?
            if not self.date:
                m = re.match(r"\s*(\d\d\/\d\d\/\d\d)\s+(Presidential )?(\w+) ?;", row)
                if m:
                    self.election_type = m.group(3).lower()
                    self.date = "20{}{}{}".format(m.group(1)[6:8], m.group(1)[0:2], m.group(1)[3:5])

            # New chunk begins: only one semicolon on a non-short line
            elif len(re.findall(';', row)) == 1 and len(row) > 5:
                # print(row)
                if lastchunkstart:
                    self.chunks.append(Chunk(self.raw[lastchunkstart:i]))

                lastchunkstart = i

        # After finishing, append the last chunk
        self.chunks.append(Chunk(self.raw[lastchunkstart:]))

    def process(self):
        for chunk in filter(lambda c: c.recognizedOffice == True, self.chunks):
            header = []
            lastED = None

            for i, line in enumerate(chunk.resultLines):
                line = [cell.strip() for cell in line.split(';')]
                # print(i, line)
                
                if line[0] == "District":
                    header = [] # Reset candidate header
                    nextLine = [c.strip() for c in chunk.resultLines[i+1].split(';')]

                    for j, cell in enumerate(line):
                        candidateName = cell.title()
                        if j <= len(nextLine) and candidateName and candidateName not in ['District', 'Total']:
                            header.append((candidateName, nextLine[j]))
                        else:
                            header.append(None)

                elif not line[0]:
                    pass # skip party and column header rows

                elif line[0] == "RD Tot":
                    # print("Skipping RD Tot line")
                    pass
                    # county = self.district_lookup[lastED]
                    # election_district = f"RD {lastED[3:5]} Total"

                else:
                    for j, candidate in enumerate(header):
                        if candidate:
                            if line[0] == "Cand Tot":
                                county = self.district_lookup[lastED]
                                election_district = "Total"
                            else:
                                try:
                                    county = self.district_lookup[line[0]]
                                    lastED = line[0]
                                except:
                                    print(f"ERROR: Can't find ED: {line[0]}")
                                election_district = line[0]

                            try:
                                def clean(str):
                                    return str.replace(',', '') or 0
                                                  # 'county election_district office district party candidate election_day absentee votes'
                                result = self.Result(county, election_district, chunk.office, chunk.district, candidate[1], candidate[0], clean(line[j]), clean(line[j+1]), clean(line[j+2]))
                                # print(result)
                                self.processed.append(result)
                            except:
                                print(f"ERROR: Failed adding result for {candidate} in ED-RD {line[0]}")


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

        self.text = text

    def identifyOfficeAndDistrict(self):
        office_district = self.rawOffice.split(' DISTRICT ')
        
        if len(office_district) > 1:
            self.office, self.district = office_district
        else:
            self.office = self.rawOffice
            self.district = None

        self.recognizedOffice = (self.office in DEParser.office_mapping)

        if self.recognizedOffice:
            self.office = DEParser.office_mapping[self.office]


    @property
    def resultLines(self):
        return self.text[1:]

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
