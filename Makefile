SHELL := /bin/bash

.PHONY: start stop logs health

start:
	@bash /Hackathon/zone_detection/scripts/start_backend.sh

stop:
	@bash /Hackathon/zone_detection/scripts/stop_backend.sh

logs:
	@tail -n 200 /Hackathon/zone_detection/backend/backend.log

health:
	@curl -fsS http://127.0.0.1:5000/healthz && echo || true


