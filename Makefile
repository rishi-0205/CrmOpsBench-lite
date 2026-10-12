.PHONY: selftest oracle nop verify-results check summary run-agent

selftest:
	pytest

oracle:
	harbor run -p tasks/offboard-departed-employee -a oracle

nop:
	harbor run -p tasks/offboard-departed-employee -a nop

verify-results:
	python scripts/check_results.py --assert-baselines

check: selftest verify-results

summary:
	python scripts/check_results.py --output-md results/RESULTS.md

ATTEMPTS ?= 1

run-agent:
	harbor run -c job_config.yaml -k $(ATTEMPTS) -n 1 --ak max_turns=15

