const API_URL = 'http://localhost:3000';

async function sendQuery(query) {
    const response = await fetch(`${API_URL}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query })
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    
    return await response.json();
}

async function getHealth() {
    const response = await fetch(`${API_URL}/health`);
    return await response.json();
}