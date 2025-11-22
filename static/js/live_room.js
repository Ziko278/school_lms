// Live Room - Agora Video/Audio + Collaborative Whiteboard

// Get data from hidden inputs
const sessionId = document.getElementById('sessionId').value;
const agoraAppId = document.getElementById('agoraAppId').value;
const agoraChannel = document.getElementById('agoraChannel').value;
let agoraToken = document.getElementById('agoraToken').value;
const websocketUrl = document.getElementById('websocketUrl').value;
const isLecturer = document.getElementById('isLecturer').value === 'true';
const userName = document.getElementById('userName').value;

// Agora Client
let rtc = {
    client: null,
    localAudioTrack: null,
    localVideoTrack: null,
};

let isAudioMuted = false;
let isVideoMuted = false;
let remoteUsers = {};

// WebSocket for whiteboard sync
let ws = null;

// Fabric.js Canvas
let fabricCanvas = null;
let isDrawing = false;
let currentTool = 'pen';
let canvasHistory = [];
let historyIndex = -1;

// ================== INIT ==================
document.addEventListener('DOMContentLoaded', async () => {
    initAgoraClient();
    initWhiteboard();
    initWebSocket();
    setupEventListeners();

    // Join Agora channel
    await joinAgoraChannel();
});

// ================== AGORA SETUP ==================
function initAgoraClient() {
    rtc.client = AgoraRTC.createClient({ mode: 'rtc', codec: 'vp8' });

    rtc.client.on('user-published', async (user, mediaType) => {
        await rtc.client.subscribe(user, mediaType);
        console.log('User published:', user.uid, mediaType);

        if (mediaType === 'video') {
            const playerId = `player-${user.uid}`;
            let playerContainer = document.getElementById(playerId);

            if (!playerContainer) {
                playerContainer = document.createElement('div');
                playerContainer.id = playerId;
                playerContainer.className = 'remote-player';
                playerContainer.innerHTML = `<div class="player-label">Participant ${user.uid}</div>`;
                document.getElementById('remote-players').appendChild(playerContainer);
            }

            user.videoTrack.play(playerId);
            remoteUsers[user.uid] = user;
            updateParticipantCount();
        }

        if (mediaType === 'audio') {
            user.audioTrack.play();
        }
    });

    rtc.client.on('user-unpublished', (user, mediaType) => {
        console.log('User unpublished:', user.uid, mediaType);

        if (mediaType === 'video') {
            const playerId = `player-${user.uid}`;
            const playerContainer = document.getElementById(playerId);
            if (playerContainer) {
                playerContainer.remove();
            }
        }
    });

    rtc.client.on('user-left', (user) => {
        console.log('User left:', user.uid);
        const playerId = `player-${user.uid}`;
        const playerContainer = document.getElementById(playerId);
        if (playerContainer) {
            playerContainer.remove();
        }
        delete remoteUsers[user.uid];
        updateParticipantCount();
    });
}

async function joinAgoraChannel() {
    try {
        const uid = await rtc.client.join(agoraAppId, agoraChannel, agoraToken, null);
        console.log('Joined Agora channel with UID:', uid);

        // Create local audio/video tracks
        rtc.localAudioTrack = await AgoraRTC.createMicrophoneAudioTrack();
        rtc.localVideoTrack = await AgoraRTC.createCameraVideoTrack();

        // Play local video
        rtc.localVideoTrack.play('local-player');

        // Publish tracks
        await rtc.client.publish([rtc.localAudioTrack, rtc.localVideoTrack]);
        console.log('Published local tracks');

        updateParticipantCount();
    } catch (error) {
        console.error('Error joining channel:', error);
        alert('Failed to join session: ' + error.message);
    }
}

async function leaveAgoraChannel() {
    // Close local tracks
    if (rtc.localAudioTrack) {
        rtc.localAudioTrack.close();
    }
    if (rtc.localVideoTrack) {
        rtc.localVideoTrack.close();
    }

    // Leave channel
    await rtc.client.leave();
    console.log('Left Agora channel');
}

function updateParticipantCount() {
    const count = 1 + Object.keys(remoteUsers).length;
    document.getElementById('participantCount').textContent = count;
}

// ================== WHITEBOARD SETUP ==================
function initWhiteboard() {
    const canvas = document.getElementById('whiteboardCanvas');
    const container = document.getElementById('whiteboardContainer');

    fabricCanvas = new fabric.Canvas(canvas, {
        isDrawingMode: true,
        backgroundColor: '#ffffff',
    });

    // Resize canvas to fit container
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Setup drawing
    fabricCanvas.freeDrawingBrush.color = '#000000';
    fabricCanvas.freeDrawingBrush.width = 3;

    // Save to history after drawing
    fabricCanvas.on('path:created', () => {
        saveToHistory();
        broadcastCanvas();
    });

    fabricCanvas.on('object:modified', () => {
        saveToHistory();
        broadcastCanvas();
    });

    // Initial history state
    saveToHistory();
}

function resizeCanvas() {
    const container = document.getElementById('whiteboardContainer');
    fabricCanvas.setWidth(container.clientWidth);
    fabricCanvas.setHeight(container.clientHeight);
    fabricCanvas.renderAll();
}

function saveToHistory() {
    canvasHistory = canvasHistory.slice(0, historyIndex + 1);
    canvasHistory.push(JSON.stringify(fabricCanvas.toJSON()));
    historyIndex = canvasHistory.length - 1;
    updateUndoRedoButtons();
}

function updateUndoRedoButtons() {
    document.getElementById('undoBtn').disabled = historyIndex <= 0;
    document.getElementById('redoBtn').disabled = historyIndex >= canvasHistory.length - 1;
}

function undo() {
    if (historyIndex > 0) {
        historyIndex--;
        fabricCanvas.loadFromJSON(canvasHistory[historyIndex], () => {
            fabricCanvas.renderAll();
            broadcastCanvas();
        });
        updateUndoRedoButtons();
    }
}

function redo() {
    if (historyIndex < canvasHistory.length - 1) {
        historyIndex++;
        fabricCanvas.loadFromJSON(canvasHistory[historyIndex], () => {
            fabricCanvas.renderAll();
            broadcastCanvas();
        });
        updateUndoRedoButtons();
    }
}

function clearCanvas() {
    if (confirm('Clear entire whiteboard?')) {
        fabricCanvas.clear();
        fabricCanvas.backgroundColor = '#ffffff';
        fabricCanvas.renderAll();
        saveToHistory();
        broadcastCanvas();
    }
}

// ================== WEBSOCKET SETUP ==================
function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = websocketUrl.replace('ws://', protocol + '//');

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
        console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
        console.log('WebSocket disconnected');
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'whiteboard_update':
            // Only apply if from others (not self)
            if (data.user !== userName) {
                applyCanvasUpdate(data.content);
            }
            break;
        case 'user_joined':
            console.log('User joined:', data.user);
            showNotification(`${data.user} joined the session`);
            break;
        case 'user_left':
            console.log('User left:', data.user);
            showNotification(`${data.user} left the session`);
            break;
        case 'chat_message':
            // Handle chat if implemented
            break;
    }
}

function broadcastCanvas() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        const canvasData = JSON.stringify(fabricCanvas.toJSON());
        ws.send(JSON.stringify({
            type: 'whiteboard_update',
            content: canvasData,
        }));
    }
}

function applyCanvasUpdate(content) {
    fabricCanvas.loadFromJSON(content, () => {
        fabricCanvas.renderAll();
    });
}

// ================== EVENT LISTENERS ==================
function setupEventListeners() {
    // Video controls
    document.getElementById('muteAudioBtn').addEventListener('click', toggleAudio);
    document.getElementById('muteVideoBtn').addEventListener('click', toggleVideo);
    document.getElementById('leaveBtn').addEventListener('click', leaveSession);
    document.getElementById('toggleVideoPanel').addEventListener('click', toggleVideoPanel);

    // Whiteboard tools
    document.getElementById('penBtn').addEventListener('click', () => setTool('pen'));
    document.getElementById('eraserBtn').addEventListener('click', () => setTool('eraser'));
    document.getElementById('selectBtn').addEventListener('click', () => setTool('select'));
    document.getElementById('colorPicker').addEventListener('input', changeColor);
    document.getElementById('brushSize').addEventListener('input', changeBrushSize);
    document.getElementById('undoBtn').addEventListener('click', undo);
    document.getElementById('redoBtn').addEventListener('click', redo);
    document.getElementById('clearBtn').addEventListener('click', clearCanvas);

    // Save whiteboard (lecturer only)
    if (isLecturer) {
        document.getElementById('saveWhiteboardBtn').addEventListener('click', saveWhiteboard);
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey || e.metaKey) {
            if (e.key === 'z') {
                e.preventDefault();
                undo();
            } else if (e.key === 'y') {
                e.preventDefault();
                redo();
            }
        }
    });
}

// ================== VIDEO CONTROLS ==================
async function toggleAudio() {
    if (rtc.localAudioTrack) {
        await rtc.localAudioTrack.setEnabled(!isAudioMuted);
        isAudioMuted = !isAudioMuted;

        const btn = document.getElementById('muteAudioBtn');
        btn.innerHTML = isAudioMuted ? '<i class="bi bi-mic-mute-fill"></i>' : '<i class="bi bi-mic-fill"></i>';
        btn.classList.toggle('muted', isAudioMuted);
    }
}

async function toggleVideo() {
    if (rtc.localVideoTrack) {
        await rtc.localVideoTrack.setEnabled(!isVideoMuted);
        isVideoMuted = !isVideoMuted;

        const btn = document.getElementById('muteVideoBtn');
        btn.innerHTML = isVideoMuted ? '<i class="bi bi-camera-video-off-fill"></i>' : '<i class="bi bi-camera-video-fill"></i>';
        btn.classList.toggle('off', isVideoMuted);
    }
}

async function leaveSession() {
    if (confirm('Leave this session?')) {
        await leaveAgoraChannel();
        if (ws) {
            ws.close();
        }
        window.location.href = isLecturer ? '/virtual-class/live-sessions/' : '/virtual-class/student/live-sessions/';
    }
}

function toggleVideoPanel() {
    const panel = document.getElementById('videoPanel');
    panel.classList.toggle('minimized');

    const icon = document.querySelector('#toggleVideoPanel i');
    icon.className = panel.classList.contains('minimized') ? 'bi bi-arrows-angle-expand' : 'bi bi-arrows-angle-contract';
}

// ================== WHITEBOARD CONTROLS ==================
function setTool(tool) {
    currentTool = tool;

    // Update button states
    document.querySelectorAll('.btn-tool').forEach(btn => btn.classList.remove('active'));

    if (tool === 'pen') {
        document.getElementById('penBtn').classList.add('active');
        fabricCanvas.isDrawingMode = true;
        fabricCanvas.freeDrawingBrush = new fabric.PencilBrush(fabricCanvas);
        fabricCanvas.freeDrawingBrush.color = document.getElementById('colorPicker').value;
        fabricCanvas.freeDrawingBrush.width = parseInt(document.getElementById('brushSize').value);
    } else if (tool === 'eraser') {
        document.getElementById('eraserBtn').classList.add('active');
        fabricCanvas.isDrawingMode = true;
        fabricCanvas.freeDrawingBrush = new fabric.EraserBrush(fabricCanvas);
        fabricCanvas.freeDrawingBrush.width = parseInt(document.getElementById('brushSize').value);
    } else if (tool === 'select') {
        document.getElementById('selectBtn').classList.add('active');
        fabricCanvas.isDrawingMode = false;
        fabricCanvas.selection = true;
    }
}

function changeColor(e) {
    const color = e.target.value;
    if (currentTool === 'pen' && fabricCanvas.freeDrawingBrush) {
        fabricCanvas.freeDrawingBrush.color = color;
    }
}

function changeBrushSize(e) {
    const size = parseInt(e.target.value);
    if (fabricCanvas.freeDrawingBrush) {
        fabricCanvas.freeDrawingBrush.width = size;
    }
}

function saveWhiteboard() {
    const canvasData = JSON.stringify(fabricCanvas.toJSON());
    const statusEl = document.getElementById('saveStatus');

    statusEl.textContent = 'Saving...';

    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('content', canvasData);

    fetch('/virtual-class/ajax/save-session-whiteboard/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            statusEl.textContent = 'Saved!';
            setTimeout(() => { statusEl.textContent = ''; }, 2000);
        } else {
            statusEl.textContent = 'Save failed!';
        }
    })
    .catch(error => {
        console.error('Save error:', error);
        statusEl.textContent = 'Error!';
    });
}

// ================== UTILITIES ==================
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showNotification(message) {
    // Simple notification - you can enhance this
    console.log('Notification:', message);

    // You could add a toast notification here
}

// ================== CLEANUP ==================
window.addEventListener('beforeunload', async () => {
    await leaveAgoraChannel();
    if (ws) {
        ws.close();
    }
});