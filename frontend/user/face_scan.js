/**
 * Face Scan Module
 * Manages webcam stream, face detection, identity verification, and status notifications
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

    this.apiBaseURL = this.getApiBaseURL();
    this.mediaStream = null;
    this.isRunning = false;
    this.isProcessing = false;

    this.init();
  }

  init() {
    if (this.startBtn) {
      this.startBtn.addEventListener('click', () => this.startWebcam());
    }
    if (this.stopBtn) {
      this.stopBtn.addEventListener('click', () => this.stopWebcam());
    }
    if (this.captureBtn) {
      this.captureBtn.addEventListener('click', () => this.captureAndVerify());
    }
    if (this.videoElement) {
      this.videoElement.addEventListener('loadedmetadata', () => this.markCameraReady());
      this.videoElement.addEventListener('playing', () => this.markCameraReady());
    }

    // Request permissions on load
    this.requestCameraPermissions();
  }

  getApiBaseURL() {
    const envBaseUrl =
      typeof process !== 'undefined' &&
      process.env &&
      process.env.REACT_APP_API_BASE_URL
        ? process.env.REACT_APP_API_BASE_URL
        : null;
    return envBaseUrl || window.DeepFaceAPI?.getBaseURL?.() || 'http://localhost:18000';
  }

  /**
   * Request camera permissions
   */
  async requestCameraPermissions() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      // Close the test stream
      stream.getTracks().forEach((track) => track.stop());
      this.showStatus('✓ Camera sẵn sàng', 'success');
    } catch (error) {
      this.isRunning = false;
      this.updateButtonStates();
      this.showStatus('❌ Không thể truy cập camera. Vui lòng cho phép quyền truy cập.', 'error');
      console.error('Camera permission error:', error);
    }
  }

  /**
   * Start webcam stream
   */
  async startWebcam() {
    try {
      if (this.mediaStream) {
        this.markCameraReady();
        return; // Already running
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });

      this.mediaStream = stream;
      if (this.videoElement) {
        this.videoElement.srcObject = stream;
        await this.videoElement.play();
      }

      this.markCameraReady();
      this.updateButtonStates();
      this.showStatus('✓ Camera đang chạy', 'info');

      // Start continuous frame capture for real-time detection (optional)
      this.continuousCapture();
    } catch (error) {
      this.isRunning = false;
      this.updateButtonStates();
      this.showStatus('❌ Lỗi khởi động camera: ' + error.message, 'error');
      console.error('Webcam error:', error);
    }
  }

  /**
   * Stop webcam stream
   */
  stopWebcam() {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    if (this.videoElement) {
      this.videoElement.srcObject = null;
    }

    this.isRunning = false;
    this.isProcessing = false;
    this.updateButtonStates();
    this.showStatus('✓ Camera đã dừng', 'info');
  }

  /**
   * Capture frame and send for verification
   */
  async captureAndVerify() {
    if (!this.videoElement || !this.isRunning) {
      this.showStatus('❌ Vui lòng khởi động camera trước', 'error');
      return;
    }

    if (this.isProcessing) {
      return; // Prevent multiple requests
    }

    this.isProcessing = true;
    this.captureBtn.disabled = true;
    this.showStatus('⏳ Đang xác thực...', 'info');

    try {
      // Capture frame from video
      const frameBase64 = this.captureFrame();

      // Send to backend for verification
      const result = await this.verifyFace(frameBase64);

      // Display result
      this.displayResult(result);
    } catch (error) {
      this.showStatus('❌ Lỗi xác thực: ' + error.message, 'error');
      console.error('Verification error:', error);
    } finally {
      this.isProcessing = false;
      this.updateButtonStates();
    }
  }

  /**
   * Capture frame from video element
   */
  captureFrame() {
    if (!this.videoElement || !this.canvasElement) {
      throw new Error('Video or canvas element not found');
    }
    if (!this.videoElement.videoWidth || !this.videoElement.videoHeight) {
      throw new Error('Camera is not ready yet');
    }

    const context = this.canvasElement.getContext('2d');
    this.canvasElement.width = this.videoElement.videoWidth;
    this.canvasElement.height = this.videoElement.videoHeight;

    context.drawImage(this.videoElement, 0, 0);
    return this.canvasElement.toDataURL('image/jpeg', 0.8);
  }

  /**
   * Continuous frame capture for real-time detection (optional)
   */
  continuousCapture() {
    if (!this.isRunning) return;

    // Optional: Send frames periodically for real-time detection
    // This can be implemented based on backend capability
    setTimeout(() => this.continuousCapture(), 2000);
  }

  /**
   * Send face frame to backend for verification
   */
  async verifyFace(frameBase64) {
    try {
      const payload = {
        image: frameBase64,
      };
      return window.DeepFaceAPI
        ? await window.DeepFaceAPI.post('/api/access/verify-face', payload)
        : await this.fetchJson('/api/access/verify-face', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${this.getAuthToken()}`,
            },
            body: JSON.stringify(payload),
          });
    } catch (error) {
      throw new Error(`Face verification failed: ${error.message}`);
    }
  }

  /**
   * Display verification result
   */
  displayResult(result) {
    if (!this.resultContainer) return;

    this.resultContainer.innerHTML = '';
    const resultDiv = document.createElement('div');

    if (result.status === 'allowed') {
      resultDiv.className = 'result-card result-success';
      resultDiv.innerHTML = `
        <div class="result-icon">✓</div>
        <h2>Chào mừng!</h2>
        <p class="result-name">${window.DeepFaceAPI.escapeHTML(result.employee_name || 'Nhân viên')}</p>
        <p class="result-message">Xác thực thành công</p>
        <p class="result-confidence">Độ tin cậy: ${(result.confidence * 100).toFixed(2)}%</p>
      `;
      this.showStatus('✓ Xác thực thành công!', 'success');
    } else if (result.status === 'denied') {
      const hintTextByReason = {
        multiple_faces: 'Vui lòng chỉ để một người trước camera và thử lại.',
        no_face: 'Hãy đưa khuôn mặt vào khung hình và thử lại.',
        spoof: 'Vui lòng thử lại với khuôn mặt thật (không dùng ảnh/video).',
      };
      const hintText =
        hintTextByReason[result.reason] || 'Vui lòng liên hệ quản trị viên';
      resultDiv.className = 'result-card result-error';
      resultDiv.innerHTML = `
        <div class="result-icon">✗</div>
        <h2>Xác thực thất bại</h2>
        <p class="result-message">${window.DeepFaceAPI.escapeHTML(result.message || 'Khuôn mặt không khớp với dữ liệu trong hệ thống')}</p>
        <p class="result-hint">${window.DeepFaceAPI.escapeHTML(hintText)}</p>
      `;
      this.showStatus('❌ Xác thực thất bại!', 'error');
    } else if (result.status === 'stranger') {
      resultDiv.className = 'result-card result-warning';
      resultDiv.innerHTML = `
        <div class="result-icon">⚠️</div>
        <h2>Người lạ phát hiện</h2>
        <p class="result-message">Hệ thống đã phát hiện một khuôn mặt không xác định</p>
        <p class="result-confidence">Độ tin cậy: ${(result.confidence * 100).toFixed(2)}%</p>
        <p class="result-hint">Quản trị viên đã được thông báo</p>
      `;
      this.showStatus('⚠️ Phát hiện người lạ!', 'warning');
    }

    this.resultContainer.appendChild(resultDiv);

    // Auto-hide result after 5 seconds
    setTimeout(() => {
      resultDiv.style.opacity = '0';
      resultDiv.style.transition = 'opacity 1s ease-out';
    }, 5000);
  }

  /**
   * Update button states based on running status
   */
  updateButtonStates() {
    const cameraReady = this.isRunning && Boolean(this.mediaStream);
    if (this.startBtn) {
      this.startBtn.disabled = cameraReady || this.isProcessing;
    }
    if (this.stopBtn) {
      this.stopBtn.disabled = !cameraReady;
    }
    if (this.captureBtn) {
      this.captureBtn.disabled = !cameraReady || this.isProcessing;
    }
  }

  markCameraReady() {
    if (!this.mediaStream) return;
    this.isRunning = true;
    this.updateButtonStates();
  }

  /**
   * Show status message
   */
  showStatus(message, type) {
    if (this.statusDisplay) {
      this.statusDisplay.textContent = message;
      this.statusDisplay.className = `status-display status-${type}`;
      this.statusDisplay.style.display = 'block';
    }
  }

  async fetchJson(path, options = {}) {
    const response = await fetch(`${this.apiBaseURL}${path}`, options);
    const contentType = response.headers.get('content-type') || '';
    const payload = contentType.includes('application/json')
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const detail =
        typeof payload === 'object' ? payload.detail || payload.message : payload;
      throw new Error(detail || `HTTP ${response.status}`);
    }

    return payload;
  }

  /**
   * Get authentication token
   */
  getAuthToken() {
    return localStorage.getItem('auth_token') || '';
  }

  /**
   * Cleanup on page unload
   */
  destroy() {
    this.stopWebcam();
  }
}

// Initialize module when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.faceScanModule = new FaceScanModule();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  if (window.faceScanModule) {
    window.faceScanModule.destroy();
  }
});
