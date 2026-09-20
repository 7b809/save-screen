const mode = document.getElementById("mode");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const preview = document.getElementById("preview");
const audioPreview = document.getElementById("audioPreview");
const statusBox = document.getElementById("status");

let stream = null;
let recorder = null;
let sessionId = null;
let partIndex = 1;
let recordedChunks = []; // Accumulates all chunks so every payload is a valid WebM file

// Configuration loaded dynamically from backend
let debugFlag = false;
let maxBatchSizeMB = 50; // Default limit in MB

// Custom Logger Wrapper
function log(message, ...args) {
  if (debugFlag) {
    console.log(message, ...args);
  }
}

function logInfo(message, ...args) {
  if (debugFlag) {
    console.info(message, ...args);
  }
}

function logWarn(message, ...args) {
  if (debugFlag) {
    console.warn(message, ...args);
  }
}

// Fetch backend configuration on startup
async function loadBackendConfig() {
  try {
    const response = await fetch("/api/config");
    if (response.ok) {
      const data = await response.json();
      debugFlag = Boolean(data.debug_flag);
      maxBatchSizeMB = Number(data.max_batch_size_mb) || 50;

      log(`🔧 Config loaded -> Debug: ${debugFlag}, Max Batch Size: ${maxBatchSizeMB} MB`);
    }
  } catch (error) {
    console.error("❌ Failed to load backend configuration:", error);
  }
}

// Initialize config on script load
loadBackendConfig();

function updateStatus(message, type = "secondary") {
  statusBox.className = `alert alert-${type} mt-3`;
  statusBox.textContent = message;
}

startBtn.onclick = async () => {
  log("🚀 [Start Sharing] Clicked");

  try {
    const selected = mode.value;
    const wantScreen = selected === "screen" || selected === "both";
    const wantAudio = selected === "audio" || selected === "both";

    let screenStream = null;
    let micStream = null;
    let tracks = [];

    if (wantScreen) {
      screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: wantAudio
      });
      tracks.push(...screenStream.getVideoTracks());
      if (screenStream.getAudioTracks().length) {
        tracks.push(...screenStream.getAudioTracks());
      }
    }

    if (wantAudio && (!screenStream || !screenStream.getAudioTracks().length)) {
      micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      tracks.push(...micStream.getAudioTracks());
    }

    stream = new MediaStream(tracks);
    preview.srcObject = wantScreen ? stream : null;
    audioPreview.srcObject = !wantScreen ? stream : null;

    sessionId = `session-${Date.now()}`;
    partIndex = 1;
    recordedChunks = []; // Reset recorded buffer for new session

    const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
      ? "video/webm;codecs=vp9"
      : "video/webm";

    recorder = new MediaRecorder(stream, { mimeType });

    // Store each slice in our cumulative array
    recorder.ondataavailable = async (event) => {
      if (event.data && event.data.size > 0) {
        recordedChunks.push(event.data);
        
        // Assemble current cumulative blob
        const completeBlob = new Blob(recordedChunks, { type: "video/webm" });
        const currentSizeMB = completeBlob.size / (1024 * 1024);

        log(`📦 Chunk #${recordedChunks.length} captured (${(event.data.size / 1024 / 1024).toFixed(2)} MB). Total: ${currentSizeMB.toFixed(2)} / ${maxBatchSizeMB} MB`);

        // Check if size limit has been reached
        if (currentSizeMB > maxBatchSizeMB) {
          logWarn(`⚠️ Cumulative size limit (${maxBatchSizeMB} MB) reached. Stopping recording...`);
          updateStatus(`Recording limit reached (${maxBatchSizeMB} MB). Auto-stopping...`, "warning");
          
          stopBtn.click();
          return;
        }

        await uploadBatchChunk(completeBlob, partIndex++);
      }
    };

    // Trigger ondataavailable every 5 seconds (5000ms)
    recorder.start(5000);

    startBtn.disabled = true;
    stopBtn.disabled = false;
    updateStatus("Sharing and live recording active...", "success");

    stream.getTracks().forEach(track => {
      track.onended = () => {
        if (recorder && recorder.state === "recording") {
          recorder.stop();
        }
      };
    });

  } catch (error) {
    console.error("❌ Error starting stream:", error);
    updateStatus(`Unable to start sharing: ${error.message}`, "danger");
  }
};

stopBtn.onclick = () => {
  log("🛑 Stopping sharing session...");
  if (recorder && recorder.state === "recording") {
    recorder.stop();
  }
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
  }
  startBtn.disabled = false;
  stopBtn.disabled = true;
  updateStatus("Sharing stopped.", "info");
};

async function uploadBatchChunk(completeBlob, index) {
  const currentSizeMB = (completeBlob.size / 1024 / 1024).toFixed(2);
  log(`📤 Sending Part #${index} (${currentSizeMB} MB / ${maxBatchSizeMB} MB max)...`);

  const formData = new FormData();
  formData.append("file", completeBlob, `part_${index}.webm`);
  formData.append("session_id", sessionId);
  formData.append("part_index", index);

  try {
    const response = await fetch("/api/recordings", {
      method: "POST",
      body: formData
    });

    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `HTTP Error ${response.status}`);

    logInfo(`✅ Server saved Part #${index}:`, result);
    updateStatus(`Live recording active: Saved part #${index} (${currentSizeMB} MB / ${maxBatchSizeMB} MB)`, "info");

  } catch (error) {
    console.error(`❌ Batch #${index} upload failed:`, error);
    updateStatus(`Batch #${index} upload error: ${error.message}`, "warning");
  }
}