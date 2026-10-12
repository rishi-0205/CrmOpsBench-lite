.PHONY: selftest oracle nop verify-results check run-agent

selftest:
	pytest

oracle:
	harbor run -p tasks/offboard-departed-employee -a oracle

nop:
	harbor run -p tasks/offboard-departed-employee -a nop

verify-results:
	python scripts/check_results.py --assert-baselines

check: selftest verify-results

run-agent:
	harbor run -c job_config.yaml
