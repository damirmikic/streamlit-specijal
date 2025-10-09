exports.handler = async function(event, context) {
  const API_KEY = process.env.API_KEY;

  if (!API_KEY) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'API ključ nije konfigurisan u Netlify environment variables.' }),
    };
  }

  const nowInSeconds = Math.floor(Date.now() / 1000);
  const sevenDaysFromNowInSeconds = nowInSeconds + (7 * 24 * 60 * 60);

  const API_ENDPOINT = `https://sports-api.cloudbet.com/pub/v2/odds/competitions/basketball-international-euroleague?from=${nowInSeconds}&to=${sevenDaysFromNowInSeconds}&players=true&limit=100`;

  try {
    const response = await fetch(API_ENDPOINT, {
      headers: {
        "Accept": "application/json",
        "X-API-Key": API_KEY
      }
    });

    if (!response.ok) {
      const errorBody = await response.text();
      return {
        statusCode: response.status,
        body: JSON.stringify({ error: `API zahtev nije uspeo sa statusom ${response.status}: ${errorBody}` })
      };
    }

    let data = await response.json();

    if (data && data.events && Array.isArray(data.events)) {
        const filteredEvents = data.events.filter(event => event.type !== 'EVENT_TYPE_OUTRIGHT');
        data.events = filteredEvents;
    }

    return {
      statusCode: 200,
      body: JSON.stringify(data)
    };
  } catch (error) {
    console.error("Greška pri preuzimanju:", error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Nije uspelo preuzimanje podataka' })
    };
  }
};
