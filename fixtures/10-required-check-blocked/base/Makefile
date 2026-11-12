test:
	python3 -m unittest discover -s tests -t . -v

contract:
	@test -n "$$PAYMENTS_SANDBOX_KEY" || { echo "contract: PAYMENTS_SANDBOX_KEY is not set (the payments team issues sandbox keys)"; exit 2; }
	python3 -m unittest discover -s contract -t . -v

.PHONY: test contract
