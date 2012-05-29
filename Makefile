all:
	true

clean:
	find gitcvs *_test -name \*.pyc | xargs --no-run-if-empty rm
	rm -f .coverage


unit:
	PYTHONPATH=. nosetests --with-coverage --cover-package gitcvs -s unit_test/

func:
	#PYTHONPATH=. nosetests --with-coverage --cover-package gitcvs -s func_test/

story:
	#PYTHONPATH=. nosetests --with-coverage --cover-package gitcvs -s story_test/

alltests:
	PYTHONPATH=. nosetests --with-coverage --cover-package gitcvs -s

tests: unit func story
