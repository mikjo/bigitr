#
# Copyright 2012 SAS Institute
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

all:
	true

clean:
	find gitcvs *_test -name \*.pyc | xargs --no-run-if-empty rm
	rm -f .coverage

# override for automated test runs that should not drop into
# the debugger when the code has an error
PDB=--pdb -s
COV=--with-coverage --cover-package gitcvs

unit:
	PYTHONPATH=. nosetests $(PDB) $(COV) unit_test/

func:
	#PYTHONPATH=. nosetests $(PDB) $(COV) func_test/

story:
	PYTHONPATH=. BASEDIR=$$(pwd) nosetests $(PDB) $(COV) story_test/

alltests:
	PYTHONPATH=. BASEDIR=$$(pwd) nosetests $(PDB) $(COV)

tests: unit func story
