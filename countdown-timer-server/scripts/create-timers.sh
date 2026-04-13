#!/bin/bash
curl -X POST -H "Content-Type: application/json" -d "{\"name\": \"Leave Gamma\", \"date\": \"2025-11-28:17:30\" ,\"colour\": \"MediumOrchid\"}" http://localhost:3000/api/timer
curl -X POST -H "Content-Type: application/json" -d "{\"name\": \"Mia's birthday\", \"date\": \"2026-01-18:00:00\"}" http://localhost:3000/api/timer
curl -X POST -H "Content-Type: application/json" -d "{\"name\": \"Jake's birthday\", \"date\": \"2026-03-16:00:00\"}" http://localhost:3000/api/timer
curl -X POST -H "Content-Type: application/json" -d "{\"name\": \"Rowena's birthday\", \"date\": \"2026-09-13:00:00\", \"colour\": \"fuchsia\"}" http://localhost:3000/api/timer