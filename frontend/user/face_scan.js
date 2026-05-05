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
    return envBaseUrl || 'http://localhost:8000';
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
        return; // Already running
      }

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });

      this.mediaStream = stream;
      if (this.videoElement) {
        this.videoElement.srcObject = stream;
        this.videoElement.play();
      }

      this.isRunning = true;
      this.updateButtonStates();
      this.showStatus('✓ Camera đang chạy', 'info');

      // Start continuous frame capture for real-time detection (optional)
      this.continuousCapture();
    } catch (error) {
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
      this.captureBtn.disabled = false;
    }
  }

  /**
   * Capture frame from video element
   */
  captureFrame() {
    if (!this.videoElement || !this.canvasElement) {
      throw new Error('Video or canvas element not found');
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
      const response = await fetch(`${this.apiBaseURL}/api/access/verify-face`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${this.getAuthToken()}`,
        },
        body: JSON.stringify({
          image: frameBase64, // Base64 encoded image
        }),
      });

      if (!response.ok) {
        throw new Error('Verification request failed');
      }

      return await response.json();
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
        <p class="result-name">${result.employee_name || 'Nhân viên'}</p>
        <p class="result-message">Xác thực thành công</p>
        <p class="result-confidence">Độ tin cậy: ${(result.confidence * 100).toFixed(2)}%</p>
      `;
      this.showStatus('✓ Xác thực thành công!', 'success');
    } else if (result.status === 'denied') {
      resultDiv.className = 'result-card result-error';
      resultDiv.innerHTML = `
        <div class="result-icon">✗</div>
        <h2>Xác thực thất bại</h2>
        <p class="result-message">${result.message || 'Khuôn mặt không khớp với dữ liệu trong hệ thống'}</p>
        <p class="result-hint">Vui lòng liên hệ quản trị viên</p>
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
    if (this.startBtn) {
      this.startBtn.disabled = this.isRunning;
    }
    if (this.stopBtn) {
      this.stopBtn.disabled = !this.isRunning;
    }
    if (this.captureBtn) {
      this.captureBtn.disabled = !this.isRunning;
    }
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
