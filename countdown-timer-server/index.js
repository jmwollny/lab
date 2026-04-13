const express = require('express');
const bodyParser = require('body-parser');

const app = express();
const port = 3000;
const data = new Map();
let id = 1;

// Get the next available ID
const getNextId = () => {
  let nextId = 1;
  if (data.size === 0) {
    return nextId;
  }

  Ids = Array.from(data.keys()).sort((a, b) => a - b);
  nextId = Ids[Ids.length - 1] + 1;
  return nextId;
};

app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header(
    'Access-Control-Allow-Headers',
    'Origin, X-Requested-With, Content-Type, Accept'
  );
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE');
  next();
});

app.use(bodyParser.json());

// Crud operations
// Create
app.post('/api/timer', (req, res) => {
  const receivedData = req.body;

  // Check if the expected data is present.
  if (receivedData && receivedData.date) {
    // Process the data (in this example, we just echo it back).
    const responseData = {
      id,
      name: receivedData.name,
      date: receivedData.date,
      colour: receivedData.colour,
    };
    data.set(id, responseData);

    res.status(201).json(responseData);
    id = getNextId();
  } else {
    // If the expected data is not present, send a 400 Bad Request
    // status code and an error message.  This tells the client
    // that the request was not formed correctly.
    res.status(400).json({
      error:
        'Invalid data format.  Expected date property. name and colour are optional.',
    });
  }
});

// Read
app.get('/api/timers', (req, res) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.send(Array.from(data.values()));
});

// Update
app.put('/api/timer/:id', (req, res) => {
  res.header('Access-Control-Allow-Origin', '*');
  const idInt = parseInt(req.params.id);
  if (data.has(idInt)) {
    const receivedData = req.body;
    const timer = data.get(idInt);
    timer.name = receivedData.name || timer.name;
    timer.date = receivedData.date || timer.date;
    timer.colour = receivedData.colour || timer.colour;
    data.set(idInt, timer);
    res.status(200).json(timer);
  } else {
    res.status(404).json({ error: `Update failed. Timer ${idInt} not found` });
  }
});


// Delete
app.delete('/api/timer/:id', (req, res) => {
  res.header('Access-Control-Allow-Origin', '*');
  const idInt = parseInt(req.params.id);
  if (data.has(idInt)) {
    data.delete(idInt);
    id = getNextId();
    res.status(204).json({ message: `Timer ${idInt} deleted successfully` });
  } else {
    res.status(404).json({ error: `Delete failed. Timer ${idInt} not found` });
  }
});

// Start the server and listen on the specified port.
app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});
