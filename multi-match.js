// Multi-Match Calculator JavaScript

// State
let leagues = [];
let teams = [];
let currentLeague = null;
let matches = [];
let filteredMatches = [];

// DOM Elements
const leagueSelect = document.getElementById('league-select');
const leagueStats = document.getElementById('league-stats');
const valueBetScanner = document.getElementById('value-bet-scanner');
const matchesContainer = document.getElementById('matches-container');
const matchesTableBody = document.getElementById('matches-table-body');
const emptyState = document.getElementById('empty-state');
const scanBtn = document.getElementById('scan-matches-btn');
const scanningLoader = document.getElementById('scanning-loader');
const resultsCount = document.getElementById('results-count');
const noEloWarning = document.getElementById('no-elo-warning');

// EV Filter
const evSlider = document.getElementById('ev-slider');
const evMinLabel = document.getElementById('ev-min-label');
const evMaxLabel = document.getElementById('ev-max-label');
const applyEvFilter = document.getElementById('apply-ev-filter');
const includeLive = document.getElementById('include-live');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupEventListeners();
    loadLeagues();
    loadTeams();
});

// Tab Management
function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;

            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            tabContents.forEach(content => {
                if (content.id === `${tabName}-tab`) {
                    content.classList.remove('hidden');
                } else {
                    content.classList.add('hidden');
                }
            });
        });
    });
}

// Event Listeners
function setupEventListeners() {
    leagueSelect.addEventListener('change', handleLeagueChange);
    scanBtn.addEventListener('click', scanForMatches);

    // Stats toggle
    document.getElementById('toggle-stats').addEventListener('click', () => {
        const content = document.getElementById('stats-content');
        const arrow = document.getElementById('stats-arrow');
        content.classList.toggle('hidden');
        arrow.classList.toggle('rotate-180');
    });

    // EV Slider
    evSlider.addEventListener('input', (e) => {
        const value = parseFloat(e.target.value);
        evMinLabel.textContent = `${value.toFixed(1)}%`;
        filterMatches();
    });

    // Filters
    applyEvFilter.addEventListener('change', filterMatches);
    includeLive.addEventListener('change', filterMatches);
}

// Load Leagues
async function loadLeagues() {
    try {
        const response = await fetch('/.netlify/functions/manage-leagues');
        const data = await response.json();
        leagues = data.leagues || [];
        populateLeagueDropdown();
    } catch (error) {
        console.error('Error loading leagues:', error);
    }
}

// Load Teams
async function loadTeams() {
    try {
        const response = await fetch('/.netlify/functions/manage-teams');
        const data = await response.json();
        teams = data.teams || [];
    } catch (error) {
        console.error('Error loading teams:', error);
    }
}

// Populate League Dropdown
function populateLeagueDropdown() {
    leagueSelect.innerHTML = '<option value="">Choose a league...</option>' +
        leagues.map(league => `<option value="${league.id}">${league.name} (${league.country})</option>`).join('');
}

// Handle League Change
function handleLeagueChange(e) {
    const leagueId = e.target.value;

    if (!leagueId) {
        hideAllSections();
        emptyState.classList.remove('hidden');
        return;
    }

    currentLeague = leagues.find(l => l.id === leagueId);
    if (currentLeague) {
        displayLeagueStats();
        emptyState.classList.add('hidden');
        leagueStats.classList.remove('hidden');
        valueBetScanner.classList.remove('hidden');
        matchesContainer.classList.add('hidden');
        resultsCount.classList.add('hidden');
        noEloWarning.classList.add('hidden');
    }
}

// Display League Stats
function displayLeagueStats() {
    document.getElementById('league-name').textContent =
        `${currentLeague.name} (GP: ${currentLeague.totalGames})`;
    document.getElementById('home-win-rate').textContent =
        `${(currentLeague.stats.homeWinRate * 100).toFixed(1)}%`;
    document.getElementById('draw-rate').textContent =
        `${(currentLeague.stats.drawRate * 100).toFixed(1)}%`;
    document.getElementById('away-win-rate').textContent =
        `${(currentLeague.stats.awayWinRate * 100).toFixed(1)}%`;
    document.getElementById('avg-goals').textContent =
        currentLeague.stats.avgGoals.toFixed(2);
    document.getElementById('avg-hg').textContent =
        currentLeague.stats.avgHomeGoals.toFixed(2);
    document.getElementById('avg-ag').textContent =
        currentLeague.stats.avgAwayGoals.toFixed(2);
}

// Scan for Matches
async function scanForMatches() {
    if (!currentLeague) return;

    scanBtn.disabled = true;
    scanningLoader.classList.remove('hidden');
    resultsCount.classList.add('hidden');
    noEloWarning.classList.add('hidden');
    matchesContainer.classList.add('hidden');

    try {
        // Fetch matches from Kambi API
        const response = await fetch(currentLeague.kambiUrl);
        const data = await response.json();

        if (!data.events || data.events.length === 0) {
            resultsCount.classList.remove('hidden');
            document.getElementById('match-count').textContent = '0';
            return;
        }

        // Process matches
        matches = await processMatches(data.events);

        // Show results
        resultsCount.classList.remove('hidden');
        document.getElementById('match-count').textContent = matches.length;

        const matchesWithElo = matches.filter(m => m.homeTeam && m.awayTeam);

        if (matchesWithElo.length === 0) {
            noEloWarning.classList.remove('hidden');
        } else {
            filterMatches();
            matchesContainer.classList.remove('hidden');
        }

    } catch (error) {
        console.error('Error scanning matches:', error);
        alert(`Error: ${error.message}`);
    } finally {
        scanBtn.disabled = false;
        scanningLoader.classList.add('hidden');
    }
}

// Process Matches
async function processMatches(events) {
    const processedMatches = [];

    for (const event of events) {
        try {
            // Extract basic info
            const match = {
                id: event.event.id,
                homeName: event.event.homeName,
                awayName: event.event.awayName,
                startTime: new Date(event.event.start),
                isLive: event.event.state === 'STARTED',
                odds: null,
                homeTeam: null,
                awayTeam: null,
                fairOdds: null,
                ev: null
            };

            // Match teams to database
            const homeMatch = await matchTeam(match.homeName, currentLeague.name);
            const awayMatch = await matchTeam(match.awayName, currentLeague.name);

            if (homeMatch.matched) match.homeTeam = homeMatch.team;
            if (awayMatch.matched) match.awayTeam = awayMatch.team;

            // Fetch odds for this match
            const oddsData = await fetchMatchOdds(event.event.id);
            if (oddsData) {
                match.odds = oddsData;

                // Calculate fair odds and EV if we have both teams
                if (match.homeTeam && match.awayTeam) {
                    match.fairOdds = calculateFairOdds(match.homeTeam.eloRating, match.awayTeam.eloRating);
                    match.ev = calculateEV(match.odds, match.fairOdds);
                }
            }

            processedMatches.push(match);

        } catch (error) {
            console.error('Error processing match:', error);
        }
    }

    return processedMatches;
}

// Match Team
async function matchTeam(teamName, league) {
    try {
        const response = await fetch('/.netlify/functions/match-teams', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ teamName, league })
        });

        return await response.json();
    } catch (error) {
        console.error('Error matching team:', error);
        return { matched: false, team: null };
    }
}

// Fetch Match Odds
async function fetchMatchOdds(eventId) {
    try {
        const apiClient = currentLeague.apiClient || 'ilaniuswarl';
        const url = `https://eu-offering-api.kambicdn.com/offering/v2018/${apiClient}/betoffer/event/${eventId}.json?lang=en_GB&market=GB`;

        const response = await fetch(url);
        const data = await response.json();

        // Find 1X2 market
        const matchResultMarket = data.betOffers?.find(bo =>
            bo.criterion?.label === 'Full time' && bo.betOfferType?.name?.includes('Match Result')
        );

        if (!matchResultMarket || !matchResultMarket.outcomes) return null;

        const outcomes = matchResultMarket.outcomes;

        return {
            home: outcomes.find(o => o.label === '1' || o.type === 'OT_ONE')?.odds / 1000 || null,
            draw: outcomes.find(o => o.label === 'X' || o.type === 'OT_DRAW')?.odds / 1000 || null,
            away: outcomes.find(o => o.label === '2' || o.type === 'OT_TWO')?.odds / 1000 || null
        };

    } catch (error) {
        console.error('Error fetching odds:', error);
        return null;
    }
}

// Calculate Fair Odds from Elo Ratings
function calculateFairOdds(homeElo, awayElo) {
    // Elo-based win probability calculation
    const homeProbWin = 1 / (1 + Math.pow(10, (awayElo - homeElo - 100) / 400));
    const awayProbWin = 1 / (1 + Math.pow(10, (homeElo - awayElo + 100) / 400));

    // Draw probability (simplified model)
    const drawProb = Math.max(0.15, Math.min(0.35, currentLeague.stats.drawRate));

    // Normalize probabilities
    const totalProb = homeProbWin + awayProbWin + drawProb;
    const normHome = homeProbWin / totalProb;
    const normDraw = drawProb / totalProb;
    const normAway = awayProbWin / totalProb;

    return {
        home: 1 / normHome,
        draw: 1 / normDraw,
        away: 1 / normAway
    };
}

// Calculate Expected Value (EV)
function calculateEV(bookmakerOdds, fairOdds) {
    const evHome = ((bookmakerOdds.home / fairOdds.home) - 1) * 100;
    const evDraw = ((bookmakerOdds.draw / fairOdds.draw) - 1) * 100;
    const evAway = ((bookmakerOdds.away / fairOdds.away) - 1) * 100;

    return {
        home: evHome,
        draw: evDraw,
        away: evAway,
        max: Math.max(evHome, evDraw, evAway),
        best: evHome > evDraw && evHome > evAway ? 'home' : (evAway > evDraw ? 'away' : 'draw')
    };
}

// Filter Matches
function filterMatches() {
    let filtered = matches.filter(m => m.homeTeam && m.awayTeam && m.odds && m.ev);

    // Apply EV filter
    if (applyEvFilter.checked) {
        const minEV = parseFloat(evSlider.value);
        filtered = filtered.filter(m => m.ev.max >= minEV);
    }

    // Apply live match filter
    if (!includeLive.checked) {
        filtered = filtered.filter(m => !m.isLive);
    }

    filteredMatches = filtered;
    displayMatches();
}

// Display Matches
function displayMatches() {
    if (filteredMatches.length === 0) {
        matchesTableBody.innerHTML = '<tr><td colspan="8" class="px-6 py-4 text-center text-gray-500">No matches found with the current filters</td></tr>';
        return;
    }

    matchesTableBody.innerHTML = filteredMatches.map(match => {
        const bestBet = match.ev.best;
        const bestEV = match.ev[bestBet];
        const evClass = bestEV > 5 ? 'positive-ev' : (bestEV < -5 ? 'negative-ev' : '');

        const recommendation = bestEV > 5
            ? `<span class="px-2 py-1 bg-green-100 text-green-800 rounded font-semibold">
                Bet ${bestBet === 'home' ? '1' : bestBet === 'draw' ? 'X' : '2'} (${bestEV.toFixed(1)}%)
               </span>`
            : `<span class="px-2 py-1 bg-gray-100 text-gray-600 rounded">No value</span>`;

        return `
            <tr class="match-row ${evClass}">
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    ${formatDateTime(match.startTime)}
                    ${match.isLive ? '<span class="ml-2 px-2 py-1 bg-red-100 text-red-800 text-xs rounded">LIVE</span>' : ''}
                </td>
                <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">${match.homeName}</td>
                <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">${match.awayName}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    ${match.homeTeam.eloRating} / ${match.awayTeam.eloRating}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <span class="${bestBet === 'home' ? 'font-bold text-green-700' : ''}">${match.odds.home.toFixed(2)}</span>
                    -
                    <span class="${bestBet === 'draw' ? 'font-bold text-green-700' : ''}">${match.odds.draw.toFixed(2)}</span>
                    -
                    <span class="${bestBet === 'away' ? 'font-bold text-green-700' : ''}">${match.odds.away.toFixed(2)}</span>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    ${match.fairOdds.home.toFixed(2)} - ${match.fairOdds.draw.toFixed(2)} - ${match.fairOdds.away.toFixed(2)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    <div class="font-semibold ${bestEV > 5 ? 'text-green-700' : bestEV < -5 ? 'text-red-700' : 'text-gray-600'}">
                        ${bestEV.toFixed(1)}%
                    </div>
                    <div class="text-xs text-gray-500">
                        (${match.ev.home.toFixed(1)} / ${match.ev.draw.toFixed(1)} / ${match.ev.away.toFixed(1)})
                    </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm">
                    ${recommendation}
                </td>
            </tr>
        `;
    }).join('');
}

// Format Date/Time
function formatDateTime(date) {
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');

    return `${day}/${month} ${hours}:${minutes}`;
}

// Hide All Sections
function hideAllSections() {
    leagueStats.classList.add('hidden');
    valueBetScanner.classList.add('hidden');
    matchesContainer.classList.add('hidden');
}
