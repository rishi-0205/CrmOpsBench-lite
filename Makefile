.PHONY: selftest oracle nop verify-results check

selftest:
	pytest

oracle:
	harbor run -p tasks/offboard-departed-employee -a oracle

nop:
	harbor run -p tasks/offboard-departed-employee -a nop

verify-results:
	python scripts/check_results.py --assert-baselines

check: selftest verify-results
