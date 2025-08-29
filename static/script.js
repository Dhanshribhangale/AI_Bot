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
const audioQueue = [];
let isPlaying = false;

// Speech Recognition setup
let recognition = null;
let isRecording = false;

// Initialize speech recognition if available
function initSpeechRecognition() {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        recognition = new SpeechRecognition();
        
        recognition.continuous = false;
        recognition.interimResults = true;
        recognition.lang = 'en-US';
        
        recognition.onstart = () => {
            isRecording = true;
            voiceInputBtn.classList.add('recording');
            voiceInputBtn.textContent = '⏹️';
            voiceStatus.textContent = 'Listening...';
            voiceStatus.className = 'voice-status recording';
            statusDiv.textContent = 'Voice input active...';
        };
        
        recognition.onresult = (event) => {
            let finalTranscript = '';
            let interimTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }
            
            // Show interim results
            if (interimTranscript) {
                userInput.value = interimTranscript;
            }
            
            // Process final result
            if (finalTranscript) {
                userInput.value = finalTranscript;
                voiceStatus.textContent = 'Processing voice input...';
                voiceStatus.className = 'voice-status success';
                
                // Automatically send the voice input
                setTimeout(() => {
                    sendVoiceMessage(finalTranscript);
                }, 500);
            }
        };
        
        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            isRecording = false;
            voiceInputBtn.classList.remove('recording');
            voiceInputBtn.textContent = '🎤';
            voiceStatus.textContent = `Error: ${event.error}`;
            voiceStatus.className = 'voice-status error';
            statusDiv.textContent = 'Voice input error. Please try again.';
        };
        
        recognition.onend = () => {
            isRecording = false;
            voiceInputBtn.classList.remove('recording');
            voiceInputBtn.textContent = '🎤';
            if (voiceStatus.textContent === 'Listening...') {
                voiceStatus.textContent = 'Voice input ended';
                voiceStatus.className = 'voice-status';
            }
            statusDiv.textContent = 'Ready to chat.';
        };
        
        console.log('Speech recognition initialized');
    } else {
        console.warn('Speech recognition not supported in this browser');
        voiceInputBtn.style.display = 'none';
        voiceStatus.textContent = 'Voice input not supported in this browser';
        voiceStatus.className = 'voice-status error';
    }
}

// Add event listeners for voice functionality
voiceBtn.addEventListener('click', toggleVoice);
voiceSelect.addEventListener('change', onVoiceChange);
voiceInputBtn.addEventListener('click', toggleVoiceInput);

// Voice input toggle function
function toggleVoiceInput() {
    if (!recognition) {
        voiceStatus.textContent = 'Speech recognition not available';
        voiceStatus.className = 'voice-status error';
        return;
    }
    
    if (isRecording) {
        recognition.stop();
    } else {
        try {
            recognition.start();
        } catch (error) {
            console.error('Error starting speech recognition:', error);
            voiceStatus.textContent = 'Error starting voice input';
            voiceStatus.className = 'voice-status error';
        }
    }
}

// Function to send voice message
function sendVoiceMessage(transcript) {
    if (!transcript.trim()) return;
    
    // Display user message
    addMessage('user', transcript);
    statusDiv.textContent = 'Processing voice input...';
    
    // Send message to server
    if (ws.readyState === WebSocket.OPEN) {
        const payload = {
            type: 'voice_message',
            message: transcript,
            client_agent: navigator.userAgent
        };
        ws.send(JSON.stringify(payload));
        userInput.value = '';
        
        // Automatically enable voice output for voice input
        if (!isVoiceEnabled) {
            isVoiceEnabled = true;
            voiceBtn.textContent = '🔇 Disable Voice';
            voiceBtn.classList.add('active');
        }
    } else {
        addMessage('system', 'Connection not open. Please wait.');
    }
}

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
        } else if (data.type === 'voice_message_response') {
            // Handle response to voice input - automatically enable voice output
            addMessage('assistant', data.message);
            isVoiceEnabled = true;
            voiceBtn.textContent = '🔇 Disable Voice';
            voiceBtn.classList.add('active');
            
            // Always generate voice for voice input responses
            requestVoice(data.message);
            statusDiv.textContent = 'Ready to chat.';
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
initSpeechRecognition(); // Initialize speech recognition