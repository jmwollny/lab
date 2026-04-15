const mongoose = require('mongoose');
const fs = require('fs');
// Import your Mongoose model
const Film = require('./models/Film'); 

const seedDatabase = async () => {
  try {
    // Connect to MongoDB
    await mongoose.connect('mongodb://127.0.0.1:27017/hammer_films');
    console.log("Connected to MongoDB for seeding...");

    // Read the JSON file
    const data = JSON.parse(fs.readFileSync('./films.json', 'utf-8'));

    // Clear existing films
    await Film.deleteMany({});
    console.log("Old records removed.");

    // Bulk insert the data
    await Film.insertMany(data);
    console.log(`${data.length} Hammer films successfully added to the database!`);

    // Close the connection
    process.exit();
  } catch (error) {
    console.error("Error seeding database:", error);
    process.exit(1);
  }
};

seedDatabase();