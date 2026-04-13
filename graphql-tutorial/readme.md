# Quick start

This is a quick tutorial to get to grips with the basics of graphql.

## Setup your environment
clone https://github.com/your-username/hammer-horror-graphql.git"
npm init -y
npm install apollo-server graphql

## Start the apollo server
node index.js
```bash
node index.js
🚀 Server ready at http://localhost:4000/
```

You can either go to the sandbox [here](http://localhost:4000/) or use curl commands from the terminal

### CURL commands
### All titles
curl --request POST \
  --url http://localhost:4000/ \
  --header 'Content-Type: application/json' \
  --data '{"query":"query { films { title year } }"}'

### Search for a film
curl --request POST \
  --url http://localhost:4000/ \
  --header 'Content-Type: application/json' \
  --data '{"query":"query { films(searchTerm: \"Dracula\") { title year watched } }"}'

### Filter by year using variables
curl --request POST \
  --url http://localhost:4000/ \
  --header 'Content-Type: application/json' \
  --data '{
    "query": "query GetFilmsByYear($year: Int) { films(year: $year) { title } }",
    "variables": { "year": 1957 }
  }'
