/**
 * 음성 대화 시스템 JavaScript
 * WebSocket + Web Audio API 기반 실시간 음성 대화
 */

class VoiceChatApp {
    constructor() {
        this.websocket = null;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.isConnected = false;

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

        // WebSocket 연결
        this.connectWebSocket();

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
                this.elements.connectionStatus.textContent = '연결됨';
                this.elements.connectionStatus.className = 'status online';
            };

            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };

            this.websocket.onclose = () => {
                console.log('❌ WebSocket 연결 끊김');
                this.isConnected = false;
                this.elements.connectionStatus.textContent = '연결 끊김';
                this.elements.connectionStatus.className = 'status offline';

                // 재연결 시도
                setTimeout(() => this.connectWebSocket(), 3000);
            };

            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket 오류:', error);
                this.elements.connectionStatus.textContent = '오류';
                this.elements.connectionStatus.className = 'status offline';
            };

        } catch (error) {
            console.error('❌ WebSocket 연결 실패:', error);
            this.elements.connectionStatus.textContent = '연결 실패';
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
        if (this.isRecording || !this.isConnected) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            this.audioChunks = [];

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                this.processRecording();
                stream.getTracks().forEach(track => track.stop());
            };

            this.mediaRecorder.start();
            this.isRecording = true;

            // UI 업데이트
            this.elements.startRecord.disabled = true;
            this.elements.stopRecord.disabled = false;
            this.elements.recordingIndicator.classList.add('active');

            console.log('🎤 녹음 시작');

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
            // 오디오 블롭 생성
            const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });

            // WAV로 변환 (필요시)
            const arrayBuffer = await audioBlob.arrayBuffer();
            const base64Audio = this.arrayBufferToBase64(arrayBuffer);

            // WebSocket으로 전송
            if (this.websocket && this.isConnected) {
                const message = {
                    type: 'audio',
                    data: base64Audio,
                    timestamp: new Date().toISOString()
                };

                this.websocket.send(JSON.stringify(message));
                console.log('📤 오디오 데이터 전송');
            }

        } catch (error) {
            console.error('❌ 녹음 처리 실패:', error);
            this.addMessage('system', '음성 처리 중 오류가 발생했습니다.', new Date().toISOString());
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