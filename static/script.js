const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const statusDiv = document.getElementById('status-bar');
const voiceBtn = document.getElementById('toggle-voice-btn');
const voiceSelect = document.getElementById('voice-select');

let ws;
let isVoiceEnabled = false;
let sessionId = null;
const audioQueue = [];
let isPlaying = false;

function connectWebSocket() {
    ws = new WebSocket(`ws://${location.hostname}:8765`);

    ws.onopen = () => {
        statusDiv.textContent = 'Connected. Waiting for AI...';
        console.log('WebSocket connected');
    };

    ws.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        console.log('Message received:', data);

        if (data.type === 'system' && data.client_id) {
            sessionId = data.client_id;
            addMessage('assistant', data.message);
            statusDiv.textContent = 'Ready to chat.';
        } else if (data.type === 'assistant') {
            addMessage('assistant', data.message);
            if (isVoiceEnabled) {
                // Request voice for the assistant's message
                requestVoice(data.message);
            }
            statusDiv.textContent = 'Ready to chat.';
        } else if (data.type === 'voice_response') {
            const audioData = data.audio_data;
            if (audioData) {
                const audioBlob = base64toBlob(audioData, 'audio/wav');
                const audioUrl = URL.createObjectURL(audioBlob);
                await playAudio(audioUrl);
            }
        } else if (data.type === 'error') {
            addMessage('system', `Error: ${data.message}`);
            statusDiv.textContent = 'An error occurred.';
        }
    };

    ws.onclose = () => {
        statusDiv.textContent = 'Disconnected. Retrying in 5 seconds...';
        console.log('WebSocket disconnected');
        setTimeout(connectWebSocket, 5000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        statusDiv.textContent = 'Connection error. Check console for details.';
    };
}

function addMessage(sender, message) {
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender);
    messageDiv.textContent = message;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function sendMessage() {
    const message = userInput.value.trim();
    if (message === '') return;

    // Display user message
    addMessage('user', message);
    statusDiv.textContent = 'Thinking...';

    // Send message to server
    if (ws.readyState === WebSocket.OPEN) {
        const payload = {
            type: 'message',
            message: message,
            client_agent: navigator.userAgent
        };
        ws.send(JSON.stringify(payload));
        userInput.value = '';
    } else {
        addMessage('system', 'Connection not open. Please wait.');
    }
}

function requestVoice(text) {
    if (ws.readyState === WebSocket.OPEN) {
        const payload = {
            type: 'voice_request',
            text: text,
            voice: voiceSelect.value,
            client_agent: navigator.userAgent
        };
        ws.send(JSON.stringify(payload));
    }
}

async function playAudio(url) {
    audioQueue.push(url);
    if (!isPlaying) {
        await processQueue();
    }
}

async function processQueue() {
    if (audioQueue.length === 0) {
        isPlaying = false;
        return;
    }

    isPlaying = true;
    const audioUrl = audioQueue.shift();
    const audio = new Audio(audioUrl);
    
    await new Promise(resolve => {
        audio.onended = resolve;
        audio.play().catch(e => {
            console.error('Audio playback failed:', e);
            resolve();
        });
    });

    URL.revokeObjectURL(audioUrl);
    await processQueue();
}

function base64toBlob(base64, mimeType) {
    const byteCharacters = atob(base64);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
}

sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (event) => {
    if (event.key === 'Enter') {
        sendMessage();
    }
});

voiceBtn.addEventListener('click', () => {
    isVoiceEnabled = !isVoiceEnabled;
    if (isVoiceEnabled) {
        voiceBtn.textContent = '🔇 Voice On';
        voiceBtn.style.backgroundColor = '#dc3545';
        voiceBtn.style.color = '#fff';
    } else {
        voiceBtn.textContent = '🔊 Text to Voice';
        voiceBtn.style.backgroundColor = '#28a745';
        voiceBtn.style.color = '#fff';
    }
});

document.addEventListener('DOMContentLoaded', connectWebSocket);