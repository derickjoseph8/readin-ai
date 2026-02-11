/**
 * ReadIn AI Browser Extension - Background Service Worker
 *
 * Handles:
 * - Tab audio capture
 * - Communication with desktop app via WebSocket
 * - Meeting detection
 */

// Configuration
const CONFIG = {
  DESKTOP_APP_WS_URL: 'ws://localhost:8765',
  DESKTOP_APP_HTTP_URL: 'http://localhost:8765',
  RECONNECT_INTERVAL: 5000,
  AUDIO_SAMPLE_RATE: 16000,
  AUDIO_CHUNK_MS: 100,
};

// State
let state = {
  isCapturing: false,
  isConnected: false,
  currentTabId: null,
  mediaStream: null,
  audioContext: null,
  websocket: null,
  reconnectTimer: null,
};

// Meeting URL patterns
const MEETING_PATTERNS = [
  { pattern: /meet\.google\.com\/[a-z]+-[a-z]+-[a-z]+/i, name: 'Google Meet' },
  { pattern: /zoom\.us\/(j|wc)\/\d+/i, name: 'Zoom' },
  { pattern: /webex\.com\/meet\//i, name: 'Webex' },
  { pattern: /teams\.microsoft\.com.*\/meeting/i, name: 'Microsoft Teams' },
  { pattern: /teams\.live\.com/i, name: 'Microsoft Teams' },
];

/**
 * Check if a URL is a meeting URL
 */
function detectMeeting(url) {
  for (const { pattern, name } of MEETING_PATTERNS) {
    if (pattern.test(url)) {
      return name;
    }
  }
  return null;
}

/**
 * Connect to the desktop app via WebSocket
 */
function connectToDesktopApp() {
  if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
    return;
  }

  try {
    state.websocket = new WebSocket(CONFIG.DESKTOP_APP_WS_URL);

    state.websocket.onopen = () => {
      console.log('Connected to ReadIn AI desktop app');
      state.isConnected = true;
      clearTimeout(state.reconnectTimer);

      // Notify popup of connection
      chrome.runtime.sendMessage({ type: 'CONNECTION_STATUS', connected: true });

      // Send handshake
      state.websocket.send(JSON.stringify({
        type: 'handshake',
        source: 'browser_extension',
        version: '1.0.0'
      }));
    };

    state.websocket.onclose = () => {
      console.log('Disconnected from desktop app');
      state.isConnected = false;
      chrome.runtime.sendMessage({ type: 'CONNECTION_STATUS', connected: false });

      // Attempt to reconnect
      scheduleReconnect();
    };

    state.websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
      state.isConnected = false;
    };

    state.websocket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        handleDesktopMessage(message);
      } catch (e) {
        console.error('Error parsing message:', e);
      }
    };
  } catch (error) {
    console.error('Failed to connect:', error);
    scheduleReconnect();
  }
}

/**
 * Schedule a reconnection attempt
 */
function scheduleReconnect() {
  if (state.reconnectTimer) {
    clearTimeout(state.reconnectTimer);
  }
  state.reconnectTimer = setTimeout(connectToDesktopApp, CONFIG.RECONNECT_INTERVAL);
}

/**
 * Handle messages from the desktop app
 */
function handleDesktopMessage(message) {
  switch (message.type) {
    case 'start_capture':
      if (state.currentTabId) {
        startCapture(state.currentTabId);
      }
      break;
    case 'stop_capture':
      stopCapture();
      break;
    case 'status_request':
      sendStatus();
      break;
  }
}

/**
 * Send current status to desktop app
 */
function sendStatus() {
  if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
    state.websocket.send(JSON.stringify({
      type: 'status',
      isCapturing: state.isCapturing,
      currentTabId: state.currentTabId,
    }));
  }
}

/**
 * Start capturing audio from a tab
 */
async function startCapture(tabId) {
  if (state.isCapturing) {
    console.log('Already capturing');
    return { success: false, error: 'Already capturing' };
  }

  try {
    // Get the tab info
    const tab = await chrome.tabs.get(tabId);
    const meetingName = detectMeeting(tab.url);

    // Request tab capture
    const streamId = await chrome.tabCapture.getMediaStreamId({
      targetTabId: tabId
    });

    // Create offscreen document for audio processing
    await createOffscreenDocument();

    // Send stream ID to offscreen document
    chrome.runtime.sendMessage({
      type: 'START_CAPTURE',
      target: 'offscreen',
      streamId: streamId,
      tabId: tabId,
    });

    state.isCapturing = true;
    state.currentTabId = tabId;

    // Notify desktop app
    if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
      state.websocket.send(JSON.stringify({
        type: 'capture_started',
        tabId: tabId,
        meetingName: meetingName,
        url: tab.url,
      }));
    }

    // Update extension icon
    chrome.action.setBadgeText({ text: 'ON' });
    chrome.action.setBadgeBackgroundColor({ color: '#22c55e' });

    return { success: true, meetingName };
  } catch (error) {
    console.error('Failed to start capture:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Stop capturing audio
 */
async function stopCapture() {
  if (!state.isCapturing) {
    return;
  }

  // Tell offscreen document to stop
  chrome.runtime.sendMessage({
    type: 'STOP_CAPTURE',
    target: 'offscreen',
  });

  state.isCapturing = false;
  state.currentTabId = null;

  // Notify desktop app
  if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
    state.websocket.send(JSON.stringify({
      type: 'capture_stopped',
    }));
  }

  // Update extension icon
  chrome.action.setBadgeText({ text: '' });

  // Close offscreen document
  await closeOffscreenDocument();
}

/**
 * Create offscreen document for audio processing
 */
async function createOffscreenDocument() {
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT'],
  });

  if (existingContexts.length > 0) {
    return;
  }

  await chrome.offscreen.createDocument({
    url: 'offscreen.html',
    reasons: ['USER_MEDIA'],
    justification: 'Recording audio from tab for meeting transcription',
  });
}

/**
 * Close offscreen document
 */
async function closeOffscreenDocument() {
  const existingContexts = await chrome.runtime.getContexts({
    contextTypes: ['OFFSCREEN_DOCUMENT'],
  });

  if (existingContexts.length > 0) {
    await chrome.offscreen.closeDocument();
  }
}

/**
 * Handle audio data from offscreen document
 */
function handleAudioData(audioData) {
  if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
    state.websocket.send(audioData);
  }
}

// Message listener
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('Background received message:', message.type);

  switch (message.type) {
    case 'GET_STATUS':
      sendResponse({
        isCapturing: state.isCapturing,
        isConnected: state.isConnected,
        currentTabId: state.currentTabId,
      });
      break;

    case 'START_CAPTURE_REQUEST':
      startCapture(message.tabId).then(sendResponse);
      return true; // Will respond asynchronously

    case 'STOP_CAPTURE_REQUEST':
      stopCapture();
      sendResponse({ success: true });
      break;

    case 'CONNECT_REQUEST':
      connectToDesktopApp();
      sendResponse({ success: true });
      break;

    case 'AUDIO_DATA':
      // Forward audio data from offscreen document to desktop app
      if (message.target === 'background') {
        handleAudioData(message.data);
      }
      break;

    case 'MEETING_DETECTED':
      // Content script detected a meeting
      if (state.isConnected && !state.isCapturing) {
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icons/icon128.png',
          title: 'Meeting Detected',
          message: `${message.meetingName} detected. Click to start ReadIn AI.`,
        });
      }
      break;
  }

  return false;
});

// Tab update listener - detect when user joins a meeting
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    const meetingName = detectMeeting(tab.url);
    if (meetingName) {
      console.log(`Meeting detected: ${meetingName}`);

      // Notify popup
      chrome.runtime.sendMessage({
        type: 'MEETING_DETECTED',
        tabId: tabId,
        meetingName: meetingName,
        url: tab.url,
      });
    }
  }
});

// Tab closed listener - stop capture if active tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
  if (tabId === state.currentTabId) {
    stopCapture();
  }
});

// Initialize connection on startup
connectToDesktopApp();

// Periodic connection check
setInterval(() => {
  if (!state.isConnected) {
    connectToDesktopApp();
  }
}, CONFIG.RECONNECT_INTERVAL);

console.log('ReadIn AI extension background service started');
