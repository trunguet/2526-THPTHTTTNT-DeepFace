/**
 * Face Scan Module
 * Manages webcam stream, face detection, identity verification, and status notifications
 */

class FaceScanModule {
  constructor() {
    this.videoElement = document.getElementById('video-stream');
    this.videoContainer = document.getElementById('video-container');
    this.canvasElement = document.getElementById('canvas-stream');
    this.captureBtn = document.getElementById('capture-btn');
    this.startBtn = document.getElementById('start-btn');
    this.stopBtn = document.getElementById('stop-btn');
    this.autoScanBtn = document.getElementById('auto-scan-btn');
    this.statusDisplay = document.getElementById('status-display');
    this.resultContainer = document.getElementById('result-container');

    this.apiBaseURL = this.getApiBaseURL();
    this.mediaStream = null;
    this.isRunning = false;
    this.isProcessing = false;
    this.isAutoScanning = false;
    this.autoScanTimeoutId = null;

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
    if (this.autoScanBtn) {
      this.autoScanBtn.addEventListener('click', () => this.toggleAutoScan());
    }
    if (this.videoElement) {
      this.videoElement.addEventListener('loadedmetadata', () => this.markCameraReady());
      this.videoElement.addEventListener('playing', () => this.markCameraReady());
    }

    // UX Improvement: Don't request permissions on load.
    // It will be requested when the user clicks "Start Camera".
    this.showStatus('ℹ️ Nhấn "Khởi Động Camera" để bắt đầu', 'info');
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
    if (this.autoScanTimeoutId) {
      clearTimeout(this.autoScanTimeoutId);
      this.autoScanTimeoutId = null;
    }
    this.isAutoScanning = false;

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
  async captureAndVerify(isAuto = false) {
    if (!this.videoElement || !this.isRunning) { // Check if camera is running
      this.showStatus('❌ Vui lòng khởi động camera trước', 'error');
      return;
    }

    if (this.isProcessing) {
      return; // Prevent multiple requests
    }

    this.isProcessing = true;
    this.updateButtonStates();
    if (!isAuto) {
      this.showStatus('⏳ Đang xác thực...', 'info');
    }

    try {
      // Capture frame from video
      const frameBase64 = this.captureFrame();

      // Send to backend for verification
      const result = await this.verifyFace(frameBase64);

      // In auto-scan mode, don't show a result if no face was found.
      if (isAuto && result.status === 'denied' && result.reason === 'no_face') {
        // Silently continue scanning without showing an error
      } else {
        this.displayResult(result);
      }

      // If verification is successful, handle it based on the scan mode.
      if (result.status === 'allowed') {
        // In auto-scan mode, we don't stop. We just show the result and continue scanning.
        if (isAuto) {
          this.showStatus(`✓ Chào mừng ${result.employee_name}!`, 'success');
        } else {
          // In manual scan mode, we stop the camera after success for a better UX.
          this.showStatus(`✓ Chào mừng ${result.employee_name}. Camera sẽ tự động dừng.`, 'success');
          setTimeout(() => this.stopWebcam(), 2000);
        }
      }
    } catch (error) {
      if (!isAuto) { // Only show errors on manual capture
        this.showStatus('❌ Lỗi xác thực: ' + error.message, 'error');
      }
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
  async continuousCapture() {
    if (this.autoScanTimeoutId) {
      clearTimeout(this.autoScanTimeoutId);
      this.autoScanTimeoutId = null;
    }

    // Stop if camera is off or auto-scan is disabled
    if (!this.isRunning || !this.isAutoScanning) {
      return;
    }

    await this.captureAndVerify(true); // Call with isAuto = true

    // If still in auto-scan mode (i.e., verification didn't stop it), schedule the next scan.
    if (this.isAutoScanning) {
      this.autoScanTimeoutId = setTimeout(() => this.continuousCapture(), 2000);
    }
  }

  /**
   * Toggle auto-scan mode
   */
  toggleAutoScan() {
    this.isAutoScanning = !this.isAutoScanning;
    this.updateButtonStates();
    this.showStatus(this.isAutoScanning ? '🔍 Đã bật quét tự động...' : '✓ Đã tắt quét tự động', 'info');
    this.continuousCapture();
  }

  /**
   * Flash video border color for visual feedback
   */
  flashVideoBorder(status) {
    if (!this.videoContainer) return;

    const className = status === 'success' ? 'scan-success' : 'scan-error';

    this.videoContainer.classList.add(className);

    setTimeout(() => {
      if (this.videoContainer) {
        this.videoContainer.classList.remove(className);
      }
    }, 1500);
  }

  /**
   * Send face frame to backend for verification
   */
  async verifyFace(frameBase64) {
    try {
      const payload = {
        image: frameBase64,
      };
      const employeeId = (localStorage.getItem('employee_id') || '').trim();
      if (employeeId) {
        payload.employee_id = employeeId;
      }
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
      this.flashVideoBorder('success');
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
      this.flashVideoBorder('error');
      const hintTextByReason = {
        multiple_faces: 'Vui lòng chỉ để một người trước camera và thử lại.',
        no_face: 'Hãy đưa khuôn mặt vào khung hình và thử lại.',
        spoof: 'Vui lòng thử lại với khuôn mặt thật (không dùng ảnh/video).',
        minifas_low_score: 'MiniFAS score thấp. Vui lòng thử lại.',
        too_dark: 'Khung hình quá tối. Vui lòng tăng ánh sáng và thử lại.',
        face_too_close: 'Khuôn mặt quá sát camera. Vui lòng lùi xa hơn và thử lại.',
        face_too_far: 'Khuôn mặt quá xa camera. Vui lòng lại gần hơn và thử lại.',
        face_bright_bg_dark: 'Mặt sáng bất thường nhưng nền tối. Vui lòng điều chỉnh ánh sáng và thử lại.',
        face_tilted: 'Khuôn mặt bị nghiêng. Vui lòng giữ thẳng mặt và thử lại.',
        too_blurry: 'Hình ảnh bị mờ/rung. Vui lòng giữ yên và thử lại.',
        face_turned: 'Khuôn mặt đang quay quá nhiều. Vui lòng nhìn thẳng camera và thử lại.',
        challenge_failed: 'Không qua challenge (chớp mắt/quay đầu). Vui lòng thử lại.',
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
      this.flashVideoBorder('error');
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
      this.captureBtn.disabled = !cameraReady || this.isProcessing || this.isAutoScanning;
    }
    if (this.autoScanBtn) {
      this.autoScanBtn.disabled = !cameraReady || this.isProcessing;
      if (this.isAutoScanning) {
        this.autoScanBtn.innerHTML = '<span>⏳</span> <span>Dừng Quét</span>';
        this.autoScanBtn.classList.add('active');
      } else {
        this.autoScanBtn.innerHTML = '<span>🔄</span> <span>Tự Động Quét</span>';
        this.autoScanBtn.classList.remove('active');
      }
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
