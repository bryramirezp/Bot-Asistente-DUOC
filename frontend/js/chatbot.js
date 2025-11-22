document.addEventListener('DOMContentLoaded', () => {
    
    class ChatHistory {
        constructor() {
            this.messages = [];
            this.MAX_MESSAGES = 10;
            this.STORAGE_KEY = 'duocChatHistory';
            this.loadFromStorage();
        }
        
        addMessage(role, content) {
            this.messages.push({ role, content });
            if (this.messages.length > this.MAX_MESSAGES) {
                this.messages = this.messages.slice(-this.MAX_MESSAGES);
            }
            this.saveToStorage();
        }
        
        getHistory() {
            return this.messages;
        }
        
        clear() {
            this.messages = [];
            sessionStorage.removeItem(this.STORAGE_KEY);
        }
        
        saveToStorage() {
            try {
                sessionStorage.setItem(
                    this.STORAGE_KEY, 
                    JSON.stringify(this.messages)
                );
            } catch (e) {
                console.warn('Could not save history:', e);
            }
        }
        
        loadFromStorage() {
            try {
                const stored = sessionStorage.getItem(this.STORAGE_KEY);
                if (stored) {
                    this.messages = JSON.parse(stored);
                }
            } catch (e) {
                console.warn('Could not load history:', e);
                this.messages = [];
            }
        }
    }
    
    const chatbot = {
        elements: {
            toggle: document.getElementById('chatbot-toggle'),
            window: document.getElementById('chatbot-window'),
            close: document.getElementById('close-chat'),
            send: document.getElementById('send-message'),
            input: document.getElementById('user-input'),
            messages: document.getElementById('chatbot-messages'),
            chipsContainer: document.getElementById('suggestion-chips'),
            clearHistory: document.getElementById('clear-history'),
            clearHistoryModal: document.getElementById('clear-history-modal'),
            closeClearHistoryModal: document.getElementById('close-clear-history-modal'),
            cancelClearHistory: document.getElementById('cancel-clear-history'),
            confirmClearHistory: document.getElementById('confirm-clear-history'),
            suggestionsBtn: document.getElementById('suggestions-btn'),
            suggestionsModal: document.getElementById('suggestions-modal'),
            suggestionsForm: document.getElementById('suggestions-form'),
            suggestionsNotification: document.getElementById('suggestions-notification'),
            closeSuggestionsModal: document.getElementById('close-suggestions-modal'),
            cancelSuggestions: document.getElementById('cancel-suggestions')
        },
        apiUrl: 'https://bddoqdk2ti.execute-api.us-east-1.amazonaws.com/ask',
        sessionId: null,
        history: null,

        init() {
            this.history = new ChatHistory();
            this.getOrCreateSessionId();
            this.loadHistoryToUI();
            this.addEventListeners();
            this.addChipEventListeners();
            this.initEmailJS();
            this.initSuggestionsModal();
            this.initClearHistoryModal();
            this.addClearHistoryListener();
            console.log("Chatbot inicializado con Session ID:", this.sessionId);
        },
        
        loadHistoryToUI() {
            const history = this.history.getHistory();
            if (history.length === 0) {
                this.elements.messages.innerHTML = `
                    <div class="message bot">
                        <div class="message-content">
                            ¡Hola! Soy el asistente virtual de la Mesa de Servicio de Duoc UC. ¿En qué puedo ayudarte hoy?
                        </div>
                    </div>
                `;
                return;
            }
            
            this.elements.messages.innerHTML = '';
            history.forEach(msg => {
                if (msg.role === 'user') {
                    this.addMessage(msg.content, 'user');
                } else if (msg.role === 'assistant') {
                    this.addMessage(msg.content, 'bot');
                }
            });
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

        addClearHistoryListener() {
            if (this.elements.clearHistory) {
                this.elements.clearHistory.addEventListener('click', () => {
                    this.openClearHistoryModal();
                });
            }
        },

        async sendMessage() {
            const message = this.elements.input.value.trim();
            if (!message) return;

            this.addMessage(message, 'user');
            this.elements.input.value = '';
            if (this.elements.chipsContainer) this.elements.chipsContainer.style.display = 'none';
            
            // Agregar el mensaje del usuario al historial INMEDIATAMENTE
            // Esto previene race conditions cuando el usuario envía múltiples mensajes rápidamente
            this.history.addMessage('user', message);
            
            // Obtener una copia del historial actualizado para esta petición
            const historyForRequest = this.history.getHistory();
            
            this.addTypingIndicator();

            // Deshabilitar entradas para prevenir race conditions
            this.elements.input.disabled = true;
            this.elements.send.disabled = true;

            try {
                const response = await fetch(this.apiUrl, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ 
                        query: message,
                        history: historyForRequest
                    }),
                    mode: 'cors',
                    credentials: 'omit'
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ error: 'Error desconocido' }));
                    const errorMessage = this.getErrorMessage(response.status, errorData.error);
                    this.addMessage(errorMessage, 'bot');
                    // Agregar el mensaje de error al historial también
                    this.history.addMessage('assistant', errorMessage);
                    console.error(`API Error: ${response.status} - ${errorData.error || 'Error desconocido'}`, errorData.request_id || '');
                    return;
                }
                
                const data = await response.json();
                this.addMessage(data.answer, 'bot');
                
                if (data.sources && data.sources.length > 0) {
                    this.displaySources(data.sources);
                }
                
                // Solo agregar la respuesta del asistente al historial después de recibirla
                this.history.addMessage('assistant', data.answer);

            } catch (error) {
                // Manejo específico de errores CORS
                if (error.name === 'TypeError' && (error.message.includes('Failed to fetch') || error.message.includes('CORS'))) {
                    console.error('CORS Error:', error);
                    this.addMessage('Error de conexión CORS. Por favor, verifica que el API Gateway esté configurado correctamente o contacta al administrador.', 'bot');
                } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
                    this.addMessage('Error de conexión. Por favor, verifica tu conexión a internet e intenta nuevamente.', 'bot');
                } else {
                    this.addMessage('Lo siento, estoy teniendo problemas para conectarme al asistente. Por favor, intenta nuevamente más tarde.', 'bot');
                }
                console.error('Error completo:', error);
            } finally {
                // Siempre rehabilitar las entradas, incluso si hay un error
                this.removeTypingIndicator();
                this.elements.input.disabled = false;
                this.elements.send.disabled = false;
                
                // Re-enfocar el input para el siguiente mensaje
                this.elements.input.focus();
            }
        },
        
        getErrorMessage(statusCode, errorMessage) {
            const errorMessages = {
                400: 'La solicitud no es válida. Por favor, verifica tu pregunta e intenta nuevamente.',
                403: 'Acceso denegado. Por favor, verifica que estés accediendo desde el sitio correcto.',
                429: 'Demasiadas solicitudes. Por favor, espera unos momentos e intenta nuevamente.',
                500: 'Error interno del servidor. Por favor, intenta nuevamente más tarde.',
                503: 'Servicio temporalmente no disponible. Por favor, intenta nuevamente más tarde.'
            };
            
            return errorMessages[statusCode] || errorMessage || 'Ocurrió un error. Por favor, intenta nuevamente.';
        },
        
        displaySources(sources) {
            if (!sources || sources.length === 0) return;
            
            const sourcesDiv = document.createElement('div');
            sourcesDiv.className = 'message bot sources-message';
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content sources-content';
            
            let sourcesHTML = '<div class="sources-header"><strong>Fuentes:</strong></div><ul class="sources-list">';
            sources.forEach((source, index) => {
                const url = source.url || '';
                const hasValidUrl = url && (url.startsWith('http://') || url.startsWith('https://'));
                
                sourcesHTML += `<li class="source-item">`;
                
                if (hasValidUrl) {
                    // Crear enlace clicable en azul que abre en nueva pestaña
                    sourcesHTML += `<a href="${this.escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="source-link">${this.escapeHtml(url)}</a>`;
                } else if (url) {
                    // Si hay URL pero no es válida, mostrar como texto
                    sourcesHTML += `<span class="source-name">${this.escapeHtml(url)}</span>`;
                } else {
                    // Fallback si no hay URL
                    sourcesHTML += `<span class="source-name">Fuente ${index + 1}</span>`;
                }
                
                if (source.excerpt) {
                    const excerptText = this.escapeHtml(source.excerpt.substring(0, 150));
                    const excerptEllipsis = source.excerpt.length > 150 ? '...' : '';
                    sourcesHTML += `<div class="source-excerpt">${excerptText}${excerptEllipsis}</div>`;
                }
                
                sourcesHTML += `</li>`;
            });
            sourcesHTML += '</ul>';
            
            contentDiv.innerHTML = sourcesHTML;
            sourcesDiv.appendChild(contentDiv);
            this.elements.messages.appendChild(sourcesDiv);
            this.elements.messages.scrollTop = this.elements.messages.scrollHeight;
        },
        
        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },

        addMessage(text, type) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';

            if (type === 'bot') {
                // 1. Convertir el Markdown a HTML
                const rawHtml = marked.parse(text || "");
                
                // 2. SANITIZAR el HTML antes de insertarlo
                const cleanHtml = DOMPurify.sanitize(rawHtml, {
                    ADD_ATTR: ['target', 'rel'] // Permite 'target' para _blank
                });
                
                // 3. Insertar el HTML limpio y seguro
                contentDiv.innerHTML = cleanHtml;
                
                // 4. Tu lógica de enlaces (esto sigue siendo bueno)
                const links = contentDiv.querySelectorAll('a');
                links.forEach(link => {
                    link.setAttribute('target', '_blank');
                    link.setAttribute('rel', 'noopener noreferrer');
                });
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
        },

        initEmailJS() {
            // Inicializar EmailJS con tu Public Key
            // IMPORTANTE: Reemplaza "TU_PUBLIC_KEY" con tu Public Key de EmailJS
            if (typeof emailjs !== 'undefined') {
                emailjs.init("3_b52KEgqA-2xA7AJ");
                console.log("EmailJS inicializado");
            } else {
                console.warn("EmailJS no está disponible. Verifica que el script esté cargado.");
            }
        },

        initSuggestionsModal() {
            // Abrir modal al hacer clic en el botón de sugerencias
            if (this.elements.suggestionsBtn) {
                this.elements.suggestionsBtn.addEventListener('click', () => {
                    this.openSuggestionsModal();
                });
            }

            // Cerrar modal con botón X
            if (this.elements.closeSuggestionsModal) {
                this.elements.closeSuggestionsModal.addEventListener('click', () => {
                    this.closeSuggestionsModal();
                });
            }

            // Cerrar modal con botón Cancelar
            if (this.elements.cancelSuggestions) {
                this.elements.cancelSuggestions.addEventListener('click', () => {
                    this.closeSuggestionsModal();
                });
            }

            // Cerrar modal al hacer clic fuera del contenido
            if (this.elements.suggestionsModal) {
                this.elements.suggestionsModal.addEventListener('click', (e) => {
                    if (e.target === this.elements.suggestionsModal) {
                        this.closeSuggestionsModal();
                    }
                });
            }

            // Manejar envío del formulario
            if (this.elements.suggestionsForm) {
                this.elements.suggestionsForm.addEventListener('submit', (e) => {
                    e.preventDefault();
                    this.handleSuggestionsSubmit(e.target);
                });
            }
        },

        openSuggestionsModal() {
            if (this.elements.suggestionsModal) {
                this.elements.suggestionsModal.classList.add('active');
                // Ocultar notificaciones previas al abrir el modal
                this.hideNotification();
                // Enfocar el textarea cuando se abre el modal
                const textarea = document.getElementById('suggestion-message');
                if (textarea) {
                    setTimeout(() => textarea.focus(), 100);
                }
            }
        },

        closeSuggestionsModal() {
            if (this.elements.suggestionsModal) {
                this.elements.suggestionsModal.classList.remove('active');
                // Limpiar el formulario y ocultar notificaciones al cerrar
                if (this.elements.suggestionsForm) {
                    this.elements.suggestionsForm.reset();
                }
                this.hideNotification();
            }
        },

        showNotification(message, type = 'success') {
            const notification = this.elements.suggestionsNotification;
            if (!notification) return;

            // Remover clases previas
            notification.className = 'notification';
            notification.classList.add(type);

            // Configurar icono según el tipo
            const icons = {
                success: '✅',
                error: '❌',
                warning: '⚠️'
            };

            // Establecer contenido de la notificación
            notification.innerHTML = `
                <span class="notification-icon">${icons[type] || icons.success}</span>
                <span>${message}</span>
            `;

            // Mostrar notificación
            notification.style.display = 'flex';

            // Auto-ocultar después de 5 segundos para mensajes de éxito
            if (type === 'success') {
                setTimeout(() => {
                    this.hideNotification();
                }, 5000);
            }

            // Scroll al inicio del formulario para ver la notificación
            notification.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        },

        hideNotification() {
            const notification = this.elements.suggestionsNotification;
            if (notification) {
                notification.style.display = 'none';
                notification.className = 'notification';
                notification.innerHTML = '';
            }
        },

        handleSuggestionsSubmit(form) {
            const submitBtn = form.querySelector('button[type="submit"]');
            const messageField = form.querySelector('textarea[name="message"]');
            
            // Ocultar notificaciones previas
            this.hideNotification();
            
            if (!messageField || !messageField.value.trim()) {
                this.showNotification('Por favor, escribe una sugerencia antes de enviar.', 'warning');
                return;
            }

            // Deshabilitar botón durante el envío
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Enviando...';
            }

            // Verificar que EmailJS esté disponible
            if (typeof emailjs === 'undefined') {
                this.showNotification('Error: EmailJS no está disponible. Por favor, verifica la configuración.', 'error');
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Enviar Sugerencia';
                }
                return;
            }

            // Enviar sugerencia con EmailJS
            emailjs.send("service_0jerlea", "template_ysmb4rr", {
                message: messageField.value.trim()
            })
            .then(() => {
                this.showNotification('Gracias por tu sugerencia 🙌', 'success');
                
                // Esperar un momento antes de cerrar el modal para que el usuario vea el mensaje
                setTimeout(() => {
                    form.reset();
                    this.closeSuggestionsModal();
                }, 2000);
                
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Enviar Sugerencia';
                }
            })
            .catch((error) => {
                console.error("Error al enviar sugerencia:", error);
                this.showNotification('Hubo un problema al enviar la sugerencia. Por favor, intenta nuevamente.', 'error');
                
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Enviar Sugerencia';
                }
            });
        },

        initClearHistoryModal() {
            if (this.elements.clearHistoryModal) {
                this.elements.clearHistoryModal.addEventListener('click', (e) => {
                    if (e.target === this.elements.clearHistoryModal) {
                        this.closeClearHistoryModal();
                    }
                });
            }

            if (this.elements.closeClearHistoryModal) {
                this.elements.closeClearHistoryModal.addEventListener('click', () => {
                    this.closeClearHistoryModal();
                });
            }

            if (this.elements.cancelClearHistory) {
                this.elements.cancelClearHistory.addEventListener('click', () => {
                    this.closeClearHistoryModal();
                });
            }

            if (this.elements.confirmClearHistory) {
                this.elements.confirmClearHistory.addEventListener('click', () => {
                    this.confirmClearHistoryAction();
                });
            }
        },

        openClearHistoryModal() {
            if (this.elements.clearHistoryModal) {
                this.elements.clearHistoryModal.classList.add('active');
            }
        },

        closeClearHistoryModal() {
            if (this.elements.clearHistoryModal) {
                this.elements.clearHistoryModal.classList.remove('active');
            }
        },

        confirmClearHistoryAction() {
            // A. Borrar el sessionStorage
            sessionStorage.clear();
            this.history.messages = [];
            
            // Regenerar ID de sesión
            this.getOrCreateSessionId();
            
            // B. Limpiar la interfaz visual del chat
            this.elements.messages.innerHTML = '';
            
            // C. Restaurar el mensaje de bienvenida por defecto
            this.elements.messages.innerHTML = `
                <div class="message bot">
                    <div class="message-content">
                        ¡Hola! Soy el asistente virtual de la Mesa de Servicio de Duoc UC. ¿En qué puedo ayudarte hoy?
                    </div>
                </div>
            `;
            
            // D. Cerrar el modal
            this.closeClearHistoryModal();
            
            console.log('Historial borrado y sesión reiniciada.');
        }
    };

    chatbot.init();
});