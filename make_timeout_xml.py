
def generate_xml(timeout_duration):
	return f'''<?xml version="1.0" encoding="utf-8"?>
	<testsuites>
	<testsuite name="pytest" errors="0" failures="1" skipped="0" tests="1" time="{timeout_duration}" timestamp="" hostname="">
	<testcase classname="CheckerTimedOut" time="{timeout_duration}">
	<failure message="the checker was unable to complete running your code because it took too long, presumably because of an infinite loop.  it was allowed to run for {timeout_duration} seconds before it was automatically killed" />
	</testcase>
	</testsuite>
	</testsuites>
	'''

import sys

filename = sys.argv[1]
timeout_duration = sys.argv[2]

with open(filename,'w') as f:
	f.write(generate_xml(timeout_duration))
