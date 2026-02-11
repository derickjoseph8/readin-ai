/**
 * ReadIn AI - Content Script
 *
 * Injected into meeting pages to detect when user joins a meeting
 */

// Meeting detection configurations
const MEETING_CONFIGS = {
  'meet.google.com': {
    name: 'Google Meet',
    joinedSelector: '[data-meeting-code]',
    inMeetingSelector: '[data-self-name]',
  },
  'zoom.us': {
    name: 'Zoom',
    joinedSelector: '#wc-container-left',
    inMeetingSelector: '.meeting-client',
  },
  'webex.com': {
    name: 'Webex',
    joinedSelector: '[data-test="meeting-info-button"]',
    inMeetingSelector: '.meeting-container',
  },
  'teams.microsoft.com': {
    name: 'Microsoft Teams',
    joinedSelector: '[data-tid="call-control-bar"]',
    inMeetingSelector: '.ts-calling-screen',
  },
  'teams.live.com': {
    name: 'Microsoft Teams',
    joinedSelector: '[data-tid="call-control-bar"]',
    inMeetingSelector: '.ts-calling-screen',
  },
};

let currentHost = window.location.hostname;
let meetingConfig = null;
let isInMeeting = false;
let checkInterval = null;

/**
 * Initialize the content script
 */
function init() {
  // Find matching config
  for (const [host, config] of Object.entries(MEETING_CONFIGS)) {
    if (currentHost.includes(host)) {
      meetingConfig = config;
      break;
    }
  }

  if (!meetingConfig) {
    console.log('ReadIn AI: Not a supported meeting site');
    return;
  }

  console.log(`ReadIn AI: Monitoring ${meetingConfig.name}`);

  // Start checking for meeting join
  checkInterval = setInterval(checkMeetingStatus, 2000);

  // Also check on visibility change
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      checkMeetingStatus();
    }
  });
}

/**
 * Check if user has joined the meeting
 */
function checkMeetingStatus() {
  if (!meetingConfig) return;

  const inMeeting = !!(
    document.querySelector(meetingConfig.joinedSelector) ||
    document.querySelector(meetingConfig.inMeetingSelector)
  );

  if (inMeeting && !isInMeeting) {
    // Just joined meeting
    isInMeeting = true;
    onMeetingJoined();
  } else if (!inMeeting && isInMeeting) {
    // Left meeting
    isInMeeting = false;
    onMeetingLeft();
  }
}

/**
 * Called when user joins a meeting
 */
function onMeetingJoined() {
  console.log(`ReadIn AI: Joined ${meetingConfig.name}`);

  // Notify background script
  chrome.runtime.sendMessage({
    type: 'MEETING_DETECTED',
    meetingName: meetingConfig.name,
    url: window.location.href,
  });

  // Show notification badge
  showNotification();
}

/**
 * Called when user leaves a meeting
 */
function onMeetingLeft() {
  console.log(`ReadIn AI: Left ${meetingConfig.name}`);

  // Notify background script
  chrome.runtime.sendMessage({
    type: 'MEETING_LEFT',
    meetingName: meetingConfig.name,
  });
}

/**
 * Show a subtle notification that ReadIn AI is available
 */
function showNotification() {
  // Check if notification already exists
  if (document.getElementById('readin-ai-notification')) {
    return;
  }

  const notification = document.createElement('div');
  notification.id = 'readin-ai-notification';
  notification.innerHTML = `
    <div style="
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: linear-gradient(135deg, #1e1e1e 0%, #2d2d2d 100%);
      color: white;
      padding: 12px 20px;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.3);
      z-index: 999999;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      display: flex;
      align-items: center;
      gap: 12px;
      border: 1px solid rgba(34, 197, 94, 0.3);
      animation: slideIn 0.3s ease-out;
    ">
      <div style="
        width: 32px;
        height: 32px;
        background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
      ">R</div>
      <div>
        <div style="font-weight: 600;">ReadIn AI Ready</div>
        <div style="font-size: 12px; color: #9ca3af;">Click extension icon to start</div>
      </div>
      <button id="readin-close-btn" style="
        background: none;
        border: none;
        color: #9ca3af;
        cursor: pointer;
        padding: 4px;
        margin-left: 8px;
        font-size: 18px;
        line-height: 1;
      ">&times;</button>
    </div>
    <style>
      @keyframes slideIn {
        from {
          transform: translateX(100%);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }
    </style>
  `;

  document.body.appendChild(notification);

  // Close button handler
  document.getElementById('readin-close-btn').addEventListener('click', () => {
    notification.remove();
  });

  // Auto-hide after 10 seconds
  setTimeout(() => {
    if (notification.parentNode) {
      notification.style.animation = 'slideIn 0.3s ease-out reverse';
      setTimeout(() => notification.remove(), 300);
    }
  }, 10000);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Listen for messages from background
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'CHECK_MEETING':
      sendResponse({
        isInMeeting: isInMeeting,
        meetingName: meetingConfig?.name,
      });
      break;
  }
});

console.log('ReadIn AI content script loaded');
