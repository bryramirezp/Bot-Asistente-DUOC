document.addEventListener('DOMContentLoaded', () => {
    
    const chatbot = {
        elements: {
            toggle: document.getElementById('chatbot-toggle'),
            window: document.getElementById('chatbot-window'),
            close: document.getElementById('close-chat'),
            send: document.getElementById('send-message'),
            input: document.getElementById('user-input'),
            messages: document.getElementById('chatbot-messages'),
            chipsContainer: document.getElementById('suggestion-chips')
        },
        apiUrl: 'https://bddoqdk2ti.execute-api.us-east-1.amazonaws.com/ask',
        sessionId: null,

        init() {
            this.getOrCreateSessionId();
            this.addEventListeners();
            this.addChipEventListeners();
            console.log("Chatbot inicializado con Session ID:", this.sessionId);
        },
        
        getOrCreateSessionId() {
            let sessionId = sessionStorage.getItem('duocChatSessionId');
            if (!sessionId) {
                // Fallback para navegadores que no soportan crypto.randomUUID()
                sessionId = this.generateUUID();
                sessionStorage.setItem('duocChatSessionId', sessionId);
            }
            this.sessionId = sessionId;
        },

        generateUUID() {
            // Generador de UUID v4 compatible con todos los navegadores
            return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
                const r = Math.random() * 16 | 0;
                const v = c === 'x' ? r : (r & 0x3 | 0x8);
                return v.toString(16);
            });
        },

        addEventListeners() {
            this.elements.toggle.addEventListener('click', () => this.elements.window.classList.toggle('active'));
            this.elements.close.addEventListener('click', () => this.elements.window.classList.remove('active'));
            this.elements.send.addEventListener('click', () => this.sendMessage());
            this.elements.input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendMessage();
            });
        },

        addChipEventListeners() {
            console.log('Setting up chip event listeners');
            if (!this.elements.chipsContainer) {
                console.error('Chips container not found');
                return;
            }
            console.log('Chips container found:', this.elements.chipsContainer);

            this.elements.chipsContainer.addEventListener('click', (e) => {
                console.log('Click detected on chips container', e.target);
                if (e.target.classList.contains('chip')) {
                    console.log('Chip clicked:', e.target.textContent);
                    const query = e.target.textContent;
                    this.elements.input.value = query;
                    this.sendMessage();
                    this.elements.chipsContainer.style.display = 'none';
                }
            });
        },

        async sendMessage() {
            const message = this.elements.input.value.trim();
            if (!message) return;

            this.addMessage(message, 'user');
            this.elements.input.value = '';
            if (this.elements.chipsContainer) this.elements.chipsContainer.style.display = 'none';
            
            this.addTypingIndicator();

            try {
                const response = await fetch(this.apiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        query: message,
                        sessionId: this.sessionId
                    }),
                    mode: 'cors'
                });
                
                this.removeTypingIndicator();

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ error: 'Respuesta de error no es JSON' }));
                    throw new Error(`API Error: ${response.status} - ${errorData.error || 'Error desconocido'}`);
                }
                
                // Lógica de respuesta simple (no-streaming)
                const data = await response.json();
                this.addMessage(data.answer, 'bot');

            } catch (error) {
                this.removeTypingIndicator();
                this.addMessage('Lo siento, estoy teniendo problemas para conectarme al asistente.', 'bot');
                console.error('Error:', error);
            }
        },

        addMessage(text, type) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';

            if (type === 'bot') {
                // Mantenemos el renderizado de Markdown
                contentDiv.innerHTML = marked.parse(text || "");
            } else {
                contentDiv.textContent = text;
            }
            
            messageDiv.appendChild(contentDiv);
            this.elements.messages.appendChild(messageDiv);
            this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
            return messageDiv;
        },

        addTypingIndicator() {
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message bot typing-message';
            typingDiv.innerHTML = `<div class="message-content"><div class="typing-indicator"><span></span><span></span><span></span></div></div>`;
            this.elements.messages.appendChild(typingDiv);
            this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
        },

        removeTypingIndicator() {
            const typingMessage = this.elements.messages.querySelector('.typing-message');
            if (typingMessage) typingMessage.remove();
        }
    };

    chatbot.init();
});