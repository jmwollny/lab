const mongoose = require('mongoose');

const filmSchema = new mongoose.Schema({
  title: { type: String, required: true },
  year: { type: Number, required: true },
  watched: { type: Boolean, default: false }
});

// Export the model so both index.js and seed.js can use it
module.exports = mongoose.model('Film', filmSchema);