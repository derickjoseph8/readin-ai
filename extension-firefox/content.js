/**
 * ReadIn AI - Content Script (Firefox)
 *
 * Injected into meeting pages to detect meetings and capture audio
 */

const SAMPLE_RATE = 16000;
const BUFFER_SIZE = 4096;

// Audio capture state
let mediaStream = null;
let audioContext = null;
let processor = null;
let isCapturing = false;

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
    isInMeeting = true;
    onMeetingJoined();
  } else if (!inMeeting && isInMeeting) {
    isInMeeting = false;
    onMeetingLeft();
  }
}

/**
 * Called when user joins a meeting
 */
function onMeetingJoined() {
  console.log(`ReadIn AI: Joined ${meetingConfig.name}`);

  browser.runtime.sendMessage({
    type: 'MEETING_DETECTED',
    meetingName: meetingConfig.name,
    url: window.location.href,
  });

  showNotification();
}

/**
 * Called when user leaves a meeting
 */
function onMeetingLeft() {
  console.log(`ReadIn AI: Left ${meetingConfig.name}`);

  if (isCapturing) {
    stopAudioCapture();
  }

  browser.runtime.sendMessage({
    type: 'MEETING_LEFT',
    meetingName: meetingConfig.name,
  });
}

/**
 * Start capturing audio using getDisplayMedia
 */
async function startAudioCapture() {
  if (isCapturing) {
    console.log('Already capturing');
    return;
  }

  try {
    // Request display media with audio
    // This will prompt user to select what to share
    mediaStream = await navigator.mediaDevices.getDisplayMedia({
      video: true, // Required but we'll ignore it
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        sampleRate: SAMPLE_RATE,
      }
    });

    // Check if we got audio
    const audioTracks = mediaStream.getAudioTracks();
    if (audioTracks.length === 0) {
      throw new Error('No audio track in capture. Please share a tab with audio.');
    }

    // Stop video track (we only need audio)
    mediaStream.getVideoTracks().forEach(track => track.stop());

    // Create audio context
    audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });

    // Create source from media stream
    const source = audioContext.createMediaStreamSource(new MediaStream(audioTracks));

    // Create script processor for audio data access
    processor = audioContext.createScriptProcessor(BUFFER_SIZE, 1, 1);

    processor.onaudioprocess = (event) => {
      if (!isCapturing) return;

      const inputData = event.inputBuffer.getChannelData(0);

      // Convert Float32Array to Int16Array for efficient transmission
      const int16Data = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        const s = Math.max(-1, Math.min(1, inputData[i]));
        int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }

      // Send audio data to background script
      browser.runtime.sendMessage({
        type: 'AUDIO_DATA',
        data: Array.from(int16Data),
        sampleRate: SAMPLE_RATE,
      });
    };

    // Connect the audio graph
    source.connect(processor);
    processor.connect(audioContext.destination);

    isCapturing = true;
    console.log('Audio capture started');

    // Show indicator
    showCaptureIndicator();
  } catch (error) {
    console.error('Failed to start audio capture:', error);
    stopAudioCapture();

    // Show helpful error to user
    if (error.name === 'NotAllowedError') {
      alert('ReadIn AI: Please allow screen/tab sharing to capture meeting audio. Make sure to check "Share audio" when selecting what to share.');
    }
  }
}

/**
 * Stop capturing audio
 */
function stopAudioCapture() {
  isCapturing = false;

  if (processor) {
    processor.disconnect();
    processor = null;
  }

  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }

  console.log('Audio capture stopped');
  hideCaptureIndicator();
}

/**
 * Show capture indicator
 */
function showCaptureIndicator() {
  let indicator = document.getElementById('readin-capture-indicator');
  if (indicator) return;

  indicator = document.createElement('div');
  indicator.id = 'readin-capture-indicator';
  indicator.innerHTML = `
    <div style="
      position: fixed;
      top: 10px;
      right: 10px;
      background: rgba(34, 197, 94, 0.9);
      color: white;
      padding: 8px 16px;
      border-radius: 20px;
      font-family: -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 13px;
      font-weight: 500;
      z-index: 999999;
      display: flex;
      align-items: center;
      gap: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    ">
      <span style="
        width: 8px;
        height: 8px;
        background: white;
        border-radius: 50%;
        animation: pulse 1.5s infinite;
      "></span>
      ReadIn AI Recording
    </div>
    <style>
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
      }
    </style>
  `;
  document.body.appendChild(indicator);
}

/**
 * Hide capture indicator
 */
function hideCaptureIndicator() {
  const indicator = document.getElementById('readin-capture-indicator');
  if (indicator) {
    indicator.remove();
  }
}

/**
 * Show a subtle notification that ReadIn AI is available
 */
function showNotification() {
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

  document.getElementById('readin-close-btn').addEventListener('click', () => {
    notification.remove();
  });

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
browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  switch (message.type) {
    case 'CHECK_MEETING':
      sendResponse({
        isInMeeting: isInMeeting,
        meetingName: meetingConfig?.name,
      });
      break;
    case 'START_AUDIO_CAPTURE':
      startAudioCapture();
      break;
    case 'STOP_AUDIO_CAPTURE':
      stopAudioCapture();
      break;
  }
});

console.log('ReadIn AI Firefox content script loaded');
