const fs = require('fs');
const path = require('path');

const TEAMS_DB_PATH = path.join(__dirname, '../../teams_database.json');

// Helper to read teams database
function readTeamsDB() {
  try {
    const data = fs.readFileSync(TEAMS_DB_PATH, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    return { teams: [], lastUpdated: new Date().toISOString() };
  }
}

// Helper to write teams database
function writeTeamsDB(data) {
  data.lastUpdated = new Date().toISOString();
  fs.writeFileSync(TEAMS_DB_PATH, JSON.stringify(data, null, 2));
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
    const db = readTeamsDB();

    // GET - Retrieve teams
    if (event.httpMethod === 'GET') {
      const { search, league } = event.queryStringParameters || {};

      let teams = db.teams;

      // Filter by search term
      if (search) {
        const searchLower = search.toLowerCase();
        teams = teams.filter(team =>
          team.name.toLowerCase().includes(searchLower) ||
          team.aliases.some(alias => alias.toLowerCase().includes(searchLower)) ||
          team.kambiName.toLowerCase().includes(searchLower)
        );
      }

      // Filter by league
      if (league) {
        teams = teams.filter(team => team.league === league);
      }

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ teams, lastUpdated: db.lastUpdated })
      };
    }

    // POST - Add new team
    if (event.httpMethod === 'POST') {
      const newTeam = JSON.parse(event.body);

      // Generate ID
      const maxId = db.teams.reduce((max, team) => {
        const num = parseInt(team.id.replace('team_', ''));
        return num > max ? num : max;
      }, 0);

      newTeam.id = `team_${String(maxId + 1).padStart(3, '0')}`;
      newTeam.aliases = newTeam.aliases || [];

      db.teams.push(newTeam);
      writeTeamsDB(db);

      return {
        statusCode: 201,
        headers,
        body: JSON.stringify({ success: true, team: newTeam })
      };
    }

    // PUT - Update existing team
    if (event.httpMethod === 'PUT') {
      const updatedTeam = JSON.parse(event.body);
      const index = db.teams.findIndex(t => t.id === updatedTeam.id);

      if (index === -1) {
        return {
          statusCode: 404,
          headers,
          body: JSON.stringify({ error: 'Team not found' })
        };
      }

      db.teams[index] = { ...db.teams[index], ...updatedTeam };
      writeTeamsDB(db);

      return {
        statusCode: 200,
        headers,
        body: JSON.stringify({ success: true, team: db.teams[index] })
      };
    }

    // DELETE - Remove team
    if (event.httpMethod === 'DELETE') {
      const { id } = event.queryStringParameters || {};

      if (!id) {
        return {
          statusCode: 400,
          headers,
          body: JSON.stringify({ error: 'Team ID required' })
        };
      }

      const index = db.teams.findIndex(t => t.id === id);

      if (index === -1) {
        return {
          statusCode: 404,
          headers,
          body: JSON.stringify({ error: 'Team not found' })
        };
      }

      db.teams.splice(index, 1);
      writeTeamsDB(db);

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
