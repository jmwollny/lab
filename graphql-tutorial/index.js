const { ApolloServer, gql } = require('apollo-server');

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
    id: ID!
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

// Mock Data - Hammer Studios films

const films = [
  {
    id: '1',
    title: 'The Public Life of Henry the Ninth',
    year: 1935,
    watched: false,
  },
  {
    id: '2',
    title: 'The Mystery of the Mary Celeste',
    year: 1935,
    watched: false,
  },
  { id: '3', title: 'Song of Freedom', year: 1936, watched: false },
  { id: '4', title: 'The Gypsy Melody', year: 1936, watched: false },
  { id: '5', title: 'Sporting Love', year: 1936, watched: false },
  { id: '6', title: 'Death in High Heels', year: 1947, watched: false },
  { id: '7', title: 'The River Patrol', year: 1948, watched: false },
  { id: '8', title: 'Who Killed Van Loon?', year: 1948, watched: false },
  { id: '9', title: 'Dick Barton: Special Agent', year: 1948, watched: false },
  { id: '10', title: 'The Adventures of P.C. 49', year: 1949, watched: false },
  { id: '11', title: 'Celia', year: 1949, watched: false },
  { id: '12', title: 'Dick Barton Strikes Back', year: 1949, watched: false },
  {
    id: '13',
    title: 'Dr. Morelle: The Case of the Missing Heiress',
    year: 1949,
    watched: false,
  },
  { id: '14', title: 'The Man in Black', year: 1949, watched: false },
  { id: '15', title: 'Meet Simon Cherry', year: 1949, watched: false },
  { id: '16', title: 'Dick Barton at Bay', year: 1950, watched: false },
  { id: '17', title: 'The Lady Craved Excitement', year: 1950, watched: false },
  { id: '18', title: 'Room to Let', year: 1950, watched: false },
  { id: '19', title: 'Someone at the Door', year: 1950, watched: false },
  { id: '20', title: 'What the Butler Saw', year: 1950, watched: false },
  { id: '21', title: 'The Black Widow', year: 1951, watched: false },
  { id: '22', title: 'A Case for PC 49', year: 1951, watched: false },
  { id: '23', title: 'Cloudburst', year: 1951, watched: false },
  { id: '24', title: 'The Dark Light', year: 1951, watched: false },
  { id: '25', title: 'The Rossiter Case', year: 1951, watched: false },
  { id: '26', title: 'To Have and to Hold', year: 1951, watched: false },
  { id: '27', title: 'Death of an Angel', year: 1952, watched: false },
  { id: '28', title: 'The Gambler and the Lady', year: 1952, watched: false },
  { id: '29', title: 'Lady in the Fog', year: 1952, watched: false },
  { id: '30', title: 'The Last Page', year: 1952, watched: false },
  { id: '31', title: 'Never Look Back', year: 1952, watched: false },
  { id: '32', title: 'Stolen Face', year: 1952, watched: false },
  {
    id: '33',
    title: 'Whispering Smith Hits London',
    year: 1952,
    watched: false,
  },
  { id: '34', title: 'Wings of Danger', year: 1952, watched: false },
  { id: '35', title: 'Blood Orange', year: 1953, watched: false },
  { id: '36', title: 'The Four Sided Triangle', year: 1953, watched: false },
  { id: '37', title: 'Manty-Trap', year: 1953, watched: false },
  { id: '38', title: "The Saint's Return", year: 1953, watched: false },
  { id: '39', title: 'Spaceways', year: 1953, watched: false },
  { id: '40', title: 'Face the Music', year: 1954, watched: false },
  { id: '41', title: 'Five Days', year: 1954, watched: false },
  { id: '42', title: 'The House Across the Lake', year: 1954, watched: false },
  { id: '43', title: 'Life with the Lyons', year: 1954, watched: false },
  { id: '44', title: 'Mask of Dust', year: 1954, watched: false },
  { id: '45', title: 'The Men of Sherwood Forest', year: 1954, watched: false },
  { id: '46', title: 'The Stranger Came Home', year: 1954, watched: false },
  { id: '47', title: 'Third Party Risk', year: 1954, watched: false },
  { id: '48', title: 'The Glass Cage', year: 1955, watched: false },
  { id: '49', title: 'The Lyons in Paris', year: 1955, watched: false },
  { id: '50', title: 'Murder by Proxy', year: 1955, watched: false },
  { id: '51', title: 'The Quatermass Xperiment', year: 1955, watched: false },
  { id: '52', title: 'Women Without Men', year: 1956, watched: false },
  { id: '53', title: 'X the Unknown', year: 1956, watched: true },
  { id: '54', title: 'The Abominable Snowman', year: 1957, watched: true },
  { id: '55', title: 'The Curse of Frankenstein', year: 1957, watched: true },
  { id: '56', title: 'Quatermass 2', year: 1957, watched: false },
  { id: '57', title: 'The Steel Bayonet', year: 1957, watched: false },
  { id: '58', title: 'The Camp on Blood Island', year: 1958, watched: false },
  { id: '59', title: 'Dracula', year: 1958, watched: true },
  { id: '60', title: 'Further Up the Creek', year: 1958, watched: false },
  { id: '61', title: 'I Only Arsked!', year: 1958, watched: false },
  {
    id: '62',
    title: 'The Revenge of Frankenstein',
    year: 1958,
    watched: false,
  },
  { id: '63', title: 'The Snorkel', year: 1958, watched: false },
  { id: '64', title: "Don't Panic Chaps!", year: 1959, watched: false },
  {
    id: '65',
    title: 'The Hound of the Baskervilles',
    year: 1959,
    watched: false,
  },
  {
    id: '66',
    title: 'The Man Who Could Cheat Death',
    year: 1959,
    watched: false,
  },
  { id: '67', title: 'The Mummy', year: 1959, watched: false },
  { id: '68', title: 'The Stranglers of Bombay', year: 1959, watched: false },
  { id: '69', title: "Yesterday's Enemy", year: 1959, watched: false },
  { id: '70', title: 'The Brides of Dracula', year: 1960, watched: false },
  { id: '71', title: 'The Full Treatment', year: 1960, watched: false },
  { id: '72', title: 'Hell Is a City', year: 1960, watched: false },
  {
    id: '73',
    title: 'Never Take Sweets from a Stranger',
    year: 1960,
    watched: false,
  },
  { id: '74', title: 'Sword of Sherwood Forest', year: 1960, watched: false },
  {
    id: '75',
    title: 'The Two Faces of Dr. Jekyll',
    year: 1960,
    watched: false,
  },
  { id: '76', title: 'Cash on Demand', year: 1961, watched: false },
  { id: '77', title: 'The Curse of the Werewolf', year: 1961, watched: false },
  { id: '78', title: 'Taste of Fear', year: 1961, watched: false },
  { id: '79', title: 'The Terror of the Tongs', year: 1961, watched: false },
  { id: '80', title: 'Visa to Canton', year: 1961, watched: false },
  { id: '81', title: 'Watch It, Sailor!', year: 1961, watched: false },
  { id: '82', title: 'A Weekend with Lulu', year: 1961, watched: false },
  { id: '83', title: 'Captain Clegg', year: 1962, watched: false },
  { id: '84', title: 'The Phantom of the Opera', year: 1962, watched: false },
  { id: '85', title: 'The Pirates of Blood River', year: 1962, watched: false },
  { id: '86', title: 'The Damned', year: 1963, watched: false },
  { id: '87', title: 'The Kiss of the Vampire', year: 1963, watched: false },
  { id: '88', title: 'Maniac', year: 1963, watched: true },
  { id: '89', title: 'The Old Dark House', year: 1963, watched: false },
  { id: '90', title: 'Paranoiac', year: 1963, watched: false },
  { id: '91', title: 'The Scarlet Blade', year: 1963, watched: false },
  {
    id: '92',
    title: "The Curse of the Mummy's Tomb",
    year: 1964,
    watched: false,
  },
  { id: '93', title: 'The Devil-Ship Pirates', year: 1964, watched: false },
  { id: '94', title: 'The Evil of Frankenstein', year: 1964, watched: false },
  { id: '95', title: 'The Gorgon', year: 1964, watched: false },
  { id: '96', title: 'Nightmare', year: 1964, watched: false },
  { id: '97', title: 'The Brigand of Kandahar', year: 1965, watched: false },
  { id: '98', title: 'Fanatic', year: 1965, watched: false },
  { id: '99', title: 'The Nanny', year: 1965, watched: false },
  {
    id: '100',
    title: 'The Secret of Blood Island',
    year: 1965,
    watched: false,
  },
  { id: '101', title: 'She', year: 1965, watched: false },
  {
    id: '102',
    title: 'Dracula: Prince of Darkness',
    year: 1966,
    watched: false,
  },
  { id: '103', title: 'One Million Years B.C.', year: 1966, watched: false },
  { id: '104', title: 'The Plague of the Zombies', year: 1966, watched: false },
  { id: '105', title: 'Rasputin the Mad Monk', year: 1966, watched: false },
  { id: '106', title: 'The Reptile', year: 1966, watched: false },
  { id: '107', title: 'The Witches', year: 1966, watched: false },
  {
    id: '108',
    title: 'A Challenge for Robin Hood',
    year: 1967,
    watched: false,
  },
  {
    id: '109',
    title: 'Frankenstein Created Woman',
    year: 1967,
    watched: false,
  },
  { id: '110', title: 'Prehistoric Women', year: 1967, watched: false },
  { id: '111', title: 'Quatermass and the Pit', year: 1967, watched: false },
  { id: '112', title: 'The Viking Queen', year: 1967, watched: false },
  { id: '113', title: 'The Anniversary', year: 1968, watched: false },
  { id: '114', title: 'The Devil Rides Out', year: 1968, watched: false },
  {
    id: '115',
    title: 'Dracula Has Risen from the Grave',
    year: 1968,
    watched: false,
  },
  { id: '116', title: 'The Lost Continent', year: 1968, watched: false },
  { id: '117', title: 'The Vengeance of She', year: 1968, watched: false },
  {
    id: '118',
    title: 'Frankenstein Must Be Destroyed',
    year: 1969,
    watched: false,
  },
  { id: '119', title: 'Moon Zero Two', year: 1969, watched: false },
  { id: '120', title: 'Crescendo', year: 1970, watched: false },
  { id: '121', title: 'The Horror of Frankenstein', year: 1970, watched: true },
  { id: '122', title: 'Scars of Dracula', year: 1970, watched: false },
  { id: '123', title: 'The Vampire Lovers', year: 1970, watched: true },
  {
    id: '124',
    title: 'When Dinosaurs Ruled the Earth',
    year: 1970,
    watched: false,
  },
  { id: '125', title: 'Countess Dracula', year: 1971, watched: false },
  {
    id: '126',
    title: 'Creatures the World Forgot',
    year: 1971,
    watched: false,
  },
  {
    id: '127',
    title: 'Dr. Jekyll and Sister Hyde',
    year: 1971,
    watched: false,
  },
  { id: '128', title: 'Hands of the Ripper', year: 1971, watched: false },
  { id: '129', title: 'Lust for a Vampire', year: 1971, watched: true },
  { id: '130', title: 'On the Buses', year: 1971, watched: false },
  { id: '131', title: 'Twins of Evil', year: 1971, watched: true },
  { id: '132', title: 'Demons of the Mind', year: 1972, watched: false },
  { id: '133', title: 'Dracula A.D. 1972', year: 1972, watched: true },
  { id: '134', title: 'Fear in the Night', year: 1972, watched: false },
  { id: '135', title: 'Mutiny on the Buses', year: 1972, watched: false },
  { id: '136', title: 'Nearest and Dearest', year: 1972, watched: false },
  { id: '137', title: 'Straight on Till Morning', year: 1972, watched: false },
  { id: '138', title: "That's Your Funeral", year: 1972, watched: false },
  { id: '139', title: 'Vampire Circus', year: 1972, watched: false },
  { id: '140', title: 'Holiday on the Buses', year: 1973, watched: false },
  { id: '141', title: 'Love Thy Neighbour', year: 1973, watched: false },
  {
    id: '142',
    title: 'The Satanic Rites of Dracula',
    year: 1973,
    watched: true,
  },
  {
    id: '143',
    title: 'Captain Kronos – Vampire Hunter',
    year: 1974,
    watched: false,
  },
  {
    id: '144',
    title: 'Frankenstein and the Monster from Hell',
    year: 1974,
    watched: false,
  },
  {
    id: '145',
    title: 'The Legend of the 7 Golden Vampires',
    year: 1974,
    watched: false,
  },
  { id: '146', title: 'Shatter', year: 1974, watched: false },
  { id: '147', title: 'To the Devil a Daughter', year: 1976, watched: false },
  { id: '148', title: 'The Lady Vanishes', year: 1979, watched: false },
  { id: '149', title: 'Beyond the Rave', year: 2008, watched: false },
  { id: '150', title: 'Let Me In', year: 2010, watched: false },
  { id: '151', title: 'The Resident', year: 2011, watched: false },
  { id: '152', title: 'Wake Wood', year: 2011, watched: false },
  { id: '153', title: 'The Woman in Black', year: 2012, watched: true },
  { id: '154', title: 'The Quiet Ones', year: 2014, watched: false },
  {
    id: '155',
    title: 'The Woman in Black: Angel of Death',
    year: 2015,
    watched: true,
  },
  { id: '156', title: 'The Lodge', year: 2019, watched: false },
  { id: '157', title: 'Doctor Jekyll', year: 2023, watched: false },
];

// The Resolvers
const resolvers = {
  Query: {
    films: (parent, args) => {
      let filteredFilms = films;

      // Watch filter
      if (args.watched !== undefined) {
        filteredFilms = filteredFilms.filter((f) => f.watched === args.watched);
      }

      // Year filter
      if (args.year) {
        filteredFilms = filteredFilms.filter((f) => f.year === args.year);
      }

      // Date range filter
      if (args.where) {
        if (args.where.year_gte) {
          filteredFilms = filteredFilms.filter(
            (f) => f.year >= args.where.year_gte,
          );
        }
        if (args.where.year_lte) {
          filteredFilms = filteredFilms.filter(
            (f) => f.year <= args.where.year_lte,
          );
        }
      }

      // Search filter
      if (args.searchTerm) {
        filteredFilms = filteredFilms.filter((f) =>
          f.title.toLowerCase().includes(args.searchTerm.toLowerCase()),
        );
      }

      return filteredFilms;
    },
    film: (parent, args) => films.find((f) => f.id === args.id),
  },
  Mutation: {
    addFilm: (parent, { input }) => {
      // Check if ID already exists to prevent duplicates
      const exists = films.find((f) => f.id === input.id);
      if (exists) {
        throw new Error('A film with this ID already exists.');
      }

      const newFilm = { ...input };
      films.push(newFilm);
      return newFilm;
    },
    updateWatched: (parent, { id, watched }) => {
      const film = films.find((f) => f.id == id);
      if (!film) {
        throw new Error('Film not found');
      }

      film.watched = watched;
      return film;
    },

    deleteFilm: (parent, { id }) => {
      const index = films.findIndex((f) => f.id == id);
      if (index == -1) {
        throw new Error('Film not found');
      }

      // Remove the film and return the updated list
      films.splice(index, 1);
      return films;
    },
  },
};

// Create ands start the Apollo Server
const server = new ApolloServer({ typeDefs, resolvers });

server.listen().then(({ url }) => {
  console.log(`🚀 Server ready at ${url}`);
});
