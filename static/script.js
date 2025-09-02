const chatMessages = document.getElementById('chat-messages');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const statusDiv = document.getElementById('status-bar');
const voiceBtn = document.getElementById('toggle-voice-btn');
const voiceSelect = document.getElementById('voice-select');
const voiceInputBtn = document.getElementById('voice-input-btn');
const voiceStatus = document.getElementById('voice-status');

let ws;
let isVoiceEnabled = false;
let sessionId = null;

// Speech Recognition setup
let recognition = null;
let isRecording = false;

// --- WebSocket Connection Setup ---
function connectWebSocket() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Use your actual WebSocket host and port
    ws = new WebSocket(`${wsProtocol}//${window.location.hostname}:8765`);

    ws.onopen = () => {
        statusDiv.textContent = 'Connected to AI Voice Bot';
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Message received:', data);

        if (data.type === 'system' && data.client_id) {
            sessionId = data.client_id;
            addMessage('assistant', data.message);
        } else if (data.type === 'assistant' || data.type === 'voice_message_response') {
            const messageElement = addMessage('assistant', data.message, false, data.response_time_ms);
            // If voice is on, request audio for this new message
            if (isVoiceEnabled || data.type === 'voice_message_response') {
                requestVoice(data.message, messageElement.id);
            }
        } else if (data.type === 'voice_response') {
            // Audio is ready, add the play and download buttons
            addAudioButtonsToMessage(data.audio_data, data.messageId);
        } else if (data.type === 'user_transcript') {
             addMessage('user', data.message, true);
        } else if (data.type === 'error') {
            addMessage('system', `Error: ${data.message}`);
        }
    };

    ws.onclose = () => {
        statusDiv.textContent = 'Disconnected. Retrying in 5 seconds...';
        console.log('WebSocket disconnected');
        setTimeout(connectWebSocket, 5000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        statusDiv.textContent = 'Connection error. Check console.';
    };
}

// --- Message Display and Handling ---
function addMessage(sender, message, isUser = false, responseTime = null) {
    const messageId = `msg-${Date.now()}-${Math.random()}`;
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender);
    messageDiv.id = messageId;

    const contentDiv = document.createElement('div');
    contentDiv.classList.add('message-content');

    const p = document.createElement('p');
    // Basic markdown and HTML safety
    let formattedMessage = message.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    formattedMessage = formattedMessage.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>').replace(/\n/g, '<br>');
    p.innerHTML = formattedMessage;
    contentDiv.appendChild(p);

    if (sender === 'assistant') {
        const audioBtnContainer = document.createElement('div');
        audioBtnContainer.classList.add('audio-btn-container');
        contentDiv.appendChild(audioBtnContainer);
    }
    
    messageDiv.appendChild(contentDiv);

    const timestampDiv = document.createElement('div');
    timestampDiv.classList.add('timestamp');
    timestampDiv.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    if (responseTime) {
        const responseTimeSpan = document.createElement('span');
        responseTimeSpan.classList.add('response-time');
        responseTimeSpan.textContent = ` (${responseTime}ms)`;
        timestampDiv.appendChild(responseTimeSpan);
    }
    
    messageDiv.appendChild(timestampDiv);
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageDiv; // Return the element so we can get its ID
}

function sendMessage() {
    const message = userInput.value.trim();
    if (message === '' || ws.readyState !== WebSocket.OPEN) return;

    addMessage('user', message, true);
    
    const payload = {
        type: 'message',
        message: message,
        client_agent: navigator.userAgent
    };
    ws.send(JSON.stringify(payload));
    userInput.value = '';
}

// --- Voice Generation and Playback ---
function requestVoice(text, messageId) {
    if (ws.readyState === WebSocket.OPEN) {
        const payload = {
            type: 'voice_request',
            text: text,
            voice: voiceSelect.value,
            messageId: messageId
        };
        ws.send(JSON.stringify(payload));
    }
}

function addAudioButtonsToMessage(audioData, messageId) {
    if (!messageId) {
        console.error("Cannot add audio buttons: messageId is missing.");
        return;
    }
    const messageDiv = document.getElementById(messageId);
    if (!messageDiv) {
        console.error(`Element with ID ${messageId} not found.`);
        return;
    }

    const audioBtnContainer = messageDiv.querySelector('.audio-btn-container');
    if (audioBtnContainer) {
        // Create Play Button
        const playBtn = document.createElement('button');
        playBtn.className = 'play-audio-btn';
        playBtn.innerHTML = '▶️';
        playBtn.title = 'Play Audio';
        playBtn.onclick = () => {
            const audioBlob = base64toBlob(audioData, 'audio/wav');
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audio.play().catch(e => console.error("Audio play failed:", e));
        };

        // Create Download Button
        const downloadBtn = document.createElement('button');
        downloadBtn.className = 'download-audio-btn';
        downloadBtn.innerHTML = '💾'; // Save icon
        downloadBtn.title = 'Download Audio';
        downloadBtn.onclick = () => {
            const audioBlob = base64toBlob(audioData, 'audio/wav');
            const audioUrl = URL.createObjectURL(audioBlob);
            const link = document.createElement('a');
            link.href = audioUrl;
            const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
            link.download = `bot-response-${timestamp}.wav`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(audioUrl);
        };
        
        audioBtnContainer.innerHTML = ''; // Clear any placeholders
        audioBtnContainer.appendChild(playBtn);
        audioBtnContainer.appendChild(downloadBtn);
    }
}

function base64toBlob(base64Data, mimeType) {
    const byteCharacters = atob(base64Data);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
}

// --- UI Controls and Speech Recognition ---
function toggleVoice() {
    isVoiceEnabled = !isVoiceEnabled;
    voiceBtn.textContent = isVoiceEnabled ? '🔇 Disable Voice' : '🔊 Enable Voice';
    voiceBtn.classList.toggle('active', isVoiceEnabled);
}

function onVoiceChange() {
    statusDiv.textContent = `Voice changed to: ${voiceSelect.value}`;
}

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        voiceInputBtn.style.display = 'none';
        console.warn('Speech recognition not supported.');
        return;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        isRecording = true;
        voiceInputBtn.classList.add('recording');
        voiceInputBtn.textContent = '⏹️';
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        sendVoiceMessage(transcript);
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
    };

    recognition.onend = () => {
        isRecording = false;
        voiceInputBtn.classList.remove('recording');
        voiceInputBtn.textContent = '🎤';
    };
}

function toggleVoiceInput() {
    if (!recognition) return;
    if (isRecording) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

function sendVoiceMessage(transcript) {
    if (!transcript.trim()) return;
    
    addMessage('user', transcript, true);
    
    if (ws.readyState === WebSocket.OPEN) {
        const payload = {
            type: 'voice_message',
            message: transcript,
            client_agent: navigator.userAgent
        };
        ws.send(JSON.stringify(payload));
        userInput.value = '';
    }
}

// --- Event Listeners and Initialization ---
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

voiceBtn.addEventListener('click', toggleVoice);
voiceSelect.addEventListener('change', onVoiceChange);
voiceInputBtn.addEventListener('click', toggleVoiceInput);

// Initialize the application
connectWebSocket();
initSpeechRecognition();

