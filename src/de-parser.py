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
        self.district_lookup = []
        self.raw = []
        self.election_type = None

        self.readIn()
        self.process()

    def readIn(self):
        with open("election_districts_2012.csv", "rU") as lookup_file:
            self.district_lookup = [row for row in csv.reader(lookup_file)]

        with open(self.inputFilePath, "r") as text_file:
            self.raw = text_file.read().splitlines()

    def process(self):
        # split into chunks for each table
        # new table begins with line where many characters are letters and all characters are uppercase
        lastchunkstart = 0
        chunked = []
        for i, row in enumerate(self.raw):
            # Does this line have the election type and date?
            m = re.match(r"^(\d\d\/\d\d\/\d\d) (\w+)", row)
            if m:
                self.election_type = m.group(2).lower()
                self.date = "20{}{}{}".format(m.group(1)[6:8], m.group(1)[0:2], m.group(1)[3:5])

            # no non-uppercase, first character is an uppercase letter, proportion of letters is high
            elif (row == row.upper() and row[0].isupper() and
                sum(1 for c in re.sub(r'\s+', '', row) if c.isupper()) / float(len(re.sub(r'\s+', '', row))) > .8):
                # skip the file headers in the first chunk
                if lastchunkstart > 0:
                    chunked.append(self.raw[lastchunkstart:i])
                lastchunkstart = i

        chunked.append(self.raw[lastchunkstart:i])

        # drop chunks for local offices, keep only:
        # [PRESIDENT;', 'UNITED STATES SENATOR;', 'REPRESENTATIVE IN CONGRESS;',
        # 'GOVERNOR;', ''LIEUTENANT GOVERNOR;', 'ATTORNEY GENERAL;',
        # 'STATE REPRESENTATIVE DISTRICT #;', 'STATE SENATOR DISTRICT #;']
        filtered = []
        for i in range(0, len(chunked)):
            if re.match(r"^PRESIDENT$", chunked[i][0].strip().replace(';','')):
                filtered.append(chunked[i])
            if re.match(r"^UNITED STATES SENATOR$", chunked[i][0].strip().replace(';','')):
                filtered.append(chunked[i])
            if re.match(r"^REPRESENTATIVE IN CONGRESS$", chunked[i][0].strip().replace(';','')):
                filtered.append(chunked[i])
            if re.match(r"^GOVERNOR$", chunked[i][0].strip().replace(';','')):
                filtered.append(chunked[i])
            if re.match(r"^LIEUTENANT GOVERNOR$", chunked[i][0].strip().replace(';','')):
                filtered.append(chunked[i])
            if re.match(r"^ATTORNEY GENERAL$", chunked[i][0].strip().replace(';','')):
                filtered.append(chunked[i])
            if re.match(r"^STATE REPRESENTATIVE DISTRICT \d+$", chunked[i][0].strip().replace(';','')):
                filtered.append(chunked[i])
            if re.match(r"^STATE SENATOR DISTRICT \d+$", chunked[i][0].strip().replace(';','')):
                filtered.append(chunked[i])

        # process chunks
        for i in range(0,len(filtered)):
            tb = filtered[i]
            # parse second/third line to create lists of candidates & parties
            candidates = [j for j in tb[2].split(';') if j != '' and j != ' ' and j != 'District' and j != 'Total']
            parties = [j for j in tb[3].split(';') if j != '' and j != ' ']
            if (len(candidates) != len(parties)):
                print("ERROR: Number of candidates not the same as number of parties")
            # parse first line to identify office & district
            office_district_split = tb[0].find('DISTRICT')
            office = DEParser.office_mapping[tb[0][0:office_district_split].strip()]  # relies on -1 removing ; at end
            if office_district_split == -1:
                district = ''
            else:
                district = tb[0][office_district_split + 9 : -1] # relies on -1 removing ; at end
            # individual election districts start on row 4 and begin with a ##-## value
            # each set of election districts is followed by a rep-district total
            # after all election districts for a race, the last one is followed by a candidate total
            # failed to parse candidate totals because the data quality is too bad:
            # * last character of the line is routinely cut off
            # * numbers within a line overlap
            for j in range(4,len(tb)):
                line = tb[j].split(';')
                if re.match(r"^\d\d-\d\d$", line[0]):
                    for k in range(0, len(candidates)):
                        # election_district, office, district, party, candidate, votes
                        county = [d[0] for d in self.district_lookup if d[1] == line[0]][0]
                        self.processed.append([county, line[0], office, district, parties[k], candidates[k], re.sub(r",", "", line[3*k+4].strip())])
                    self.processed.append([county, line[0], office, district, '', 'Total', re.sub(r",", "", line[1].strip())])
                elif re.match(r"^RD Tot$", line[0]):
                    pass
                elif re.match(r"^Cand Tot$", line[0]):
                    pass
                    # if 3*k+4 > len(line) - 2:
                    #     print("ERROR: Overlapping numbers in Cand Tot line of filtered[" + str(i) + "].")
                    # else:
                    #     for k in range(0, len(candidates)):
                    #         print(i)
                    #         self.processed.append(['Total', office, district, parties[k], candidates[k], line[3*k+4]])
                else:
                    print("ERROR: Line in unknown format.")

    def writeOut(self):
        with open(os.path.join(self.outDirPath, f"{self.date}__de__{self.election_type}__precinct.csv"), 'w') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(('county', 'election_district', 'office', 'district', 'party', 'candidate', 'votes'))
            writer.writerows(self.processed)

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
