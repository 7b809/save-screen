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

function updateStatus(message, type = "secondary") {
  statusBox.className = `alert alert-${type} mt-3`;
  statusBox.textContent = message;
}

startBtn.onclick = async () => {
  console.log("🚀 [Start Sharing] Clicked");

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
        console.log(`📦 Captured chunk #${recordedChunks.length} (${event.data.size} bytes). Total buffered chunks: ${recordedChunks.length}`);

        // Create a complete, valid WebM Blob containing all headers + data accumulated so far
        const completeBlob = new Blob(recordedChunks, { type: "video/webm" });
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
  console.log("🛑 Stopping sharing session...");
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
  console.log(`📤 Sending Part #${index} (Cumulative Size: ${(completeBlob.size / 1024 / 1024).toFixed(2)} MB)...`);

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

    console.log(`✅ Server saved Part #${index}:`, result);
    updateStatus(`Live recording active: Saved part #${index} (${(completeBlob.size / 1024 / 1024).toFixed(2)} MB)`, "info");

  } catch (error) {
    console.error(`❌ Batch #${index} upload failed:`, error);
    updateStatus(`Batch #${index} upload error: ${error.message}`, "warning");
  }
}