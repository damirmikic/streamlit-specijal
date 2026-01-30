const fs = require('fs');
const path = require('path');

const LEAGUES_DB_PATH = path.join(__dirname, '../../leagues_database.json');

// Helper to read leagues database
function readLeaguesDB() {
  try {
    const data = fs.readFileSync(LEAGUES_DB_PATH, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    return { leagues: [], lastUpdated: new Date().toISOString() };
  }
}

// Helper to write leagues database
function writeLeaguesDB(data) {
  data.lastUpdated = new Date().toISOString();
  fs.writeFileSync(LEAGUES_DB_PATH, JSON.stringify(data, null, 2));
}

exports.handler = async (event) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE',
    'Content-Type': 'application/json'
  };

  // Handle preflight
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  try {
    const db = readLeaguesDB();

    // GET - Retrieve leagues
    if (event.httpMethod === 'GET') {
      const { id, name } = event.queryStringParameters || {};

      let leagues = db.leagues;

      // Filter by ID
      if (id) {
        leagues = leagues.filter(league => league.id === id);
      }

      // Filter by name
      if (name) {
        leagues = leagues.filter(league => league.name === name);
      }

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ leagues, lastUpdated: db.lastUpdated })
      };
    }

    // POST - Add new league
    if (event.httpMethod === 'POST') {
      const newLeague = JSON.parse(event.body);

      // Generate ID
      const maxId = db.leagues.reduce((max, league) => {
        const num = parseInt(league.id.replace('league_', ''));
        return num > max ? num : max;
      }, 0);

      newLeague.id = `league_${String(maxId + 1).padStart(3, '0')}`;
      newLeague.stats = newLeague.stats || {
        homeWinRate: 0.45,
        drawRate: 0.27,
        awayWinRate: 0.28,
        avgGoals: 2.7,
        avgHomeGoals: 1.5,
        avgAwayGoals: 1.2
      };

      db.leagues.push(newLeague);
      writeLeaguesDB(db);

      return {
        statusCode: 201,
        headers,
        body: JSON.stringify({ success: true, league: newLeague })
      };
    }

    // PUT - Update existing league
    if (event.httpMethod === 'PUT') {
      const updatedLeague = JSON.parse(event.body);
      const index = db.leagues.findIndex(l => l.id === updatedLeague.id);

      if (index === -1) {
        return {
          statusCode: 404,
          headers,
          body: JSON.stringify({ error: 'League not found' })
        };
      }

      db.leagues[index] = { ...db.leagues[index], ...updatedLeague };
      writeLeaguesDB(db);

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ success: true, league: db.leagues[index] })
      };
    }

    // DELETE - Remove league
    if (event.httpMethod === 'DELETE') {
      const { id } = event.queryStringParameters || {};

      if (!id) {
        return {
          statusCode: 400,
          headers,
          body: JSON.stringify({ error: 'League ID required' })
        };
      }

      const index = db.leagues.findIndex(l => l.id === id);

      if (index === -1) {
        return {
          statusCode: 404,
          headers,
          body: JSON.stringify({ error: 'League not found' })
        };
      }

      db.leagues.splice(index, 1);
      writeLeaguesDB(db);

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ success: true })
      };
    }

    return {
      statusCode: 405,
      headers,
      body: JSON.stringify({ error: 'Method not allowed' })
    };

  } catch (error) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: error.message })
    };
  }
};
