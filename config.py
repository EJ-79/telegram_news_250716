import os

# 텔레그램 설정 (공통)
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# 뉴스봇 설정
NEWS_RSS_FEEDS = {
    'TechCrunch': 'https://techcrunch.com/feed/',
    'Yahoo Finance': 'https://finance.yahoo.com/rss/',
    'IEEE Spectrum': 'https://spectrum.ieee.org/rss/fulltext',
    'Ars Technica': 'https://feeds.arstechnica.com/arstechnica/index',
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

# 실적봇 설정
EARNINGS_COMPANIES = [
    # 관심 있는 기업 티커 심볼들
    'GOOGL', 'META', '9988', '9888', '00020', '035420',
    'MSFT', 'AMZN', 'ORCL', '9984', 
    'NVDA', 'AVGO', 'AMD', 'INTC', 'MU', '000660', 'SNPS', 'CDNS', 'APH', 'VRT', 'MRVL', 'CRWV', '603019', '981', '2330', '2317', '3231', '3661'
    'NFLX', 'IBM', 'IONQ'
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
