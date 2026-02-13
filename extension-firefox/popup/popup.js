/**
 * ReadIn AI - Extension Popup (Firefox)
 *
 * Handles UI interactions and communication with background script
 */

// DOM Elements
const elements = {
  connectionStatus: document.getElementById('connectionStatus'),
  disconnectedWarning: document.getElementById('disconnectedWarning'),
  connectedInfo: document.getElementById('connectedInfo'),
  meetingIcon: document.getElementById('meetingIcon'),
  meetingName: document.getElementById('meetingName'),
  meetingUrl: document.getElementById('meetingUrl'),
  captureBtn: document.getElementById('captureBtn'),
  captureStatus: document.getElementById('captureStatus'),
  openDashboardBtn: document.getElementById('openDashboardBtn'),
  openSettingsBtn: document.getElementById('openSettingsBtn'),
  openHelpBtn: document.getElementById('openHelpBtn'),
};

// State
let state = {
  isConnected: false,
  isCapturing: false,
  currentTabId: null,
  meetingName: null,
};

// Meeting platform configurations
const MEETING_PLATFORMS = {
  'Google Meet': { iconClass: 'google-meet', emoji: '🎥' },
  'Zoom': { iconClass: 'zoom', emoji: '🎦' },
  'Microsoft Teams': { iconClass: 'teams', emoji: '👥' },
  'Webex': { iconClass: 'webex', emoji: '📹' },
};

/**
 * Initialize popup
 */
async function init() {
  // Get current status from background
  browser.runtime.sendMessage({ type: 'GET_STATUS' }).then((response) => {
    if (response) {
      state.isConnected = response.isConnected;
      state.isCapturing = response.isCapturing;
      state.currentTabId = response.currentTabId;
      updateUI();
    }
  }).catch(() => {});

  // Check current tab for meeting
  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  if (tabs[0]) {
    checkForMeeting(tabs[0]);
  }

  // Setup event listeners
  setupEventListeners();

  // Listen for status updates
  browser.runtime.onMessage.addListener(handleMessage);
}

/**
 * Check if current tab is a meeting
 */
function checkForMeeting(tab) {
  const url = tab.url || '';
  state.currentTabId = tab.id;

  // Check for meeting patterns
  const meetingPatterns = [
    { pattern: /meet\.google\.com\/[a-z]+-[a-z]+-[a-z]+/i, name: 'Google Meet' },
    { pattern: /zoom\.us\/(j|wc)\/\d+/i, name: 'Zoom' },
    { pattern: /webex\.com\/meet\//i, name: 'Webex' },
    { pattern: /teams\.microsoft\.com.*\/meeting/i, name: 'Microsoft Teams' },
    { pattern: /teams\.live\.com/i, name: 'Microsoft Teams' },
  ];

  for (const { pattern, name } of meetingPatterns) {
    if (pattern.test(url)) {
      state.meetingName = name;
      updateMeetingInfo(name, url);
      return;
    }
  }

  // No meeting detected
  state.meetingName = null;
  updateMeetingInfo(null, url);
}

/**
 * Update meeting info display
 */
function updateMeetingInfo(meetingName, url) {
  if (meetingName) {
    const platform = MEETING_PLATFORMS[meetingName] || { iconClass: '', emoji: '🎥' };

    elements.meetingIcon.className = `meeting-icon ${platform.iconClass}`;
    elements.meetingIcon.textContent = platform.emoji;
    elements.meetingName.textContent = meetingName;
    try {
      elements.meetingUrl.textContent = new URL(url).hostname;
    } catch {
      elements.meetingUrl.textContent = url;
    }

    // Enable capture button if connected
    if (state.isConnected) {
      elements.captureBtn.disabled = false;
    }
  } else {
    elements.meetingIcon.className = 'meeting-icon';
    elements.meetingIcon.textContent = '📷';
    elements.meetingName.textContent = 'No meeting detected';
    elements.meetingUrl.textContent = 'Open a meeting to get started';
    elements.captureBtn.disabled = true;
  }
}

/**
 * Update UI based on state
 */
function updateUI() {
  // Connection status
  const statusDot = elements.connectionStatus.querySelector('.status-dot');
  const statusText = elements.connectionStatus.querySelector('.status-text');

  if (state.isConnected) {
    statusDot.className = 'status-dot connected';
    statusText.textContent = 'Connected';
    elements.disconnectedWarning.classList.add('hidden');
    elements.connectedInfo.classList.remove('hidden');
  } else {
    statusDot.className = 'status-dot disconnected';
    statusText.textContent = 'Disconnected';
    elements.disconnectedWarning.classList.remove('hidden');
    elements.connectedInfo.classList.add('hidden');
  }

  // Capture button
  if (state.isCapturing) {
    elements.captureBtn.classList.remove('btn-primary');
    elements.captureBtn.classList.add('btn-danger');
    elements.captureBtn.querySelector('.btn-icon').textContent = '⬛';
    elements.captureBtn.querySelector('.btn-text').textContent = 'Stop Capture';
    elements.captureStatus.classList.remove('hidden');
  } else {
    elements.captureBtn.classList.remove('btn-danger');
    elements.captureBtn.classList.add('btn-primary');
    elements.captureBtn.querySelector('.btn-icon').textContent = '▶';
    elements.captureBtn.querySelector('.btn-text').textContent = 'Start Capture';
    elements.captureStatus.classList.add('hidden');
  }

  // Enable/disable capture button
  elements.captureBtn.disabled = !state.isConnected || !state.meetingName;
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
  // Capture button
  elements.captureBtn.addEventListener('click', toggleCapture);

  // Quick actions
  elements.openDashboardBtn.addEventListener('click', () => {
    browser.tabs.create({ url: 'https://www.getreadin.us/dashboard' });
  });

  elements.openSettingsBtn.addEventListener('click', () => {
    browser.tabs.create({ url: 'https://www.getreadin.us/dashboard/settings' });
  });

  elements.openHelpBtn.addEventListener('click', () => {
    browser.tabs.create({ url: 'https://www.getreadin.us/help' });
  });
}

/**
 * Toggle audio capture
 */
async function toggleCapture() {
  if (state.isCapturing) {
    // Stop capture
    browser.runtime.sendMessage({ type: 'STOP_CAPTURE_REQUEST' }).then((response) => {
      if (response && response.success) {
        state.isCapturing = false;
        updateUI();
      }
    });
  } else {
    // Start capture
    browser.runtime.sendMessage({
      type: 'START_CAPTURE_REQUEST',
      tabId: state.currentTabId
    }).then((response) => {
      if (response && response.success) {
        state.isCapturing = true;
        updateUI();
      } else if (response && response.error) {
        showError(response.error);
      }
    });
  }
}

/**
 * Handle messages from background script
 */
function handleMessage(message) {
  switch (message.type) {
    case 'CONNECTION_STATUS':
      state.isConnected = message.connected;
      updateUI();
      break;

    case 'CAPTURE_STARTED':
      state.isCapturing = true;
      updateUI();
      break;

    case 'CAPTURE_STOPPED':
      state.isCapturing = false;
      updateUI();
      break;
  }
}

/**
 * Show error message
 */
function showError(message) {
  alert(`Error: ${message}`);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);
