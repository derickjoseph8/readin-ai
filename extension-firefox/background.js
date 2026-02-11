/**
 * ReadIn AI Browser Extension - Background Script (Firefox)
 *
 * Handles:
 * - Communication with desktop app via WebSocket
 * - Meeting detection
 * - Audio capture coordination
 */

// Configuration
const CONFIG = {
  DESKTOP_APP_WS_URL: 'ws://localhost:8765',
  RECONNECT_INTERVAL: 5000,
};

// State
let state = {
  isCapturing: false,
  isConnected: false,
  currentTabId: null,
  websocket: null,
  reconnectTimer: null,
  mediaStream: null,
  audioContext: null,
  processor: null,
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
      browser.runtime.sendMessage({ type: 'CONNECTION_STATUS', connected: true }).catch(() => {});

      // Send handshake
      state.websocket.send(JSON.stringify({
        type: 'handshake',
        source: 'browser_extension_firefox',
        version: '1.0.0'
      }));
    };

    state.websocket.onclose = () => {
      console.log('Disconnected from desktop app');
      state.isConnected = false;
      browser.runtime.sendMessage({ type: 'CONNECTION_STATUS', connected: false }).catch(() => {});
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
 * Start capturing audio from a tab (Firefox approach using content script)
 */
async function startCapture(tabId) {
  if (state.isCapturing) {
    console.log('Already capturing');
    return { success: false, error: 'Already capturing' };
  }

  try {
    const tab = await browser.tabs.get(tabId);
    const meetingName = detectMeeting(tab.url);

    // For Firefox, we'll inject a content script to capture audio
    // using the getDisplayMedia API
    await browser.tabs.sendMessage(tabId, {
      type: 'START_AUDIO_CAPTURE',
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
    browser.browserAction.setBadgeText({ text: 'ON' });
    browser.browserAction.setBadgeBackgroundColor({ color: '#22c55e' });

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

  // Tell content script to stop
  if (state.currentTabId) {
    browser.tabs.sendMessage(state.currentTabId, {
      type: 'STOP_AUDIO_CAPTURE',
    }).catch(() => {});
  }

  // Clean up local resources
  if (state.processor) {
    state.processor.disconnect();
    state.processor = null;
  }

  if (state.audioContext) {
    state.audioContext.close();
    state.audioContext = null;
  }

  if (state.mediaStream) {
    state.mediaStream.getTracks().forEach(track => track.stop());
    state.mediaStream = null;
  }

  state.isCapturing = false;
  state.currentTabId = null;

  // Notify desktop app
  if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
    state.websocket.send(JSON.stringify({
      type: 'capture_stopped',
    }));
  }

  // Update extension icon
  browser.browserAction.setBadgeText({ text: '' });
}

/**
 * Handle audio data from content script
 */
function handleAudioData(audioData) {
  if (state.websocket && state.websocket.readyState === WebSocket.OPEN) {
    // Send as JSON with audio array
    state.websocket.send(JSON.stringify({
      type: 'AUDIO_DATA',
      data: audioData.data,
      sampleRate: audioData.sampleRate || 16000,
    }));
  }
}

// Message listener
browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
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
      // Audio data from content script
      handleAudioData(message);
      break;

    case 'MEETING_DETECTED':
      // Content script detected a meeting
      if (state.isConnected && !state.isCapturing) {
        browser.notifications.create({
          type: 'basic',
          iconUrl: 'icons/icon128.png',
          title: 'Meeting Detected',
          message: `${message.meetingName} detected. Click to start ReadIn AI.`,
        });
      }
      break;
  }
});

// Tab update listener - detect when user joins a meeting
browser.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    const meetingName = detectMeeting(tab.url);
    if (meetingName) {
      console.log(`Meeting detected: ${meetingName}`);
      state.currentTabId = tabId;

      browser.runtime.sendMessage({
        type: 'MEETING_DETECTED',
        tabId: tabId,
        meetingName: meetingName,
        url: tab.url,
      }).catch(() => {});
    }
  }
});

// Tab closed listener
browser.tabs.onRemoved.addListener((tabId) => {
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

console.log('ReadIn AI Firefox extension background service started');
