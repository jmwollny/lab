# Countdown timer
This application is the UI that uses the countdown-timer-server to read, display and update countdown timers. 

To get started pull this repo, then install the dependencies
```bash
npm install
```

Now pull the coundown-time-server repo and then:
```bash
npm install
up to date, audited 67 packages in 622ms
node index.js
Server listening on port 3000
```

I have provided some example scripts to create sample timers. These can be found in the `/scripts` directory. 
I suggest running the timer creation script
```bash
sh ./create-timers.sh
{"id":1,"name":"Leave Gamma","date":"2025-11-28:17:30","colour":"MediumOrchid"}{"id":2,"name":"Mia's birthday","date":"2026-01-18:00:00"}{"id":3,"name":"Jake's birthday","date":"2026-03-16:00:00"}{"id":4,"name":"Rowena's birthday","date":"2026-09-13:00:00","colour":"fuchsia"}%
```
You can check if this was successful by running
```bash
jonathanwollny@Jonathans-MacBook-Air-2 scripts % sh ./get-timers.sh
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   281  100   281    0     0  99539      0 --:--:-- --:--:-- --:--:-- 93666
[
  {
    "id": 1,
    "name": "Leave Gamma",
    "date": "2025-11-28:17:30",
    "colour": "MediumOrchid"
  },
  {
    "id": 2,
    "name": "Mia's birthday",
    "date": "2026-01-18:00:00"
  },
  {
    "id": 3,
    "name": "Jake's birthday",
    "date": "2026-03-16:00:00"
  },
  {
    "id": 4,
    "name": "Rowena's birthday",
    "date": "2026-09-13:00:00",
    "colour": "fuchsia"
  }
]
```

Once you have done this run the frontend app to display the timers.
```bash
cd countdown-timer
npm run dev
```
