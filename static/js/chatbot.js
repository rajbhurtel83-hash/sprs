/**
 * SPRS Chatbot Widget
 * Handles chat interaction with the AI assistant
 */
(function() {
    'use strict';

    const toggleBtn = document.getElementById('chatbotToggle');
    const chatWindow = document.getElementById('chatbotWindow');
    const closeBtn = document.getElementById('chatbotClose');
    const chatForm = document.getElementById('chatbotForm');
    const chatInput = document.getElementById('chatbotInput');
    const messagesContainer = document.getElementById('chatbotMessages');

    if (!toggleBtn || !chatWindow) return;

    let conversationHistory = [];
    var MAX_HISTORY_ITEMS = 16;
    var MAX_MESSAGE_LENGTH = 1200;

    // Toggle chat window
    toggleBtn.addEventListener('click', function() {
        chatWindow.classList.toggle('open');
        toggleBtn.classList.toggle('active');
        if (chatWindow.classList.contains('open')) {
            chatInput.focus();
        }
    });

    // Close chat window
    closeBtn.addEventListener('click', function() {
        chatWindow.classList.remove('open');
        toggleBtn.classList.remove('active');
    });

    // Handle message submission
    chatForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const message = chatInput.value.trim();
        if (!message) return;
        if (message.length > MAX_MESSAGE_LENGTH) {
            addMessage('Message too long. Please keep it under 1200 characters.', 'bot');
            return;
        }

        addMessage(message, 'user');
        chatInput.value = '';
        chatInput.disabled = true;

        conversationHistory.push({ role: 'user', content: message });
        if (conversationHistory.length > MAX_HISTORY_ITEMS) {
            conversationHistory = conversationHistory.slice(-MAX_HISTORY_ITEMS);
        }

        showTypingIndicator();

        fetch(CHATBOT_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN,
            },
            body: JSON.stringify({
                message: message,
                history: conversationHistory,
            }),
        })
        .then(function(response) {
            if (!response.ok) throw new Error('Network error');
            return response.json();
        })
        .then(function(data) {
            removeTypingIndicator();
            chatInput.disabled = false;
            chatInput.focus();

            conversationHistory.push({ role: 'assistant', content: data.response });
            if (conversationHistory.length > MAX_HISTORY_ITEMS) {
                conversationHistory = conversationHistory.slice(-MAX_HISTORY_ITEMS);
            }

            addBotMessage(data.response, data.properties || []);
        })
        .catch(function(error) {
            removeTypingIndicator();
            chatInput.disabled = false;
            chatInput.focus();
            addMessage('Sorry, something went wrong. Please try again.', 'bot');
        });
    });

    function addMessage(text, type) {
        var div = document.createElement('div');
        div.className = 'chat-message ' + type;
        div.innerHTML = '<div class="chat-bubble">' + escapeHtml(text) + '</div>';
        messagesContainer.appendChild(div);
        scrollToBottom();
    }

    function addBotMessage(text, properties) {
        var div = document.createElement('div');
        div.className = 'chat-message bot';

        var html = '<div class="chat-bubble">' + formatBotText(text);

        if (properties && properties.length > 0) {
            html += '<div class="chat-property-results">';
            properties.forEach(function(p) {
                var imgHtml = p.image
                    ? '<img src="' + p.image + '" alt="' + escapeHtml(p.title) + '">'
                    : '<div class="no-img"><i class="bi bi-image"></i></div>';

                html += '<a href="' + p.url + '" class="chat-property-card" target="_blank">'
                    + imgHtml
                    + '<div class="chat-property-info">'
                    + '<h6>' + escapeHtml(p.title) + '</h6>'
                    + '<p><i class="bi bi-geo-alt"></i> ' + escapeHtml(p.district) + '</p>'
                    + '<span class="price">Rs. ' + Number(p.price).toLocaleString() + '/mo</span>'
                    + '</div></a>';
            });
            html += '</div>';
        }

        html += '</div>';
        div.innerHTML = html;
        messagesContainer.appendChild(div);
        scrollToBottom();
    }

    function showTypingIndicator() {
        var div = document.createElement('div');
        div.className = 'chat-message bot';
        div.id = 'typingIndicator';
        div.innerHTML = '<div class="chat-bubble"><div class="typing-indicator">'
            + '<span></span><span></span><span></span></div></div>';
        messagesContainer.appendChild(div);
        scrollToBottom();
    }

    function removeTypingIndicator() {
        var el = document.getElementById('typingIndicator');
        if (el) el.remove();
    }

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    function escapeHtml(text) {
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }

    function formatBotText(text) {
        // Escape model output first, then apply simple formatting.
        var escaped = escapeHtml(String(text));
        return escaped.replace(/\n/g, '<br>').replace(/- /g, '&bull; ');
    }
})();
