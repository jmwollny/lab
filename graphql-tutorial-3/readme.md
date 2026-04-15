# 🧛 GraphQL tutorial - Part 3 - persisting data using MongbDB

A tutorial to show how to persist the film list in a database.

You can find the tutorial blog posts for parts 1 and 2 here:
- Part 1 - introduction to GraphQL and how to query data - https://tapir.me.uk/?p=469
- Part 2 - how to add, update and remove data - https://tapir.me.uk/?p=503

## 🛠️ Setup your environment

First, clone the lab repository and navigate to the tutorial directory:

```bash
git clone https://github.com/jmwollny/lab.git
cd lab/graphql-tutorial-3
```
### Install MongoDB
Refer to the blog post for details - https://tapir.me.uk/?p=511

### Install mongoose
```bash
npm install mongoose
```

🚀 Start the Apollo Server

```bash
node index.js
```

```bash
🚀 Server ready at http://localhost:4000/
```

Once you have your MongoDB server running you can seed your database by running
```bash
node seed.js
```