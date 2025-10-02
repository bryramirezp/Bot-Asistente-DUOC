const messagesDiv = document.getElementById('messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const statusSpan = document.getElementById('connection-status');

// Verificar conexión al cargar
checkHealth();

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

async function sendMessage() {
    const query = userInput.value.trim();
    if (!query) return;
    
    // Mostrar mensaje del usuario
    addMessage(query, 'user');
    userInput.value = '';
    
    // Mostrar indicador de carga
    const loadingId = addMessage('Pensando...', 'assistant', true);
    
    try {
        const response = await sendQuery(query);
        removeMessage(loadingId);
        addMessage(response.answer, 'assistant');
        
        if (response.sources && response.sources.length > 0) {
            const sources = response.sources.map(s => s.source).join(', ');
            addMessage(`Fuentes: ${sources}`, 'sources');
        }
    } catch (error) {
        removeMessage(loadingId);
        addMessage('Error: No pude procesar tu pregunta. Verifica que los servicios estén corriendo.', 'error');
    }
}

function addMessage(text, type, isLoading = false) {
    const id = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.id = `msg-${id}`;
    messageDiv.textContent = text;
    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    return id;
}

function removeMessage(id) {
    const msg = document.getElementById(`msg-${id}`);
    if (msg) msg.remove();
}

async function checkHealth() {
    try {
        const health = await getHealth();
        const allUp = Object.values(health.services).every(s => s === 'up');
        statusSpan.textContent = allUp ? 'Estado: Conectado ✓' : 'Estado: Servicios parcialmente activos';
        statusSpan.className = allUp ? 'connected' : 'partial';
    } catch {
        statusSpan.textContent = 'Estado: Desconectado ✗';
        statusSpan.className = 'disconnected';
    }
}

setInterval(checkHealth, 30000); // Verificar cada 30s