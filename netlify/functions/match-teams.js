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

// Fuzzy matching algorithm
function calculateSimilarity(str1, str2) {
  const s1 = str1.toLowerCase().trim();
  const s2 = str2.toLowerCase().trim();

  // Exact match
  if (s1 === s2) return 1.0;

  // One contains the other
  if (s1.includes(s2) || s2.includes(s1)) return 0.9;

  // Levenshtein distance (simplified)
  const longer = s1.length > s2.length ? s1 : s2;
  const shorter = s1.length > s2.length ? s2 : s1;

  if (longer.length === 0) return 1.0;

  const editDistance = getEditDistance(longer, shorter);
  return (longer.length - editDistance) / longer.length;
}

function getEditDistance(s1, s2) {
  const costs = [];
  for (let i = 0; i <= s1.length; i++) {
    let lastValue = i;
    for (let j = 0; j <= s2.length; j++) {
      if (i === 0) {
        costs[j] = j;
      } else if (j > 0) {
        let newValue = costs[j - 1];
        if (s1.charAt(i - 1) !== s2.charAt(j - 1)) {
          newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
        }
        costs[j - 1] = lastValue;
        lastValue = newValue;
      }
    }
    if (i > 0) costs[s2.length] = lastValue;
  }
  return costs[s2.length];
}

// Find best matching team
function findBestMatch(teamName, teams) {
  let bestMatch = null;
  let bestScore = 0;

  for (const team of teams) {
    // Check against team name
    let score = calculateSimilarity(teamName, team.name);

    // Check against kambiName
    const kambiScore = calculateSimilarity(teamName, team.kambiName);
    score = Math.max(score, kambiScore);

    // Check against aliases
    for (const alias of team.aliases) {
      const aliasScore = calculateSimilarity(teamName, alias);
      score = Math.max(score, aliasScore);
    }

    if (score > bestScore) {
      bestScore = score;
      bestMatch = team;
    }
  }

  return { team: bestMatch, confidence: bestScore };
}

exports.handler = async (event) => {
  const headers = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'POST',
    'Content-Type': 'application/json'
  };

  // Handle preflight
  if (event.httpMethod === 'OPTIONS') {
    return { statusCode: 200, headers, body: '' };
  }

  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      headers,
      body: JSON.stringify({ error: 'Method not allowed' })
    };
  }

  try {
    const { teamName, league } = JSON.parse(event.body);

    if (!teamName) {
      return {
        statusCode: 400,
        headers,
        body: JSON.stringify({ error: 'Team name required' })
      };
    }

    const db = readTeamsDB();
    let teams = db.teams;

    // Filter by league if provided
    if (league) {
      teams = teams.filter(t => t.league === league);
    }

    const result = findBestMatch(teamName, teams);

    return {
      statusCode: 200,
      headers,
      body: JSON.stringify({
        matched: result.confidence >= 0.7,
        team: result.team,
        confidence: result.confidence,
        originalName: teamName
      })
    };

  } catch (error) {
    return {
      statusCode: 500,
      headers,
      body: JSON.stringify({ error: error.message })
    };
  }
};
