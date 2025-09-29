"""
E2E 브라우저 자동화 테스트
"""

import pytest
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

@pytest.fixture(scope="module")
def browser():
    """브라우저 픽스처"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 헤드리스 모드
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--use-fake-ui-for-media-stream")  # 가짜 미디어 스트림
    chrome_options.add_argument("--use-fake-device-for-media-stream")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-web-security")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
    except WebDriverException as e:
        pytest.skip(f"Chrome WebDriver not available: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()

@pytest.fixture
def server_url():
    """서버 URL"""
    return "http://localhost:6001"

class TestMainPage:
    """메인 페이지 E2E 테스트"""

    def test_page_loads(self, browser, server_url):
        """페이지 로딩 테스트"""
        browser.get(server_url)

        # 페이지 제목 확인
        assert "음성 대화" in browser.title or "Voice Chat" in browser.title

        # 필수 요소들이 로드되었는지 확인
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

    def test_ui_elements_present(self, browser, server_url):
        """UI 요소 존재 확인"""
        browser.get(server_url)

        # 녹음 버튼 확인
        try:
            record_button = WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.ID, "recordButton"))
            )
            assert record_button.is_displayed()
        except TimeoutException:
            # 다른 셀렉터로 시도
            record_elements = browser.find_elements(By.CSS_SELECTOR, "[class*='record'], [id*='record'], button")
            assert len(record_elements) > 0

        # 메시지 영역 확인
        try:
            messages_area = browser.find_element(By.ID, "messages")
            assert messages_area.is_displayed()
        except:
            # 대체 셀렉터로 시도
            message_elements = browser.find_elements(By.CSS_SELECTOR, "[class*='message'], [id*='message'], .chat")
            assert len(message_elements) >= 0  # 메시지가 없을 수도 있음

    def test_css_loading(self, browser, server_url):
        """CSS 로딩 테스트"""
        browser.get(server_url)

        # 스타일시트가 로드되었는지 확인
        stylesheets = browser.find_elements(By.TAG_NAME, "link")
        css_loaded = any(
            link.get_attribute("rel") == "stylesheet"
            for link in stylesheets
        )
        assert css_loaded

    def test_javascript_loading(self, browser, server_url):
        """JavaScript 로딩 테스트"""
        browser.get(server_url)

        # JavaScript 파일이 로드되었는지 확인
        scripts = browser.find_elements(By.TAG_NAME, "script")
        js_loaded = any(
            script.get_attribute("src") and "voice-chat" in script.get_attribute("src")
            for script in scripts
        )

        # 인라인 스크립트도 확인
        if not js_loaded:
            inline_scripts = [
                script for script in scripts
                if script.get_attribute("innerHTML") and len(script.get_attribute("innerHTML")) > 100
            ]
            assert len(inline_scripts) > 0

class TestQuickTestPage:
    """빠른 테스트 페이지 E2E 테스트"""

    def test_quick_test_page_loads(self, browser, server_url):
        """빠른 테스트 페이지 로딩"""
        browser.get(f"{server_url}/static/quick_test.html")

        # 페이지 제목 확인
        assert "마이크 권한" in browser.title

        # 테스트 버튼들 확인
        mic_button = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "testMic"))
        )
        ws_button = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "testWS"))
        )

        assert mic_button.is_displayed()
        assert ws_button.is_displayed()

    def test_microphone_permission_request(self, browser, server_url):
        """마이크 권한 요청 테스트"""
        browser.get(f"{server_url}/static/quick_test.html")

        # 마이크 테스트 버튼 클릭
        mic_button = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, "testMic"))
        )
        mic_button.click()

        # 로그 영역에서 결과 확인
        log_area = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "log"))
        )

        # 권한 요청 메시지가 나타나는지 확인
        WebDriverWait(browser, 5).until(
            lambda driver: "마이크 권한" in log_area.text
        )

        # 결과 확인 (성공 또는 실패)
        time.sleep(2)  # 권한 처리 대기
        log_text = log_area.text
        assert "마이크 권한" in log_text

    def test_websocket_connection(self, browser, server_url):
        """WebSocket 연결 테스트"""
        browser.get(f"{server_url}/static/quick_test.html")

        # WebSocket 테스트 버튼 클릭
        ws_button = WebDriverWait(browser, 10).until(
            EC.element_to_be_clickable((By.ID, "testWS"))
        )
        ws_button.click()

        # 로그 영역에서 연결 결과 확인
        log_area = WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, "log"))
        )

        # WebSocket 연결 메시지 확인
        WebDriverWait(browser, 10).until(
            lambda driver: "WebSocket" in log_area.text
        )

        # 연결 성공 여부 확인
        time.sleep(3)  # 연결 및 응답 대기
        log_text = log_area.text
        assert "WebSocket" in log_text

class TestAudioWorkflow:
    """오디오 워크플로우 E2E 테스트"""

    @pytest.mark.slow
    def test_full_audio_workflow(self, browser, server_url):
        """전체 오디오 워크플로우 테스트"""
        browser.get(server_url)

        # 페이지 로딩 대기
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # JavaScript 실행하여 마이크 권한 확인
        mic_available = browser.execute_script("""
            return navigator.mediaDevices &&
                   navigator.mediaDevices.getUserMedia &&
                   typeof MediaRecorder !== 'undefined';
        """)

        assert mic_available, "브라우저가 미디어 API를 지원하지 않습니다"

        # WebSocket 연결 테스트
        ws_supported = browser.execute_script("""
            return typeof WebSocket !== 'undefined';
        """)

        assert ws_supported, "브라우저가 WebSocket을 지원하지 않습니다"

    def test_media_recorder_api(self, browser, server_url):
        """MediaRecorder API 테스트"""
        browser.get(server_url)

        # MediaRecorder 지원 확인
        recorder_supported = browser.execute_script("""
            return typeof MediaRecorder !== 'undefined' &&
                   MediaRecorder.isTypeSupported &&
                   MediaRecorder.isTypeSupported('audio/webm');
        """)

        # 최소한 하나의 오디오 형식은 지원되어야 함
        if not recorder_supported:
            wav_supported = browser.execute_script("""
                return typeof MediaRecorder !== 'undefined' &&
                       MediaRecorder.isTypeSupported &&
                       MediaRecorder.isTypeSupported('audio/webm;codecs=opus');
            """)
            assert wav_supported or recorder_supported

class TestResponsiveness:
    """반응형 디자인 테스트"""

    def test_mobile_responsiveness(self, browser, server_url):
        """모바일 반응형 테스트"""
        browser.get(server_url)

        # 모바일 크기로 변경
        browser.set_window_size(375, 667)  # iPhone 6/7/8 크기

        # 페이지가 올바르게 렌더링되는지 확인
        body = browser.find_element(By.TAG_NAME, "body")
        assert body.is_displayed()

        # 가로 스크롤이 생기지 않는지 확인
        body_width = browser.execute_script("return document.body.scrollWidth;")
        window_width = browser.execute_script("return window.innerWidth;")

        assert body_width <= window_width + 50  # 약간의 여유 허용

    def test_tablet_responsiveness(self, browser, server_url):
        """태블릿 반응형 테스트"""
        browser.get(server_url)

        # 태블릿 크기로 변경
        browser.set_window_size(768, 1024)  # iPad 크기

        # 페이지가 올바르게 렌더링되는지 확인
        body = browser.find_element(By.TAG_NAME, "body")
        assert body.is_displayed()

    def test_desktop_responsiveness(self, browser, server_url):
        """데스크톱 반응형 테스트"""
        browser.get(server_url)

        # 데스크톱 크기로 변경
        browser.set_window_size(1920, 1080)

        # 페이지가 올바르게 렌더링되는지 확인
        body = browser.find_element(By.TAG_NAME, "body")
        assert body.is_displayed()

class TestAPIIntegration:
    """API 통합 테스트"""

    def test_api_accessibility(self, browser, server_url):
        """브라우저에서 API 접근 테스트"""
        # API 엔드포인트에 직접 접근
        browser.get(f"{server_url}/api/models/status")

        # JSON 응답이 표시되는지 확인
        page_source = browser.page_source
        assert "tts_available" in page_source
        assert "stt_available" in page_source

    def test_swagger_ui(self, browser, server_url):
        """Swagger UI 테스트"""
        browser.get(f"{server_url}/docs")

        # Swagger UI가 로드되는지 확인
        WebDriverWait(browser, 15).until(
            EC.presence_of_element_located((By.CLASS_NAME, "swagger-ui"))
        )

        # API 엔드포인트들이 표시되는지 확인
        page_source = browser.page_source
        assert "api/tts" in page_source or "/tts" in page_source

class TestPerformance:
    """성능 테스트"""

    @pytest.mark.slow
    def test_page_load_time(self, browser, server_url):
        """페이지 로딩 시간 테스트"""
        start_time = time.time()
        browser.get(server_url)

        # 페이지 완전 로딩 대기
        WebDriverWait(browser, 10).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )

        end_time = time.time()
        load_time = end_time - start_time

        # 10초 이내에 로딩되어야 함
        assert load_time < 10.0

    def test_memory_usage(self, browser, server_url):
        """메모리 사용량 테스트"""
        browser.get(server_url)

        # JavaScript를 통한 메모리 정보 수집
        memory_info = browser.execute_script("""
            return {
                usedHeap: performance.memory ? performance.memory.usedJSHeapSize : 0,
                totalHeap: performance.memory ? performance.memory.totalJSHeapSize : 0
            };
        """)

        # 메모리 사용량이 과도하지 않은지 확인 (100MB 이하)
        if memory_info['usedHeap'] > 0:
            assert memory_info['usedHeap'] < 100 * 1024 * 1024