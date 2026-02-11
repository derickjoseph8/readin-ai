/**
 * ReadIn AI - Offscreen Audio Processor
 *
 * Handles audio capture from tab and sends to background script
 */

const SAMPLE_RATE = 16000;
const BUFFER_SIZE = 4096;

let mediaStream = null;
let audioContext = null;
let processor = null;
let isCapturing = false;

/**
 * Start capturing audio from the stream
 */
async function startCapture(streamId) {
  if (isCapturing) {
    console.log('Already capturing');
    return;
  }

  try {
    // Get media stream from stream ID
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId,
        },
      },
      video: false,
    });

    // Create audio context
    audioContext = new AudioContext({ sampleRate: SAMPLE_RATE });

    // Create source from media stream
    const source = audioContext.createMediaStreamSource(mediaStream);

    // Create script processor for audio data access
    processor = audioContext.createScriptProcessor(BUFFER_SIZE, 1, 1);

    processor.onaudioprocess = (event) => {
      if (!isCapturing) return;

      const inputData = event.inputBuffer.getChannelData(0);

      // Convert Float32Array to Int16Array for efficient transmission
      const int16Data = new Int16Array(inputData.length);
      for (let i = 0; i < inputData.length; i++) {
        // Clamp and convert to 16-bit integer
        const s = Math.max(-1, Math.min(1, inputData[i]));
        int16Data[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
      }

      // Send audio data to background script
      chrome.runtime.sendMessage({
        type: 'AUDIO_DATA',
        target: 'background',
        data: Array.from(int16Data),
        sampleRate: SAMPLE_RATE,
      });
    };

    // Connect the audio graph
    source.connect(processor);
    processor.connect(audioContext.destination);

    isCapturing = true;
    console.log('Audio capture started');
  } catch (error) {
    console.error('Failed to start audio capture:', error);
    stopCapture();
  }
}

/**
 * Stop capturing audio
 */
function stopCapture() {
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
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.target !== 'offscreen') {
    return;
  }

  switch (message.type) {
    case 'START_CAPTURE':
      startCapture(message.streamId);
      break;
    case 'STOP_CAPTURE':
      stopCapture();
      break;
  }
});

console.log('Offscreen audio processor ready');
