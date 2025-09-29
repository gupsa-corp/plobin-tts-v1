#!/usr/bin/env python3
"""
자동 대화 패턴 데이터 모듈
다양한 주제와 시간대별 대화 내용을 관리
"""

import random
from datetime import datetime
from typing import Dict, List, Any

class ConversationPatterns:
    def __init__(self):
        self.patterns = {
            "greeting": [
                "안녕하세요! 오늘 기분이 어떠세요?",
                "좋은 하루네요! 무엇을 도와드릴까요?",
                "반갑습니다! 음성 대화를 시작해볼까요?",
                "어서오세요! 오늘도 함께 대화해요.",
                "안녕하세요! 새로운 하루가 시작됐네요.",
                "환영합니다! 무엇이든 편하게 말씀하세요."
            ],

            "casual": [
                "오늘 하루는 어떻게 보내고 계신가요?",
                "취미가 뭔지 궁금해요! 어떤 걸 좋아하시나요?",
                "좋아하는 음식이 있으신가요?",
                "최근에 재미있는 일이 있었나요?",
                "요즘 관심 있는 것이 있으신가요?",
                "어떤 음악을 즐겨 듣시나요?",
                "주말에는 뭘 하며 시간을 보내시나요?",
                "여행 가고 싶은 곳이 있으신가요?",
                "커피와 차 중에 뭘 더 좋아하시나요?",
                "책 읽기를 좋아하시나요?"
            ],

            "weather": [
                "오늘 날씨가 정말 좋네요!",
                "밖이 추운 것 같은데, 따뜻하게 입으셨나요?",
                "비가 올 것 같은 날씨네요.",
                "햇살이 참 따뜻하네요!",
                "구름이 많은 날이에요. 산책하기엔 괜찮을 것 같아요.",
                "바람이 시원하게 부는 날이네요.",
                "눈이 올 것 같은 차가운 날씨예요.",
                "맑은 하늘이 정말 예쁘네요!",
                "습한 날씨에 건강 관리 잘 하세요.",
                "오늘 같은 날씨엔 따뜻한 차 한 잔이 좋겠어요."
            ],

            "time_based": {
                "morning": [
                    "좋은 아침이에요! 잘 주무셨나요?",
                    "일찍 일어나셨네요! 활기찬 하루 되세요.",
                    "아침 식사는 드셨나요?",
                    "오늘 계획이 있으신가요?",
                    "상쾌한 아침이네요!",
                    "커피 한 잔으로 하루를 시작하시나요?"
                ],
                "afternoon": [
                    "점심시간이네요, 식사하셨나요?",
                    "오후 시간을 어떻게 보내고 계신가요?",
                    "오후에 졸리지 않으신가요?",
                    "점심 후 산책이라도 하시는 걸 어떨까요?",
                    "오후 간식 시간이네요!",
                    "바쁜 하루 중간에 잠깐 쉬어가세요."
                ],
                "evening": [
                    "하루 수고 많으셨어요!",
                    "저녁 식사 맛있게 드세요.",
                    "오늘 하루는 어떠셨나요?",
                    "편안한 저녁 시간 되세요.",
                    "가족과 함께하는 저녁 시간이군요.",
                    "오늘 하루도 고생하셨습니다."
                ],
                "night": [
                    "늦은 시간까지 수고하고 계시네요.",
                    "편안한 밤 되세요.",
                    "오늘 하루도 수고하셨어요. 푹 쉬세요.",
                    "따뜻한 차 한 잔과 함께 휴식하세요.",
                    "내일도 좋은 하루가 되길 바라요.",
                    "좋은 꿈 꾸세요!"
                ]
            },

            "educational": [
                "새로운 언어를 배우고 계신가요?",
                "오늘 새로 배운 것이 있나요?",
                "읽고 있는 책이 있으신가요?",
                "어떤 기술에 관심이 있으신가요?",
                "온라인 강의를 들어보신 적 있나요?",
                "한국어 발음 연습을 함께 해볼까요?",
                "영어 회화 연습도 도움이 될까요?",
                "새로운 취미를 배워보는 건 어떨까요?",
                "요리 레시피를 찾아보시나요?",
                "운동이나 건강 관리에 관심 있으신가요?"
            ],

            "entertainment": [
                "재미있는 농담 하나 들려드릴까요?",
                "퀴즈 문제 하나 내볼게요. 준비되셨나요?",
                "최근에 본 영화 중에 재미있는 게 있나요?",
                "좋아하는 드라마나 예능 프로그램이 있나요?",
                "게임을 즐기시나요?",
                "주말에 볼 만한 영화 추천해드릴까요?",
                "음악 듣기를 좋아하시나요? 어떤 장르를 선호하시나요?",
                "친구들과 어떤 활동을 즐기시나요?",
                "스포츠 경기 보시나요?",
                "여가 시간에 뭘 하시는 게 가장 즐거우세요?"
            ],

            "motivational": [
                "오늘도 화이팅하세요!",
                "당신은 충분히 잘하고 계세요.",
                "작은 진전도 큰 발전이에요.",
                "긍정적인 마음가짐이 중요해요.",
                "오늘 하루도 의미 있게 보내세요.",
                "새로운 도전을 두려워하지 마세요.",
                "당신의 노력이 빛을 발할 거예요.",
                "매일 조금씩 성장하고 계신 것 같아요.",
                "힘든 일이 있어도 이겨낼 수 있어요.",
                "당신만의 속도로 천천히 가도 괜찮아요."
            ],

            "questions": [
                "혹시 질문이 있으시면 언제든 말씀하세요.",
                "제가 도울 수 있는 일이 있나요?",
                "궁금한 게 있으시면 편하게 물어보세요.",
                "어떤 이야기를 나누고 싶으신가요?",
                "오늘 어떤 걸 배워보실까요?",
                "함께 대화할 주제가 있으신가요?",
                "혹시 도움이 필요한 일이 있나요?",
                "어떤 정보를 찾고 계신가요?",
                "음성 연습을 더 해보실까요?",
                "다른 언어로도 대화해볼까요?"
            ]
        }

        # 응답 패턴 (사용자 입력에 대한 반응)
        self.response_patterns = {
            "positive": [
                "정말 좋네요!",
                "훌륭하세요!",
                "멋져요!",
                "잘하셨어요!",
                "좋은 생각이네요!",
                "그렇게 생각하시는군요!",
                "정말 인상적이에요!",
                "대단하세요!"
            ],

            "neutral": [
                "그렇군요.",
                "이해했어요.",
                "알겠습니다.",
                "말씀해 주셔서 감사해요.",
                "흥미로운 이야기네요.",
                "더 자세히 듣고 싶어요.",
                "그런 경험이 있으셨군요.",
                "좋은 정보네요."
            ],

            "encouraging": [
                "힘내세요!",
                "잘 될 거예요!",
                "포기하지 마세요!",
                "당신이라면 할 수 있어요!",
                "걱정하지 마세요.",
                "시간이 해결해 줄 거예요.",
                "충분히 좋아요!",
                "완벽하지 않아도 괜찮아요."
            ]
        }

    def get_time_based_message(self) -> str:
        """현재 시간에 맞는 메시지 반환"""
        now = datetime.now()
        hour = now.hour

        if 6 <= hour < 12:
            time_period = "morning"
        elif 12 <= hour < 18:
            time_period = "afternoon"
        elif 18 <= hour < 22:
            time_period = "evening"
        else:
            time_period = "night"

        return random.choice(self.patterns["time_based"][time_period])

    def get_themed_message(self, theme: str) -> str:
        """주제별 메시지 반환"""
        if theme in self.patterns:
            return random.choice(self.patterns[theme])
        else:
            return random.choice(self.patterns["casual"])

    def get_contextual_message(self, theme: str = "casual", include_time: bool = True) -> str:
        """상황에 맞는 메시지 생성"""
        # 30% 확률로 시간 기반 메시지 포함
        if include_time and random.random() < 0.3:
            return self.get_time_based_message()
        else:
            return self.get_themed_message(theme)

    def get_response_to_input(self, user_input: str, sentiment: str = "neutral") -> str:
        """사용자 입력에 대한 적절한 응답 생성"""
        user_input_lower = user_input.lower()

        # 키워드 기반 응답
        positive_keywords = ["좋", "훌륭", "멋진", "재미있", "행복", "기쁜", "즐거운"]
        negative_keywords = ["나쁜", "슬픈", "힘든", "어려운", "피곤", "지친"]

        if any(keyword in user_input_lower for keyword in positive_keywords):
            return random.choice(self.response_patterns["positive"])
        elif any(keyword in user_input_lower for keyword in negative_keywords):
            return random.choice(self.response_patterns["encouraging"])
        else:
            return random.choice(self.response_patterns["neutral"])

    def get_all_themes(self) -> List[str]:
        """사용 가능한 모든 테마 목록 반환"""
        return [theme for theme in self.patterns.keys() if theme != "time_based"]

# 전역 인스턴스
conversation_patterns = ConversationPatterns()