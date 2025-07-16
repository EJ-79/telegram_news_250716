import requests
import feedparser
import json
import os
from datetime import datetime

# 환경 변수에서 설정 읽기 (GitHub Secrets에서 설정할 예정)
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# RSS 피드 URL들
RSS_FEEDS = {
    'TechCrunch': 'https://techcrunch.com/feed/',
    'Yahoo Finance': 'https://finance.yahoo.com/rss/',
    'IEEE Spectrum': 'https://spectrum.ieee.org/rss/fulltext',
    'Ars Technica': 'https://feeds.arstechnica.com/arstechnica/index',
}

# 관심 키워드
AI_KEYWORDS = [
    'artificial intelligence', 'AI', 'machine learning', 'deep learning', 
    'neural network', 'LLM', 'ChatGPT', 'OpenAI', 'anthropic', 'claude',
    'generative AI', 'transformer', 'GPT', 'large language model', 'grok', 'Gemini'
]

QUANTUM_KEYWORDS = [
    'quantum', 'qubit', 'quantum computing', 'quantum communication', 
    'quantum sensing', 'quantum internet', 'quantum supremacy', 
    'quantum encryption', 'IBM quantum', 'Google quantum', 'quantum algorithm', 'Majorana', 'QKD', 'NISQ', 'FTQC'
]

def send_message_to_telegram(message):
    """텔레그램으로 메시지 전송"""
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
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ 텔레그램 전송 오류: {e}")
        return False

def check_keywords_in_text(text, keywords):
    """텍스트에 키워드가 포함되어 있는지 확인"""
    if not text:
        return False
    text_lower = text.lower()
    for keyword in keywords:
        if keyword.lower() in text_lower:
            return True
    return False

def filter_news_by_keywords(entries, keywords, category_name):
    """키워드로 뉴스 필터링"""
    filtered_news = []
    
    for entry in entries:
        title = entry.title if hasattr(entry, 'title') else ""
        summary = entry.summary if hasattr(entry, 'summary') else ""
        full_text = f"{title} {summary}"
        
        # 키워드 매칭 확인
        if check_keywords_in_text(full_text, keywords):
            matched_keywords = [kw for kw in keywords if kw.lower() in full_text.lower()]
            
            filtered_news.append({
                'title': title,
                'link': entry.link if hasattr(entry, 'link') else "",
                'published': entry.published if hasattr(entry, 'published') else 'Unknown',
                'summary': summary[:200] + "..." if len(summary) > 200 else summary,
                'matched_keywords': matched_keywords,
                'category': category_name,
                'source': ''  # 나중에 사이트명 추가
            })
    
    return filtered_news

def collect_filtered_news():
    """모든 사이트에서 뉴스 수집 및 필터링"""
    all_filtered_news = []
    
    print("🔍 뉴스 수집 시작...")
    
    for site_name, feed_url in RSS_FEEDS.items():
        print(f"📰 {site_name} 분석 중...")
        try:
            # RSS 피드 파싱
            feed = feedparser.parse(feed_url)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                print(f"   ⚠️ {site_name}: 뉴스가 없습니다.")
                continue
            
            # AI 키워드로 필터링
            ai_news = filter_news_by_keywords(feed.entries, AI_KEYWORDS, "AI")
            for news in ai_news:
                news['source'] = site_name
            
            # 양자 키워드로 필터링  
            quantum_news = filter_news_by_keywords(feed.entries, QUANTUM_KEYWORDS, "Quantum")
            for news in quantum_news:
                news['source'] = site_name
            
            print(f"   🤖 AI 관련: {len(ai_news)}개")
            print(f"   ⚛️ 양자 관련: {len(quantum_news)}개")
            
            all_filtered_news.extend(ai_news)
            all_filtered_news.extend(quantum_news)
            
        except Exception as e:
            print(f"   ❌ {site_name} 오류: {e}")
            continue
    
    return all_filtered_news

def smart_truncate(text, length):
    """스마트하게 텍스트 자르기 (단어 단위)"""
    if len(text) <= length:
        return text
    
    # 길이 내에서 마지막 공백 찾기
    truncated = text[:length]
    last_space = truncated.rfind(' ')
    
    if last_space > length * 0.8:  # 80% 이상이면 단어 단위로 자르기
        return truncated[:last_space] + "..."
    else:
        return truncated + "..."

def create_news_summary(news_list, max_news=8):
    """뉴스 요약 메시지 생성 (개선된 버전)"""
    if not news_list:
        return "📰 오늘은 AI/양자 관련 뉴스가 없습니다."
    
    # 카테고리별로 분류
    ai_news = [n for n in news_list if n['category'] == 'AI']
    quantum_news = [n for n in news_list if n['category'] == 'Quantum']
    
    # 메시지 구성
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    message = f"🤖 <b>AI & 양자 뉴스 요약</b>\n"
    message += f"📅 {current_time} (한국시간)\n\n"
    
    if ai_news:
        message += f"🤖 <b>AI 뉴스 ({len(ai_news)}개 중 {min(len(ai_news), max_news//2)}개)</b>\n\n"
        for i, news in enumerate(ai_news[:max_news//2], 1):
            # 제목을 80자로 늘리고 스마트하게 자르기
            title = smart_truncate(news['title'], 80)
            
            message += f"<b>{i}. {title}</b>\n"
            message += f"   📰 {news['source']}\n"
            
            # 요약이 있으면 첫 100자 추가
            if news.get('summary') and len(news['summary']) > 10:
                summary = smart_truncate(news['summary'], 100)
                message += f"   💭 {summary}\n"
            
            message += f"   🔗 <a href='{news['link']}'>기사 보기</a>\n\n"
    
    if quantum_news:
        message += f"⚛️ <b>양자 뉴스 ({len(quantum_news)}개 중 {min(len(quantum_news), max_news//2)}개)</b>\n\n"
        for i, news in enumerate(quantum_news[:max_news//2], 1):
            title = smart_truncate(news['title'], 80)
            
            message += f"<b>{i}. {title}</b>\n"
            message += f"   📰 {news['source']}\n"
            
            if news.get('summary') and len(news['summary']) > 10:
                summary = smart_truncate(news['summary'], 100)
                message += f"   💭 {summary}\n"
            
            message += f"   🔗 <a href='{news['link']}'>기사 보기</a>\n\n"
    
    # 텔레그램 메시지 길이 제한 (4096자)
    if len(message) > 3800:  # 여유분 확보
        message = message[:3800] + "...\n\n📱 <i>더 많은 뉴스가 있습니다!</i>"
    
    message += f"\n🔄 <i>다음 업데이트: 12시간 후</i>\n"
    message += f"🤖 <i>AI & 양자 뉴스봇 v1.0</i>"
    
    return message

def main():
    """메인 실행 함수"""
    print("🚀 뉴스봇 시작!")
    print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 뉴스 수집
        news_list = collect_filtered_news()
        print(f"📊 총 수집된 뉴스: {len(news_list)}개")
        
        # 2. 요약 생성
        summary = create_news_summary(news_list, max_news=8)
        
        # 3. 텔레그램 전송
        success = send_message_to_telegram(summary)
        
        if success:
            print("✅ 뉴스 요약 전송 완료!")
        else:
            print("❌ 전송 실패")
            
    except Exception as e:
        error_msg = f"❌ 뉴스봇 실행 오류: {e}"
        print(error_msg)
        
        # 오류 발생 시 관리자에게 알림
        if BOT_TOKEN and CHAT_ID:
            send_message_to_telegram(f"🚨 <b>뉴스봇 오류 발생</b>\n\n{error_msg}")

if __name__ == "__main__":
    main()
