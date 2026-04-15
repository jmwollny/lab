# # 🧛 GraphQL tutorial - Parts 1 and 2

A three part tutorial to get you up and running with GraphQL querying basics using a dataset of classic Hammer Studios films. [View the full list of 157 films here](./films.md). Part 2 will introduce ways of mutating the data in order to add, update and delete films.

You can find the tutorial blog posts here:
- Part 1 - introduction to GraphQL and how to query data - https://tapir.me.uk/?p=469
- Part 2 - how to add, update and remove data - https://tapir.me.uk/?p=503

## 🛠️ Setup your environment

First, clone the lab repository and navigate to the tutorial directory:

```bash
git clone https://github.com/jmwollny/lab.git
cd lab/graphql-tutorial
npm install
```

🚀 Start the Apollo Server

```bash
node index.js
```

```bash
🚀 Server ready at http://localhost:4000/
```

## 🔍 How to Query
You can interact with the API using the Apollo Sandbox by visiting http://localhost:4000/ in your browser, or use the cURL commands below from your terminal.

1. Fetch All Film Titles
```bash
curl --request POST \
  --url http://localhost:4000/ \
  --header 'Content-Type: application/json' \
  --data '{"query":"query { films { title year } }"}'
```

2. Search for a Specific Film

```bash
curl --request POST \
  --url http://localhost:4000/ \
  --header 'Content-Type: application/json' \
  --data '{"query":"query { films(searchTerm: \"Dracula\") { title year watched } }"}'
```

3. Filter by Year (Using Variables)

This demonstrates the best practice of separating the query from the data.

```bash
curl --request POST \
  --url http://localhost:4000/ \
  --header 'Content-Type: application/json' \
  --data '{
    "query": "query GetFilmsByYear($year: Int) { films(year: $year) { title } }",
    "variables": { "year": 1957 }
  }'
```
