import re
import csv
import sys

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

text_file = open("stwres.txt", "r")
raw = text_file.read().splitlines()
text_file.close()

# split into chunks for each table
# new table begins with line where many characters are letters and all characters are uppercase
lastchunkstart = 0
chunked = []
for i in range(0, len(raw)):
    # no non-uppercase, first character is an uppercase letter, proportion of letters is high
    if (raw[i] == raw[i].upper() and raw[i][0].isupper() and
        sum(1 for c in re.sub(r'\s+', '', raw[i]) if c.isupper()) / float(len(re.sub(r'\s+', '', raw[i]))) > .8):
        # skip the file headers in the first chunk
        if lastchunkstart > 0:
            chunked.append(raw[lastchunkstart:i])
        lastchunkstart = i
    i = i + 1
chunked.append(raw[lastchunkstart:i])

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
processed = []
for i in range(0,len(filtered)):
    tb = filtered[i]
    # parse second/third line to create lists of candidates & parties
    candidates = [j for j in tb[1].split(';') if j != '' and j != ' ' and j != 'District' and j != 'Total']
    parties = [j for j in tb[2].split(';') if j != '' and j != ' ']
    if (len(candidates) != len(parties)):
        print "ERROR: Number of candidates not the same as number of parties"
    # parse first line to identify office & district
    office_district_split = tb[0].find('DISTRICT')
    office = office_mapping[tb[0][0:office_district_split].strip()]  # relies on -1 removing ; at end
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
                processed.append([line[0], office, district, parties[k], candidates[k], re.sub(r",", "", line[3*k+4].strip())])            
            processed.append([line[0], office, district, '', 'Total', re.sub(r",", "", line[1].strip())]) 
        elif re.match(r"^RD Tot$", line[0]):
            pass
        elif re.match(r"^Cand Tot$", line[0]):
            pass
            # if 3*k+4 > len(line) - 2:
            #     print "ERROR: Overlapping numbers in Cand Tot line of filtered[" + str(i) + "]."
            # else:
            #     for k in range(0, len(candidates)):
            #         print i
            #         processed.append(['Total', office, district, parties[k], candidates[k], line[3*k+4]]) 
        else:
            print "ERROR: Line in unknown format."

f = open('20161108__de__general__precinct.csv', 'wt')
try:
    writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow( ('election_district', 'office', 'district', 'party', 'candidate', 'votes') )
    for i in range(0, len(processed)):
        writer.writerow( processed[i] )
finally:
    f.close()
