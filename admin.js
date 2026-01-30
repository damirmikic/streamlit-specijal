// Admin Panel JavaScript

// State
let teams = [];
let leagues = [];
let currentEditingTeam = null;
let currentEditingLeague = null;

// DOM Elements
const teamsTableBody = document.getElementById('teams-table-body');
const leaguesTableBody = document.getElementById('leagues-table-body');
const teamModal = document.getElementById('team-modal');
const leagueModal = document.getElementById('league-modal');
const statusMessages = document.getElementById('status-messages');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupModals();
    setupEventListeners();
    loadTeams();
    loadLeagues();
});

// Tab Management
function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;

            // Update active states
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            // Show selected tab content
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

// Modal Management
function setupModals() {
    // Team modal
    document.getElementById('add-team-btn').addEventListener('click', () => {
        currentEditingTeam = null;
        document.getElementById('team-modal-title').textContent = 'Add New Team';
        document.getElementById('team-form').reset();
        document.getElementById('team-id').value = '';
        teamModal.classList.remove('hidden');
    });

    document.getElementById('close-team-modal').addEventListener('click', () => {
        teamModal.classList.add('hidden');
    });

    document.getElementById('cancel-team-btn').addEventListener('click', () => {
        teamModal.classList.add('hidden');
    });

    // League modal
    document.getElementById('add-league-btn').addEventListener('click', () => {
        currentEditingLeague = null;
        document.getElementById('league-modal-title').textContent = 'Add New League';
        document.getElementById('league-form').reset();
        document.getElementById('league-id').value = '';
        leagueModal.classList.remove('hidden');
    });

    document.getElementById('close-league-modal').addEventListener('click', () => {
        leagueModal.classList.add('hidden');
    });

    document.getElementById('cancel-league-btn').addEventListener('click', () => {
        leagueModal.classList.add('hidden');
    });
}

// Event Listeners
function setupEventListeners() {
    // Team form submit
    document.getElementById('team-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveTeam();
    });

    // League form submit
    document.getElementById('league-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveLeague();
    });

    // Search and filters
    document.getElementById('team-search').addEventListener('input', (e) => {
        filterTeams(e.target.value, document.getElementById('team-league-filter').value);
    });

    document.getElementById('team-league-filter').addEventListener('change', (e) => {
        filterTeams(document.getElementById('team-search').value, e.target.value);
    });

    document.getElementById('league-search').addEventListener('input', (e) => {
        filterLeagues(e.target.value);
    });

    // Import/Export
    document.getElementById('import-teams-file').addEventListener('change', handleTeamsImport);
    document.getElementById('import-leagues-file').addEventListener('change', handleLeaguesImport);
    document.getElementById('export-teams-btn').addEventListener('click', exportTeams);
    document.getElementById('export-leagues-btn').addEventListener('click', exportLeagues);
}

// Load Teams
async function loadTeams() {
    try {
        const response = await fetch('/.netlify/functions/manage-teams');
        const data = await response.json();
        teams = data.teams || [];
        renderTeams();
        updateLeagueFilter();
        showStatus('Teams loaded successfully', 'success');
    } catch (error) {
        showStatus(`Error loading teams: ${error.message}`, 'error');
    }
}

// Load Leagues
async function loadLeagues() {
    try {
        const response = await fetch('/.netlify/functions/manage-leagues');
        const data = await response.json();
        leagues = data.leagues || [];
        renderLeagues();
        showStatus('Leagues loaded successfully', 'success');
    } catch (error) {
        showStatus(`Error loading leagues: ${error.message}`, 'error');
    }
}

// Render Teams Table
function renderTeams(filteredTeams = null) {
    const teamsToRender = filteredTeams || teams;

    if (teamsToRender.length === 0) {
        teamsTableBody.innerHTML = '<tr><td colspan="6" class="px-6 py-4 text-center text-gray-500">No teams found</td></tr>';
        return;
    }

    teamsTableBody.innerHTML = teamsToRender.map(team => `
        <tr class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">${team.name}</td>
            <td class="px-6 py-4 whitespace-nowrap text-gray-600">${team.league}</td>
            <td class="px-6 py-4 whitespace-nowrap text-gray-600">${team.kambiName}</td>
            <td class="px-6 py-4 whitespace-nowrap">
                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                    ${team.eloRating}
                </span>
            </td>
            <td class="px-6 py-4 text-sm text-gray-600">${team.aliases.join(', ') || '-'}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button onclick="editTeam('${team.id}')" class="text-blue-600 hover:text-blue-900 mr-3">Edit</button>
                <button onclick="deleteTeam('${team.id}')" class="text-red-600 hover:text-red-900">Delete</button>
            </td>
        </tr>
    `).join('');
}

// Render Leagues Table
function renderLeagues(filteredLeagues = null) {
    const leaguesToRender = filteredLeagues || leagues;

    if (leaguesToRender.length === 0) {
        leaguesTableBody.innerHTML = '<tr><td colspan="7" class="px-6 py-4 text-center text-gray-500">No leagues found</td></tr>';
        return;
    }

    leaguesTableBody.innerHTML = leaguesToRender.map(league => `
        <tr class="hover:bg-gray-50">
            <td class="px-6 py-4 whitespace-nowrap font-medium text-gray-900">${league.name}</td>
            <td class="px-6 py-4 whitespace-nowrap text-gray-600">${league.country}</td>
            <td class="px-6 py-4 whitespace-nowrap text-gray-600">${(league.stats.homeWinRate * 100).toFixed(1)}%</td>
            <td class="px-6 py-4 whitespace-nowrap text-gray-600">${(league.stats.drawRate * 100).toFixed(1)}%</td>
            <td class="px-6 py-4 whitespace-nowrap text-gray-600">${(league.stats.awayWinRate * 100).toFixed(1)}%</td>
            <td class="px-6 py-4 whitespace-nowrap text-gray-600">${league.stats.avgGoals.toFixed(2)}</td>
            <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button onclick="editLeague('${league.id}')" class="text-blue-600 hover:text-blue-900 mr-3">Edit</button>
                <button onclick="deleteLeague('${league.id}')" class="text-red-600 hover:text-red-900">Delete</button>
            </td>
        </tr>
    `).join('');
}

// Update League Filter Dropdown
function updateLeagueFilter() {
    const select = document.getElementById('team-league-filter');
    const uniqueLeagues = [...new Set(teams.map(t => t.league))].sort();

    select.innerHTML = '<option value="">All Leagues</option>' +
        uniqueLeagues.map(league => `<option value="${league}">${league}</option>`).join('');
}

// Filter Teams
function filterTeams(searchTerm, league) {
    let filtered = teams;

    if (searchTerm) {
        const search = searchTerm.toLowerCase();
        filtered = filtered.filter(team =>
            team.name.toLowerCase().includes(search) ||
            team.kambiName.toLowerCase().includes(search) ||
            team.aliases.some(alias => alias.toLowerCase().includes(search))
        );
    }

    if (league) {
        filtered = filtered.filter(team => team.league === league);
    }

    renderTeams(filtered);
}

// Filter Leagues
function filterLeagues(searchTerm) {
    if (!searchTerm) {
        renderLeagues();
        return;
    }

    const search = searchTerm.toLowerCase();
    const filtered = leagues.filter(league =>
        league.name.toLowerCase().includes(search) ||
        league.country.toLowerCase().includes(search)
    );

    renderLeagues(filtered);
}

// Save Team
async function saveTeam() {
    const teamData = {
        id: document.getElementById('team-id').value,
        name: document.getElementById('team-name').value.trim(),
        kambiName: document.getElementById('team-kambi-name').value.trim(),
        league: document.getElementById('team-league').value.trim(),
        country: document.getElementById('team-country').value.trim(),
        eloRating: parseInt(document.getElementById('team-elo').value),
        aliases: document.getElementById('team-aliases').value
            .split(',')
            .map(a => a.trim())
            .filter(a => a.length > 0)
    };

    try {
        const method = teamData.id ? 'PUT' : 'POST';
        const response = await fetch('/.netlify/functions/manage-teams', {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(teamData)
        });

        const result = await response.json();

        if (response.ok) {
            teamModal.classList.add('hidden');
            await loadTeams();
            showStatus(`Team ${teamData.id ? 'updated' : 'added'} successfully`, 'success');
        } else {
            showStatus(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        showStatus(`Error saving team: ${error.message}`, 'error');
    }
}

// Save League
async function saveLeague() {
    const leagueData = {
        id: document.getElementById('league-id').value,
        name: document.getElementById('league-name').value.trim(),
        country: document.getElementById('league-country').value.trim(),
        kambiUrl: document.getElementById('league-kambi-url').value.trim(),
        apiClient: document.getElementById('league-api-client').value,
        totalGames: parseInt(document.getElementById('league-total-games').value),
        stats: {
            homeWinRate: parseFloat(document.getElementById('league-home-win').value),
            drawRate: parseFloat(document.getElementById('league-draw').value),
            awayWinRate: parseFloat(document.getElementById('league-away-win').value),
            avgGoals: parseFloat(document.getElementById('league-avg-goals').value),
            avgHomeGoals: parseFloat(document.getElementById('league-avg-home-goals').value),
            avgAwayGoals: parseFloat(document.getElementById('league-avg-away-goals').value)
        }
    };

    try {
        const method = leagueData.id ? 'PUT' : 'POST';
        const response = await fetch('/.netlify/functions/manage-leagues', {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(leagueData)
        });

        const result = await response.json();

        if (response.ok) {
            leagueModal.classList.add('hidden');
            await loadLeagues();
            showStatus(`League ${leagueData.id ? 'updated' : 'added'} successfully`, 'success');
        } else {
            showStatus(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        showStatus(`Error saving league: ${error.message}`, 'error');
    }
}

// Edit Team
window.editTeam = function(teamId) {
    const team = teams.find(t => t.id === teamId);
    if (!team) return;

    currentEditingTeam = team;
    document.getElementById('team-modal-title').textContent = 'Edit Team';
    document.getElementById('team-id').value = team.id;
    document.getElementById('team-name').value = team.name;
    document.getElementById('team-kambi-name').value = team.kambiName;
    document.getElementById('team-league').value = team.league;
    document.getElementById('team-country').value = team.country || '';
    document.getElementById('team-elo').value = team.eloRating;
    document.getElementById('team-aliases').value = team.aliases.join(', ');

    teamModal.classList.remove('hidden');
};

// Delete Team
window.deleteTeam = async function(teamId) {
    if (!confirm('Are you sure you want to delete this team?')) return;

    try {
        const response = await fetch(`/.netlify/functions/manage-teams?id=${teamId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadTeams();
            showStatus('Team deleted successfully', 'success');
        } else {
            const result = await response.json();
            showStatus(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        showStatus(`Error deleting team: ${error.message}`, 'error');
    }
};

// Edit League
window.editLeague = function(leagueId) {
    const league = leagues.find(l => l.id === leagueId);
    if (!league) return;

    currentEditingLeague = league;
    document.getElementById('league-modal-title').textContent = 'Edit League';
    document.getElementById('league-id').value = league.id;
    document.getElementById('league-name').value = league.name;
    document.getElementById('league-country').value = league.country;
    document.getElementById('league-kambi-url').value = league.kambiUrl;
    document.getElementById('league-api-client').value = league.apiClient;
    document.getElementById('league-total-games').value = league.totalGames;
    document.getElementById('league-home-win').value = league.stats.homeWinRate;
    document.getElementById('league-draw').value = league.stats.drawRate;
    document.getElementById('league-away-win').value = league.stats.awayWinRate;
    document.getElementById('league-avg-goals').value = league.stats.avgGoals;
    document.getElementById('league-avg-home-goals').value = league.stats.avgHomeGoals;
    document.getElementById('league-avg-away-goals').value = league.stats.avgAwayGoals;

    leagueModal.classList.remove('hidden');
};

// Delete League
window.deleteLeague = async function(leagueId) {
    if (!confirm('Are you sure you want to delete this league?')) return;

    try {
        const response = await fetch(`/.netlify/functions/manage-leagues?id=${leagueId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            await loadLeagues();
            showStatus('League deleted successfully', 'success');
        } else {
            const result = await response.json();
            showStatus(`Error: ${result.error}`, 'error');
        }
    } catch (error) {
        showStatus(`Error deleting league: ${error.message}`, 'error');
    }
};

// Import/Export Functions
async function handleTeamsImport(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const importedData = JSON.parse(e.target.result);
            const importedTeams = importedData.teams || importedData;

            for (const team of importedTeams) {
                await fetch('/.netlify/functions/manage-teams', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(team)
                });
            }

            await loadTeams();
            showStatus(`Imported ${importedTeams.length} teams successfully`, 'success');
            event.target.value = '';
        } catch (error) {
            showStatus(`Error importing teams: ${error.message}`, 'error');
        }
    };
    reader.readAsText(file);
}

async function handleLeaguesImport(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const importedData = JSON.parse(e.target.result);
            const importedLeagues = importedData.leagues || importedData;

            for (const league of importedLeagues) {
                await fetch('/.netlify/functions/manage-leagues', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(league)
                });
            }

            await loadLeagues();
            showStatus(`Imported ${importedLeagues.length} leagues successfully`, 'success');
            event.target.value = '';
        } catch (error) {
            showStatus(`Error importing leagues: ${error.message}`, 'error');
        }
    };
    reader.readAsText(file);
}

function exportTeams() {
    const dataStr = JSON.stringify({ teams, lastUpdated: new Date().toISOString() }, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `teams_export_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
    showStatus('Teams exported successfully', 'success');
}

function exportLeagues() {
    const dataStr = JSON.stringify({ leagues, lastUpdated: new Date().toISOString() }, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `leagues_export_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
    showStatus('Leagues exported successfully', 'success');
}

// Status Messages
function showStatus(message, type = 'info') {
    const colors = {
        success: 'bg-green-100 border-green-400 text-green-700',
        error: 'bg-red-100 border-red-400 text-red-700',
        info: 'bg-blue-100 border-blue-400 text-blue-700'
    };

    const statusDiv = document.createElement('div');
    statusDiv.className = `border-l-4 p-4 ${colors[type]} mb-2`;
    statusDiv.innerHTML = `
        <div class="flex justify-between items-center">
            <p>${message}</p>
            <button onclick="this.parentElement.parentElement.remove()" class="text-gray-600 hover:text-gray-800">
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
            </button>
        </div>
    `;

    statusMessages.insertBefore(statusDiv, statusMessages.firstChild);

    // Auto-remove after 5 seconds
    setTimeout(() => statusDiv.remove(), 5000);
}
