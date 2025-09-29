/**
 * 음성 대화 시스템 JavaScript
 * WebSocket + Web Audio API 기반 실시간 음성 대화
 */

class VoiceChatApp {
    constructor() {
        this.websocket = null;
        this.streamingWebsocket = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.isConnected = false;
        this.isStreamingMode = true; // 기본적으로 스트리밍 모드 사용

        // DOM 요소들
        this.elements = {
            startRecord: document.getElementById('start-record'),
            stopRecord: document.getElementById('stop-record'),
            recordingIndicator: document.getElementById('recording-indicator'),
            chatMessages: document.getElementById('chat-messages'),
            ttsStatus: document.getElementById('tts-status'),
            sttStatus: document.getElementById('stt-status'),
            connectionStatus: document.getElementById('connection-status'),
            languageSelect: document.getElementById('language-select'),
            speedInput: document.getElementById('speed-input'),
            speedValue: document.getElementById('speed-value'),
            clearChat: document.getElementById('clear-chat'),
            testText: document.getElementById('test-text'),
            testTts: document.getElementById('test-tts'),
            // 자동 대화 관련 요소들
            autoChatStatus: document.getElementById('auto-chat-status'),
            autoChatTheme: document.getElementById('auto-chat-theme'),
            autoChatInterval: document.getElementById('auto-chat-interval'),
            autoIntervalValue: document.getElementById('auto-interval-value'),
            startAutoChat: document.getElementById('start-auto-chat'),
            stopAutoChat: document.getElementById('stop-auto-chat')
        };

        // 자동 대화 상태 관리
        this.autoChatState = {
            isActive: false,
            sessionId: null,
            theme: 'casual',
            interval: 30
        };

        this.init();
    }

    async init() {
        console.log('🚀 음성 대화 시스템 초기화...');

        // 이벤트 리스너 등록
        this.setupEventListeners();

        // 모델 상태 확인
        await this.checkModelsStatus();

        // WebSocket 연결 (기존 채팅용)
        this.connectWebSocket();

        // 스트리밍 STT WebSocket 연결
        this.connectStreamingWebSocket();

        // 마이크 권한 요청
        await this.requestMicrophoneAccess();
    }

    setupEventListeners() {
        // 녹음 버튼
        this.elements.startRecord.addEventListener('click', () => this.startRecording());
        this.elements.stopRecord.addEventListener('click', () => this.stopRecording());

        // 속도 슬라이더
        this.elements.speedInput.addEventListener('input', (e) => {
            this.elements.speedValue.textContent = e.target.value;
        });

        // 채팅 지우기
        this.elements.clearChat.addEventListener('click', () => this.clearChat());

        // TTS 테스트
        this.elements.testTts.addEventListener('click', () => this.testTTS());

        // 자동 대화 이벤트 리스너들
        this.elements.startAutoChat.addEventListener('click', () => this.startAutoChat());
        this.elements.stopAutoChat.addEventListener('click', () => this.stopAutoChat());

        // 자동 대화 간격 슬라이더
        this.elements.autoChatInterval.addEventListener('input', (e) => {
            this.elements.autoIntervalValue.textContent = e.target.value;
            this.autoChatState.interval = parseInt(e.target.value);
        });

        // 자동 대화 주제 변경
        this.elements.autoChatTheme.addEventListener('change', (e) => {
            this.autoChatState.theme = e.target.value;
        });

        // 키보드 단축키 (스페이스바로 녹음)
        document.addEventListener('keydown', (e) => {
            if (e.code === 'Space' && !e.repeat && e.target.tagName !== 'TEXTAREA') {
                e.preventDefault();
                if (!this.isRecording) {
                    this.startRecording();
                }
            }
        });

        document.addEventListener('keyup', (e) => {
            if (e.code === 'Space' && this.isRecording) {
                e.preventDefault();
                this.stopRecording();
            }
        });
    }

    async checkModelsStatus() {
        try {
            const response = await fetch('/api/models/status');
            const status = await response.json();

            // TTS 상태 업데이트
            this.updateStatus(this.elements.ttsStatus, status.tts_available, 'TTS');

            // STT 상태 업데이트
            this.updateStatus(this.elements.sttStatus, status.stt_available, 'STT');

            console.log('📊 모델 상태:', status);
        } catch (error) {
            console.error('❌ 모델 상태 확인 실패:', error);
            this.updateStatus(this.elements.ttsStatus, false, 'TTS');
            this.updateStatus(this.elements.sttStatus, false, 'STT');
        }
    }

    updateStatus(element, isAvailable, label) {
        element.textContent = isAvailable ? '온라인' : '오프라인';
        element.className = `status ${isAvailable ? 'online' : 'offline'}`;
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

        console.log('🔌 WebSocket 연결 시도:', wsUrl);

        try {
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log('✅ WebSocket 연결됨');
                this.isConnected = true;
                this.updateConnectionStatus();
            };

            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };

            this.websocket.onclose = () => {
                console.log('❌ WebSocket 연결 끊김');
                this.isConnected = false;
                this.updateConnectionStatus();

                // 재연결 시도
                setTimeout(() => this.connectWebSocket(), 3000);
            };

            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket 오류:', error);
                this.updateConnectionStatus();
            };

        } catch (error) {
            console.error('❌ WebSocket 연결 실패:', error);
            this.updateConnectionStatus();
        }
    }

    connectStreamingWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/streaming-stt`;

        console.log('🎤 스트리밍 STT WebSocket 연결 시도:', wsUrl);

        try {
            this.streamingWebsocket = new WebSocket(wsUrl);

            this.streamingWebsocket.onopen = () => {
                console.log('✅ 스트리밍 STT WebSocket 연결됨');
                this.isStreamingConnected = true;
                this.updateConnectionStatus();

                // 스트림 시작 신호 전송
                this.streamingWebsocket.send(JSON.stringify({
                    type: 'start_stream',
                    timestamp: new Date().toISOString()
                }));
            };

            this.streamingWebsocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleStreamingSTTMessage(data);
            };

            this.streamingWebsocket.onclose = () => {
                console.log('❌ 스트리밍 STT WebSocket 연결 끊김');
                this.isStreamingConnected = false;
                this.updateConnectionStatus();

                // 재연결 시도
                setTimeout(() => this.connectStreamingWebSocket(), 3000);
            };

            this.streamingWebsocket.onerror = (error) => {
                console.error('❌ 스트리밍 STT WebSocket 오류:', error);
                this.updateConnectionStatus();
            };

        } catch (error) {
            console.error('❌ 스트리밍 STT WebSocket 연결 실패:', error);
            this.updateConnectionStatus();
        }
    }

    updateConnectionStatus() {
        const isConnected = this.isConnected && (this.isStreamingConnected || !this.isStreamingMode);

        if (isConnected) {
            this.elements.connectionStatus.textContent = '연결됨';
            this.elements.connectionStatus.className = 'status online';
        } else {
            this.elements.connectionStatus.textContent = '연결 끊김';
            this.elements.connectionStatus.className = 'status offline';
        }
    }

    handleWebSocketMessage(data) {
        console.log('📨 메시지 수신:', data);

        switch (data.type) {
            case 'user_message':
                this.addMessage('user', data.text, data.timestamp);
                break;
            case 'system_response':
                this.addMessage('system', data.text, data.timestamp, data.audio_url);
                break;
            case 'auto_chat_message':
                // 자동 대화 메시지를 TTS 처리 요청
                this.handleAutoMessage(data);
                break;
            case 'auto_message_response':
                // TTS 처리된 자동 대화 메시지 표시
                this.addMessage('auto', data.text, data.timestamp, data.audio_url);
                break;
            case 'auto_chat_started':
                this.handleAutoChatStarted(data);
                break;
            case 'auto_chat_stopped':
                this.handleAutoChatStopped(data);
                break;
            case 'auto_chat_settings_updated':
                this.handleAutoChatSettingsUpdated(data);
                break;
            case 'error':
                this.addMessage('system', `오류: ${data.message}`, new Date().toISOString());
                break;
        }
    }

    handleStreamingSTTMessage(data) {
        console.log('🎤 스트리밍 STT 수신:', data);

        switch (data.type) {
            case 'partial_result':
                // 부분 결과 표시 (실시간으로 업데이트)
                this.updatePartialTranscription(data.text, data.confidence);
                break;
            case 'final_result':
                // 최종 결과 표시
                this.finalizeTranscription(data.text, data.confidence, data.timestamp);
                break;
            case 'stream_started':
                console.log('✅ 스트리밍 STT 시작됨');
                break;
            case 'stream_stopped':
                console.log('🛑 스트리밍 STT 중지됨');
                break;
            case 'error':
                console.error('❌ 스트리밍 STT 오류:', data.error);
                this.addMessage('system', `STT 오류: ${data.error}`, new Date().toISOString());
                break;
        }
    }

    async requestMicrophoneAccess() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            console.log('🎤 마이크 접근 권한 획득');
            stream.getTracks().forEach(track => track.stop()); // 스트림 정리
            return true;
        } catch (error) {
            console.error('❌ 마이크 접근 실패:', error);
            this.addMessage('system', '마이크 접근 권한이 필요합니다. 브라우저 설정에서 마이크를 허용해주세요.', new Date().toISOString());
            return false;
        }
    }

    async startRecording() {
        const isConnected = this.isStreamingMode ? this.isStreamingConnected : this.isConnected;
        if (this.isRecording || !isConnected) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            // 스트리밍 모드에서는 실시간 청크 전송
            if (this.isStreamingMode && this.isStreamingConnected) {
                this.mediaRecorder = new MediaRecorder(stream, {
                    mimeType: 'audio/webm;codecs=opus',
                    audioBitsPerSecond: 64000  // 압축을 위한 비트레이트 설정
                });

                this.mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        // 실시간으로 WebM 청크 전송
                        this.sendAudioChunk(event.data);
                    }
                };

                // 2초마다 WebM 청크 생성 (더 완전한 청크를 위해)
                this.mediaRecorder.start(2000);

                // 부분 전사 결과 표시 준비
                this.preparePartialTranscription();

            } else {
                // 기존 방식 (배치 처리) - WebM 전용
                this.mediaRecorder = new MediaRecorder(stream, {
                    mimeType: 'audio/webm;codecs=opus'
                });

                this.audioChunks = [];

                this.mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        this.audioChunks.push(event.data);
                    }
                };

                this.mediaRecorder.start();
            }

            this.mediaRecorder.onstop = () => {
                if (!this.isStreamingMode) {
                    this.processRecording();
                }
                stream.getTracks().forEach(track => track.stop());
            };

            this.isRecording = true;

            // UI 업데이트
            this.elements.startRecord.disabled = true;
            this.elements.stopRecord.disabled = false;
            this.elements.recordingIndicator.classList.add('active');

            console.log(`🎤 녹음 시작 (${this.isStreamingMode ? '스트리밍' : '배치'} 모드)`);

        } catch (error) {
            console.error('❌ 녹음 시작 실패:', error);
            this.addMessage('system', '녹음을 시작할 수 없습니다. 마이크 권한을 확인해주세요.', new Date().toISOString());
        }
    }

    stopRecording() {
        if (!this.isRecording || !this.mediaRecorder) return;

        this.mediaRecorder.stop();
        this.isRecording = false;

        // UI 업데이트
        this.elements.startRecord.disabled = false;
        this.elements.stopRecord.disabled = true;
        this.elements.recordingIndicator.classList.remove('active');

        console.log('⏹️ 녹음 중지');
    }

    async processRecording() {
        if (this.audioChunks.length === 0) return;

        try {
            // WebM 오디오 블롭 생성
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm;codecs=opus' });

            // WebM 데이터를 Base64로 인코딩
            const arrayBuffer = await audioBlob.arrayBuffer();
            const base64Audio = this.arrayBufferToBase64(arrayBuffer);

            // WebSocket으로 WebM 데이터 전송
            if (this.websocket && this.isConnected) {
                const message = {
                    type: 'audio',
                    data: base64Audio,
                    timestamp: new Date().toISOString()
                };

                this.websocket.send(JSON.stringify(message));
                console.log('📤 WebM 오디오 데이터 전송:', audioBlob.size, 'bytes');
            }

        } catch (error) {
            console.error('❌ WebM 녹음 처리 실패:', error);
            this.addMessage('system', 'WebM 음성 처리 중 오류가 발생했습니다.', new Date().toISOString());
        }
    }

    arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) {
            binary += String.fromCharCode(bytes[i]);
        }
        return btoa(binary);
    }

    addMessage(type, text, timestamp, audioUrl = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}-message`;

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';

        const textSpan = document.createElement('span');
        textSpan.className = 'message-text';
        textSpan.textContent = text;

        const timeSpan = document.createElement('span');
        timeSpan.className = 'message-time';
        timeSpan.textContent = this.formatTime(timestamp);

        contentDiv.appendChild(textSpan);
        contentDiv.appendChild(timeSpan);

        // 오디오 플레이어 추가
        if (audioUrl) {
            const audioDiv = document.createElement('div');
            audioDiv.className = 'audio-player';

            const audio = document.createElement('audio');
            audio.controls = true;
            audio.src = audioUrl;
            audio.autoplay = true; // 자동 재생

            audioDiv.appendChild(audio);
            contentDiv.appendChild(audioDiv);
        }

        messageDiv.appendChild(contentDiv);
        this.elements.chatMessages.appendChild(messageDiv);

        // 스크롤을 맨 아래로
        this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
    }

    formatTime(timestamp) {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('ko-KR', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    clearChat() {
        this.elements.chatMessages.innerHTML = `
            <div class="message system-message">
                <div class="message-content">
                    <span class="message-text">채팅 기록이 지워졌습니다.</span>
                    <span class="message-time">시스템</span>
                </div>
            </div>
        `;
    }

    async testTTS() {
        const text = this.elements.testText.value.trim();
        if (!text) {
            alert('테스트할 텍스트를 입력해주세요.');
            return;
        }

        try {
            this.elements.testTts.disabled = true;
            this.elements.testTts.textContent = '변환 중...';

            const response = await fetch('/api/tts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    language: this.elements.languageSelect.value,
                    speed: parseFloat(this.elements.speedInput.value),
                    device: 'auto'
                })
            });

            const result = await response.json();

            if (result.success) {
                this.addMessage('system', text, new Date().toISOString(), result.audio_url);
            } else {
                this.addMessage('system', `TTS 오류: ${result.error}`, new Date().toISOString());
            }

        } catch (error) {
            console.error('❌ TTS 테스트 실패:', error);
            this.addMessage('system', `TTS 테스트 실패: ${error.message}`, new Date().toISOString());
        } finally {
            this.elements.testTts.disabled = false;
            this.elements.testTts.textContent = '음성 변환';
        }
    }

    // 자동 대화 관련 함수들
    async startAutoChat() {
        if (!this.isConnected) {
            alert('WebSocket이 연결되지 않았습니다.');
            return;
        }

        try {
            const message = {
                type: 'auto_chat_start',
                theme: this.autoChatState.theme,
                interval: this.autoChatState.interval
            };

            this.websocket.send(JSON.stringify(message));
            console.log('🤖 자동 대화 시작 요청 전송:', message);

        } catch (error) {
            console.error('❌ 자동 대화 시작 실패:', error);
            alert('자동 대화 시작에 실패했습니다.');
        }
    }

    async stopAutoChat() {
        if (!this.isConnected) {
            return;
        }

        try {
            const message = {
                type: 'auto_chat_stop'
            };

            this.websocket.send(JSON.stringify(message));
            console.log('🛑 자동 대화 중지 요청 전송');

        } catch (error) {
            console.error('❌ 자동 대화 중지 실패:', error);
        }
    }

    handleAutoMessage(data) {
        // 자동 대화 메시지를 TTS 처리를 위해 다시 전송
        const message = {
            type: 'auto_chat_message',
            text: data.text,
            timestamp: data.timestamp,
            session_id: data.session_id,
            theme: data.theme
        };

        this.websocket.send(JSON.stringify(message));
    }

    handleAutoChatStarted(data) {
        console.log('✅ 자동 대화 시작됨:', data);

        this.autoChatState.isActive = true;
        this.autoChatState.sessionId = data.session_id;

        // UI 업데이트
        this.elements.autoChatStatus.textContent = '활성';
        this.elements.autoChatStatus.className = 'status online';
        this.elements.startAutoChat.disabled = true;
        this.elements.stopAutoChat.disabled = false;

        // 자동 대화 패널 스타일 변경
        const panel = document.querySelector('.auto-chat-panel');
        if (panel) {
            panel.classList.add('auto-chat-active');
        }

        this.addMessage('system', `🤖 자동 대화가 시작되었습니다. (주제: ${data.theme}, 간격: ${data.interval}초)`, new Date().toISOString());
    }

    handleAutoChatStopped(data) {
        console.log('🛑 자동 대화 중지됨:', data);

        this.autoChatState.isActive = false;
        this.autoChatState.sessionId = null;

        // UI 업데이트
        this.elements.autoChatStatus.textContent = '비활성';
        this.elements.autoChatStatus.className = 'status offline';
        this.elements.startAutoChat.disabled = false;
        this.elements.stopAutoChat.disabled = true;

        // 자동 대화 패널 스타일 변경
        const panel = document.querySelector('.auto-chat-panel');
        if (panel) {
            panel.classList.remove('auto-chat-active');
        }

        this.addMessage('system', '🛑 자동 대화가 중지되었습니다.', new Date().toISOString());
    }

    handleAutoChatSettingsUpdated(data) {
        console.log('⚙️ 자동 대화 설정 업데이트:', data);

        this.autoChatState.theme = data.theme;
        this.autoChatState.interval = data.interval;

        // UI 반영
        this.elements.autoChatTheme.value = data.theme;
        this.elements.autoChatInterval.value = data.interval;
        this.elements.autoIntervalValue.textContent = data.interval;

        this.addMessage('system', `⚙️ 자동 대화 설정이 변경되었습니다. (주제: ${data.theme}, 간격: ${data.interval}초)`, new Date().toISOString());
    }

    // 새로운 스트리밍 STT 관련 메소드들
    async sendAudioChunk(audioBlob) {
        if (!this.streamingWebsocket || this.streamingWebsocket.readyState !== WebSocket.OPEN) {
            return;
        }

        // 청크 크기 검증
        if (audioBlob.size < 1000) {  // 1KB 미만은 무시
            console.log('⚠️ 너무 작은 오디오 청크 무시:', audioBlob.size, 'bytes');
            return;
        }

        try {
            // WebM 오디오 블롭을 ArrayBuffer로 변환
            const arrayBuffer = await audioBlob.arrayBuffer();

            // WebM 헤더 간단 확인
            const uint8Array = new Uint8Array(arrayBuffer);
            if (uint8Array.length < 32) {
                console.log('⚠️ WebM 헤더가 너무 짧음 - 청크 무시');
                return;
            }

            const base64Audio = this.arrayBufferToBase64(arrayBuffer);

            // 스트리밍 STT WebSocket으로 WebM 청크 전송
            const message = {
                type: 'audio_chunk',
                data: base64Audio,
                timestamp: new Date().toISOString(),
                chunk_id: Date.now().toString()
            };

            this.streamingWebsocket.send(JSON.stringify(message));
            console.log('📤 WebM 오디오 청크 전송:', audioBlob.size, 'bytes');

        } catch (error) {
            console.error('❌ WebM 오디오 청크 전송 실패:', error);
        }
    }

    preparePartialTranscription() {
        // 부분 전사 결과를 표시할 메시지 영역 준비
        if (!this.partialMessageDiv) {
            this.partialMessageDiv = document.createElement('div');
            this.partialMessageDiv.className = 'message user-message partial-transcription';
            this.partialMessageDiv.innerHTML = `
                <div class="message-content">
                    <span class="message-text partial-text">🎤 음성 인식 중...</span>
                    <span class="message-time">실시간</span>
                    <div class="confidence-bar">
                        <div class="confidence-fill"></div>
                    </div>
                </div>
            `;
            this.elements.chatMessages.appendChild(this.partialMessageDiv);
            this.elements.chatMessages.scrollTop = this.elements.chatMessages.scrollHeight;
        }
    }

    updatePartialTranscription(text, confidence) {
        if (!this.partialMessageDiv) {
            this.preparePartialTranscription();
        }

        const textElement = this.partialMessageDiv.querySelector('.partial-text');
        const confidenceBar = this.partialMessageDiv.querySelector('.confidence-fill');

        if (text && text.trim()) {
            textElement.textContent = `🎤 ${text}`;
            textElement.className = 'message-text partial-text active';

            // 신뢰도 바 업데이트
            if (confidenceBar) {
                confidenceBar.style.width = `${confidence * 100}%`;
                confidenceBar.style.backgroundColor = confidence > 0.7 ? '#4CAF50' :
                                                      confidence > 0.5 ? '#FF9800' : '#f44336';
            }
        }
    }

    finalizeTranscription(text, confidence, timestamp) {
        if (this.partialMessageDiv) {
            // 부분 전사 메시지 제거
            this.partialMessageDiv.remove();
            this.partialMessageDiv = null;
        }

        if (text && text.trim()) {
            // 최종 결과를 일반 메시지로 표시
            this.addMessage('user', text, timestamp);

            // 신뢰도가 낮으면 경고 표시
            if (confidence < 0.6) {
                this.addMessage('system',
                    `⚠️ 음성 인식 신뢰도가 낮습니다 (${Math.round(confidence * 100)}%). 다시 말씀해 주세요.`,
                    new Date().toISOString()
                );
            }

            console.log(`✅ 최종 전사: "${text}" (신뢰도: ${confidence.toFixed(3)})`);
        }
    }
}

// 앱 시작
document.addEventListener('DOMContentLoaded', () => {
    console.log('🌟 음성 대화 시스템 시작');
    new VoiceChatApp();
});

// 키보드 단축키 안내
console.log(`
🎯 사용법:
- 🎤 마이크 버튼을 클릭하거나 스페이스바를 눌러 녹음
- ⏹️ 녹음 중지 버튼을 클릭하거나 스페이스바를 떼어 중지
- 🔧 설정에서 언어와 속도 조절 가능
- 📝 텍스트 입력으로도 TTS 테스트 가능
`);