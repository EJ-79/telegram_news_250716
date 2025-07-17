import os

# 텔레그램 설정 (공통)
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 뉴스봇 설정
NEWS_RSS_FEEDS = {
    # 일반 기술 뉴스
    'TechCrunch': 'https://techcrunch.com/feed/',
    'Yahoo Finance': 'https://finance.yahoo.com/rss/',
    'Ars Technica': 'https://feeds.arstechnica.com/arstechnica/index',
    
    # 학술/연구 뉴스
    'IEEE Spectrum': 'https://spectrum.ieee.org/rss/fulltext',
    'MIT Technology Review': 'https://www.technologyreview.com/feed/',
    
    # 양자 전문 사이트들
    'Physics World': 'https://physicsworld.com/c/quantum-physics/feed/',
    'Science Daily Quantum': 'https://www.sciencedaily.com/rss/computers_math/quantum_physics.xml',
    'Quantum Computing Report': 'https://quantumcomputingreport.com/feed/',
    
    # 과학 전문 사이트들  
    'Nature News': 'https://www.nature.com/nature.rss',
    'Phys.org Quantum': 'https://phys.org/rss-feed/technology-news/quantum-physics/'
}

NEWS_AI_KEYWORDS = [
    'artificial intelligence', 'AI', 'machine learning', 'deep learning', 
    'neural network', 'LLM', 'ChatGPT', 'OpenAI', 'anthropic', 'claude',
    'generative AI', 'transformer', 'GPT', 'large language model',
    'computer vision', 'natural language processing', 'NLP', 'robotics',
    'autonomous', 'self-driving', 'AI chip', 'nvidia AI', 'google AI',
    'microsoft AI', 'AI startup', 'AI funding', 'AI breakthrough',
    'foundation model', 'multimodal AI', 'AI safety', 'AGI'
]

NEWS_QUANTUM_KEYWORDS = [
    'quantum', 'qubit', 'quantum computing', 'quantum communication', 
    'quantum sensing', 'quantum internet', 'quantum supremacy', 
    'quantum encryption', 'IBM quantum', 'Google quantum', 'quantum algorithm',
    'quantum processor', 'quantum chip', 'quantum network', 'quantum cryptography',
    'quantum advantage', 'quantum error correction', 'quantum entanglement',
    'quantum teleportation', 'quantum simulation', 'quantum startup',
    'quantum breakthrough', 'superconducting qubit', 'trapped ion',
    'photonic quantum', 'quantum annealing', 'D-Wave', 'IonQ', 'Rigetti'
]

# 실적봇 API 설정
FMP_API_KEY = os.getenv('FMP_API_KEY', 'demo')  # Financial Modeling Prep API 키
EARNINGS_COMPANIES = [
    # 관심 있는 기업 티커 심볼들
    'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA',
    'ORCL', 'CRM', 'ADBE', 'INTC', 'AMD', 'QCOM', 'CSCO',
    'IBM', 'NFLX', 'PYPL', 'UBER', 'LYFT', 'ZOOM', 'SNOW'
]

EARNINGS_RSS_FEEDS = {
    'Yahoo Finance Earnings': 'https://finance.yahoo.com/news/rssindex',
    'MarketWatch Earnings': 'https://feeds.marketwatch.com/marketwatch/marketpulse/',
    'Seeking Alpha Earnings': 'https://seekingalpha.com/market_currents.xml',
}

EARNINGS_KEYWORDS = [
    'earnings', 'quarterly results', 'financial results', 'revenue',
    'profit', 'loss', 'EPS', 'earnings per share', 'guidance',
    'outlook', 'beat estimates', 'miss estimates', 'quarterly report',
    'annual report', '10-K', '10-Q', 'SEC filing', 'conference call'
]

# 공통 함수들
def send_telegram_message(message):
    """텔레그램 메시지 전송 (공통 함수)"""
    import requests
    
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ 텔레그램 설정이 없습니다.")
        return False
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, data=data, timeout=30)
        if response.status_code == 200:
            print("✅ 텔레그램 메시지 전송 성공!")
            return True
        else:
            print(f"❌ 텔레그램 전송 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 텔레그램 전송 오류: {e}")
        return False
