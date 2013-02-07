#!/usr/bin/env python

#   Copyright 2013 Red Hat, Inc.
#
#   This is free software: you can redistribute it and/or modify it
#   under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful, but
#   WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#   General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see
#   <http://www.gnu.org/licenses/>.

import sys
import xml.etree.ElementTree as ET

from firehose.report import Message, Function, Point, \
    File, Location, Generator, Metadata, Analysis, Issue, Notes, Failure, \
    CustomFields

# Parser for output from cppcheck:
#   http://sourceforge.net/apps/mediawiki/cppcheck/index.php?title=Main_Page
# specifically, version 2 of its XML format as generated by:
#   cppcheck PATH_TO_SOURCES --xml --xml-version=2

def parse_file(fileobj, sut=None, file_=None, stats=None):
    tree = ET.parse(fileobj)
    root = tree.getroot()
    node_cppcheck = root.find('cppcheck')
    version = node_cppcheck.get('version')
    node_errors = root.find('errors')

    generator = Generator(name='cppcheck',
                          version=node_cppcheck.get('version'))
    metadata = Metadata(generator, sut, file_, stats)
    analysis = Analysis(metadata, [])

    for node_error in node_errors.findall('error'):
        # e.g.:
        # <error id="nullPointer" severity="error" msg="Possible null pointer dereference: end - otherwise it is redundant to check it against null." verbose="Possible null pointer dereference: end - otherwise it is redundant to check it against null.">
        #  <location file="python-ethtool/ethtool.c" line="139"/>
        #  <location file="python-ethtool/ethtool.c" line="141"/>
        # </error>
        testid = node_error.get('id')
        str_msg = node_error.get('msg')
        str_verbose = node_error.get('verbose')
        message = Message(text=str_msg)
        if str_verbose != str_msg:
            notes = Notes(str_verbose)
        else:
            notes = None

        location_nodes = list(node_error.findall('location'))
        for node_location in location_nodes:
            location=Location(file=File(node_location.get('file'), None),

                              # FIXME: doesn't tell us function name
                              # TODO: can we patch this upstream?
                              function=None,

                              # doesn't emit column
                              point=Point(int(node_location.get('line')), 0)) # FIXME: bogus column
            issue = Issue(None, testid, location, message, notes, None,
                          severity=node_error.get('severity'))
            analysis.results.append(issue)

        if not location_nodes:
            customfields=CustomFields()
            if str_verbose != str_msg:
                customfields['verbose'] = str_verbose
            failure = Failure(failureid=testid,
                              location=None,
                              message=message,
                              customfields=customfields)
            analysis.results.append(failure)

    return analysis

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "provide a build log file path as the only argument"
    else:
        with open(sys.argv[1]) as data_file:
            analysis = parse_file(data_file)
            analysis.to_xml().write(sys.stdout)
