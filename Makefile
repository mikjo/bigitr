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
