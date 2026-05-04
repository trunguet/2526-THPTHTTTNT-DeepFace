/**
 * Face Scan Module
 * Manages webcam stream, frame capture, and face verification request.
 */

class FaceScanModule {
  constructor() {
    this.videoElement = document.getElementById('video-stream');
    this.canvasElement = document.getElementById('canvas-stream');
    this.captureBtn = document.getElementById('capture-btn');
    this.startBtn = document.getElementById('start-btn');
    this.stopBtn = document.getElementById('stop-btn');
    this.statusDisplay = document.getElementById('status-display');
    this.resultContainer = document.getElementById('result-container');

    this.mediaStream = null;
    this.isRunning = false;
    this.isProcessing = false;

    this.init();
  }

  init() {
    if (!this.videoElement || !this.canvasElement) return;

    this.startBtn?.addEventListener('click', () => this.startWebcam());
    this.stopBtn?.addEventListener('click', () => this.stopWebcam());
    this.captureBtn?.addEventListener('click', () => this.captureAndVerify());
    this.checkCameraSupport();
  }

  checkCameraSupport() {
    if (!navigator.mediaDevices?.getUserMedia) {
      this.showStatus('Trinh duyet khong ho tro camera hoac can HTTPS/localhost', 'error');
      if (this.startBtn) this.startBtn.disabled = true;
      return;
    }

    this.showStatus('Camera san sang. Bam khoi dong de cap quyen.', 'info');
  }

  async startWebcam() {
    try {
      if (this.mediaStream) return;

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' },
        audio: false,
      });

      this.mediaStream = stream;
      this.videoElement.srcObject = stream;
      await this.videoElement.play();

      this.isRunning = true;
      this.updateButtonStates();
      this.showStatus('Camera dang chay', 'info');
    } catch (error) {
      this.showStatus(`Loi khoi dong camera: ${error.message}`, 'error');
      console.error('Webcam error:', error);
    }
  }

  stopWebcam() {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    this.videoElement.srcObject = null;
    this.isRunning = false;
    this.updateButtonStates();
    this.showStatus('Camera da dung', 'info');
  }

  async captureAndVerify() {
    if (!this.isRunning) {
      this.showStatus('Vui long khoi dong camera truoc', 'error');
      return;
    }

    if (this.isProcessing) return;

    this.isProcessing = true;
    if (this.captureBtn) this.captureBtn.disabled = true;
    this.showStatus('Dang xac thuc...', 'info');

    try {
      const frameBase64 = this.captureFrame();
      const result = await this.verifyFace(frameBase64);
      this.displayResult(result);
    } catch (error) {
      this.showStatus(`Loi xac thuc: ${error.message}`, 'error');
      console.error('Verification error:', error);
    } finally {
      this.isProcessing = false;
      this.updateButtonStates();
    }
  }

  captureFrame() {
    const context = this.canvasElement.getContext('2d');
    this.canvasElement.width = this.videoElement.videoWidth;
    this.canvasElement.height = this.videoElement.videoHeight;

    if (!this.canvasElement.width || !this.canvasElement.height) {
      throw new Error('Camera chua san sang khung hinh');
    }

    context.drawImage(this.videoElement, 0, 0);
    return this.canvasElement.toDataURL('image/jpeg', 0.85);
  }

  async verifyFace(frameBase64) {
    return await DeepFaceAPI.post('/api/access/verify-face', {
      image: frameBase64,
    });
  }

  displayResult(result) {
    if (!this.resultContainer) return;

    const status = result.status || (result.recognized ? 'allowed' : 'not_implemented');
    const confidence = Number(result.confidence ?? 0);
    const snapshotHTML = result.snapshot_url
      ? `
        <div style="margin-top: 14px">
          <img src="${DeepFaceAPI.escapeHTML(result.snapshot_url)}" alt="Snapshot" style="max-width: 220px; width: 100%; border-radius: 8px; border: 1px solid rgba(124,196,237,0.35)" />
          <p class="result-hint"><a href="${DeepFaceAPI.escapeHTML(result.snapshot_url)}" target="_blank" rel="noreferrer" style="color: #7cc4ed">Mo anh da luu</a></p>
        </div>
      `
      : '';
    let html = '';
    let className = 'result-card result-warning';
    let statusMessage = 'Backend chua tra ket qua nhan dien hoan chinh';
    let statusType = 'warning';

    if (status === 'allowed') {
      className = 'result-card result-success';
      statusMessage = 'Xac thuc thanh cong';
      statusType = 'success';
      html = `
        <div class="result-icon">OK</div>
        <h2>Chao mung</h2>
        <p class="result-name">${DeepFaceAPI.escapeHTML(result.employee_name || 'Nhan vien')}</p>
        <p class="result-message">Xac thuc thanh cong</p>
        <p class="result-confidence">Do tin cay: ${(confidence * 100).toFixed(2)}%</p>
        ${snapshotHTML}
      `;
    } else if (status === 'denied') {
      className = 'result-card result-error';
      statusMessage = 'Xac thuc that bai';
      statusType = 'error';
      html = `
        <div class="result-icon">NO</div>
        <h2>Xac thuc that bai</h2>
        <p class="result-message">${DeepFaceAPI.escapeHTML(result.message || 'Khuon mat khong khop voi du lieu')}</p>
        <p class="result-hint">Vui long lien he quan tri vien</p>
        ${snapshotHTML}
      `;
    } else if (status === 'stranger') {
      className = 'result-card result-warning';
      statusMessage = 'Phat hien nguoi la';
      statusType = 'warning';
      html = `
        <div class="result-icon">!</div>
        <h2>Nguoi la phat hien</h2>
        <p class="result-message">Khuon mat khong xac dinh trong he thong</p>
        <p class="result-confidence">Do tin cay: ${(confidence * 100).toFixed(2)}%</p>
        <p class="result-hint">Quan tri vien can kiem tra canh bao</p>
        ${snapshotHTML}
      `;
    } else {
      html = `
        <div class="result-icon">!</div>
        <h2>Backend chua san sang</h2>
        <p class="result-message">${DeepFaceAPI.escapeHTML(result.message || 'API nhan dien khuon mat chua duoc implement')}</p>
        <p class="result-hint">Frontend da gui anh thanh cong. Backend can tra status allowed/denied/stranger.</p>
        ${snapshotHTML}
      `;
    }

    const resultDiv = document.createElement('div');
    resultDiv.className = className;
    resultDiv.innerHTML = html;
    this.resultContainer.replaceChildren(resultDiv);
    this.showStatus(statusMessage, statusType);
  }

  updateButtonStates() {
    if (this.startBtn) this.startBtn.disabled = this.isRunning;
    if (this.stopBtn) this.stopBtn.disabled = !this.isRunning;
    if (this.captureBtn) this.captureBtn.disabled = !this.isRunning || this.isProcessing;
  }

  showStatus(message, type) {
    if (!this.statusDisplay) return;
    this.statusDisplay.textContent = message;
    this.statusDisplay.className = `status-display status-${type}`;
    this.statusDisplay.style.display = 'block';
  }

  destroy() {
    this.stopWebcam();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.faceScanModule = new FaceScanModule();
});

window.addEventListener('beforeunload', () => {
  window.faceScanModule?.destroy();
});
