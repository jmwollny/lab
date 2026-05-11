# Countdown timer server
To start the server run `node index.js`

Create the timers - `sh ./scripts/create-timers.sh`

## sample CURL requests

### Create a timer
```bash
curl -X POST -H "Content-Type: application/json" -d "{\"name\": \"Holiday\", \"date\": \"2026-12-01:00:00\", \"colour\": \"fuchsia\"}" http://localhost:3000/api/timer
```
### Update a timer
```bash
curl -X PUT -H "Content-Type: application/json" -d "{\"name\": \"Snowdon trip\", \"date\": \"2025-01-01:00:00\", \"colour\": \"red\"}" http://localhost:3000/api/timer/1
```

### Delete a timer
```bash
curl -X DELETE -H "Content-Type: application/json" http://localhost:3000/api/timer/1
```

### Get timers
```bash
curl -X GET -H "Content-Type: application/json" http://localhost:3000/api/timers | jq '.'
```
