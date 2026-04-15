const { ApolloServer, gql } = require('apollo-server');
const mongoose = require('mongoose');
const FilmModel = require('./models/Film');
// The Schema (TypeDefs)
const typeDefs = gql`
  type Film {
    id: ID!
    title: String!
    year: Int
    watched: Boolean
  }

  input FilmFilter {
    year_gte: Int
    year_lte: Int
  }

  type Query {
    # Return a list of films, optionally filtered by watched status, year, or search term in the title
    films(
      watched: Boolean
      year: Int
      searchTerm: String
      where: FilmFilter
    ): [Film]
    film(id: ID!): Film
  }

  input CreateFilmInput {
    title: String!
    year: Int!
    watched: Boolean!
  }

  type Mutation {
    # Add a film to our collection
    addFilm(input: CreateFilmInput!): Film

    # Toggle the watched status of a film
    updateWatched(id: ID!, watched: Boolean!): Film

    # Delete a film from our collection
    deleteFilm(id: ID!): [Film]
  }
`;

// Connect to your local or Atlas MongoDB instance
mongoose.connect('mongodb://localhost:27017/hammer_films', {
  useNewUrlParser: true,
  useUnifiedTopology: true,
});

const db = mongoose.connection;
db.on('error', console.error.bind(console, 'connection error:'));
db.once('open', () => console.log('Connected to MongoDB!'));

// The Resolvers
const resolvers = {
  Query: {
    films: async (parent, args) => {
      // 1. Build a dynamic query object
      let query = {};

      // Watch filter
      if (args.watched !== undefined) {
        query.watched = args.watched;
      }

      // Year filter (Exact match)
      if (args.year) {
        query.year = args.year;
      }

      // Date range filter (using MongoDB operators $gte and $lte)
      if (args.where) {
        query.year = query.year || {}; // Initialize year object if it doesn't exist
        if (args.where.year_gte) {
          query.year.$gte = args.where.year_gte;
        }
        if (args.where.year_lte) {
          query.year.$lte = args.where.year_lte;
        }
      }

      // Search filter (using Regex for case-insensitive partial match)
      if (args.searchTerm) {
        query.title = { $regex: args.searchTerm, $options: 'i' };
      }

      // Execute the query against the database
      return await FilmModel.find(query);
    },

    // Find by ID - Mongoose maps GraphQL 'id' to MongoDB '_id' automatically
    film: async (parent, args) => await FilmModel.findById(args.id),
  },

  Mutation: {
    addFilm: async (parent, { input }) => {
      // Create a new instance and save it
      const newFilm = new FilmModel(input);
      return await newFilm.save();
    },

    updateWatched: async (parent, { id, watched }) => {
      const updatedFilm = await FilmModel.findByIdAndUpdate(
        id,
        { watched },
        { new: true }, // This flag returns the record *after* it was updated
      );

      if (!updatedFilm) {
        throw new Error('Film not found');
      }

      return updatedFilm;
    },

    deleteFilm: async (parent, { id }) => {
      const deleted = await FilmModel.findByIdAndDelete(id);
      if (!deleted) {
        throw new Error('Film not found');
      }

      return await FilmModel.find();
    },
  },
};

// Create ands start the Apollo Server
const server = new ApolloServer({ typeDefs, resolvers });

server.listen().then(({ url }) => {
  console.log(`🚀 Server ready at ${url}`);
});
