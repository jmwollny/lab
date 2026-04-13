#!/bin/bash
curl -X PUT -H "Content-Type: application/json" -d "{\"name\": \"Snowdon trip\", \"date\": \"2025-01-01:00:00\", \"colour\": \"red\"}" http://localhost:3000/api/timer/1
