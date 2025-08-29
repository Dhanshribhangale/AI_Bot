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

// Add event listeners for voice functionality
voiceBtn.addEventListener('click', toggleVoice);
voiceSelect.addEventListener('change', onVoiceChange);

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
        statusDiv.textContent = 'Generating voice...';
    } else {
        addMessage('system', 'Connection not open. Please wait.');
    }
}

// Voice toggle functionality
function toggleVoice() {
    isVoiceEnabled = !isVoiceEnabled;
    if (isVoiceEnabled) {
        voiceBtn.textContent = '🔇 Disable Voice';
        voiceBtn.classList.add('active');
        statusDiv.textContent = 'Voice enabled. AI responses will be spoken.';
    } else {
        voiceBtn.textContent = '🔊 Enable Voice';
        voiceBtn.classList.remove('active');
        statusDiv.textContent = 'Voice disabled.';
        // Stop any currently playing audio
        stopAllAudio();
    }
}

// Handle voice selection change
function onVoiceChange() {
    const selectedVoice = voiceSelect.value;
    statusDiv.textContent = `Voice changed to: ${selectedVoice}`;
    console.log(`Voice changed to: ${selectedVoice}`);
}

// Audio queue management
function addToAudioQueue(audioUrl) {
    audioQueue.push(audioUrl);
    if (!isPlaying) {
        playNextInQueue();
    }
}

async function playNextInQueue() {
    if (audioQueue.length === 0) {
        isPlaying = false;
        return;
    }
    
    isPlaying = true;
    const audioUrl = audioQueue.shift();
    await playAudio(audioUrl);
    playNextInQueue();
}

// Stop all audio playback
function stopAllAudio() {
    // Clear the audio queue
    audioQueue.length = 0;
    isPlaying = false;
    
    // Stop any currently playing audio elements
    const audioElements = document.querySelectorAll('audio');
    audioElements.forEach(audio => {
        audio.pause();
        audio.currentTime = 0;
    });
}

async function playAudio(url) {
    return new Promise((resolve, reject) => {
        const audio = new Audio(url);
        
        audio.onloadstart = () => {
            statusDiv.textContent = 'Playing audio...';
        };
        
        audio.oncanplay = () => {
            statusDiv.textContent = 'Audio ready to play.';
        };
        
        audio.onended = () => {
            statusDiv.textContent = 'Ready to chat.';
            URL.revokeObjectURL(url);
            resolve();
        };
        
        audio.onerror = (error) => {
            console.error('Audio playback error:', error);
            statusDiv.textContent = 'Audio playback error.';
            URL.revokeObjectURL(url);
            reject(error);
        };
        
        audio.play().catch(error => {
            console.error('Failed to play audio:', error);
            statusDiv.textContent = 'Failed to play audio.';
            URL.revokeObjectURL(url);
            reject(error);
        });
    });
}

// Convert base64 to blob
function base64toBlob(base64Data, mimeType) {
    const byteCharacters = atob(base64Data);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    return new Blob([byteArray], { type: mimeType });
}

// Event listeners
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

// Initialize
connectWebSocket();