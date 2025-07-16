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

# 관심 키워드 (확장된 버전)
AI_KEYWORDS = [
    'artificial intelligence', 'AI', 'machine learning', 'deep learning', 
    'neural network', 'LLM', 'ChatGPT', 'OpenAI', 'anthropic', 'claude',
    'generative AI', 'transformer', 'GPT', 'large language model',
    'computer vision', 'natural language processing', 'NLP', 'robotics',
    'autonomous', 'self-driving', 'AI chip', 'nvidia AI', 'google AI',
    'microsoft AI', 'AI startup', 'AI funding', 'AI breakthrough',
    'foundation model', 'multimodal AI', 'AI safety', 'AGI'
]

QUANTUM_KEYWORDS = [
    'quantum', 'qubit', 'quantum computing', 'quantum communication', 
    'quantum sensing', 'quantum internet', 'quantum supremacy', 
    'quantum encryption', 'IBM quantum', 'Google quantum', 'quantum algorithm',
    'quantum processor', 'quantum chip', 'quantum network', 'quantum cryptography',
    'quantum advantage', 'quantum error correction', 'quantum entanglement',
    'quantum teleportation', 'quantum simulation', 'quantum startup',
    'quantum breakthrough', 'superconducting qubit', 'trapped ion',
    'photonic quantum', 'quantum annealing', 'D-Wave', 'IonQ', 'Rigetti'
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

def extract_key_sentences(text, keywords):
    """키워드가 포함된 문장 우선 추출"""
    if not text:
        return ""
    
    sentences = text.replace('!', '.').replace('?', '.').split('.')
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    # 키워드가 포함된 문장 찾기
    keyword_sentences = []
    for sentence in sentences:
        for keyword in keywords:
            if keyword.lower() in sentence.lower():
                keyword_sentences.append(sentence)
                break
    
    # 키워드 문장이 있으면 우선, 없으면 첫 문장
    if keyword_sentences:
        return keyword_sentences[0] + "."
    elif sentences:
        return sentences[0] + "."
    
    return text[:100] + "..." if len(text) > 100 else text

def clean_and_enhance_summary(news_item, relevant_keywords):
    """RSS 요약을 정리하고 개선"""
    title = news_item.get('title', '')
    summary = news_item.get('summary', '')
    
    # HTML 태그 제거
    import re
    summary = re.sub(r'<[^>]+>', '', summary)
    summary = summary.replace('&nbsp;', ' ').replace('&amp;', '&')
    
    # 요약이 있으면 스마트하게 처리
    if summary and len(summary) > 20:
        # 제목과 중복되는 내용 제거
        if title.lower() in summary.lower():
            summary = summary.replace(title, '').strip()
        
        # 키워드 기반 핵심 문장 추출
        enhanced = extract_key_sentences(summary, relevant_keywords)
        return enhanced
    
    # 요약이 없으면 제목에서 키워드 중심으로 설명
    return f"'{', '.join(relevant_keywords[:2])}' 관련 뉴스"

def filter_news_by_keywords(entries, keywords, category_name):
    """키워드로 뉴스 필터링 (향상된 버전)"""
    filtered_news = []
    
    for entry in entries:
        title = entry.title if hasattr(entry, 'title') else ""
        summary = entry.summary if hasattr(entry, 'summary') else ""
        full_text = f"{title} {summary}"
        
        # 키워드 매칭 확인
        matched_keywords = []
        for keyword in keywords:
            if keyword.lower() in full_text.lower():
                matched_keywords.append(keyword)
        
        if matched_keywords:
            # 향상된 요약 생성
            enhanced_summary = clean_and_enhance_summary(
                {'title': title, 'summary': summary}, 
                matched_keywords
            )
            
            filtered_news.append({
                'title': title,
                'link': entry.link if hasattr(entry, 'link') else "",
                'published': entry.published if hasattr(entry, 'published') else 'Unknown',
                'summary': summary,
                'enhanced_summary': enhanced_summary,  # 새로운 필드
                'matched_keywords': matched_keywords,
                'category': category_name,
                'source': '',
                'importance_score': len(matched_keywords)  # 키워드 개수로 중요도 점수
            })
    
    # 중요도 순으로 정렬 (키워드가 많이 매칭된 뉴스 우선)
    filtered_news.sort(key=lambda x: x['importance_score'], reverse=True)
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
    """뉴스 요약 메시지 생성 (향상된 무료 버전)"""
    if not news_list:
        return "📰 오늘은 AI/양자 관련 뉴스가 없습니다."
    
    # 카테고리별로 분류 (이미 중요도순 정렬됨)
    ai_news = [n for n in news_list if n['category'] == 'AI']
    quantum_news = [n for n in news_list if n['category'] == 'Quantum']
    
    # 메시지 구성
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    message = f"🤖 <b>AI & 양자 뉴스 요약</b>\n"
    message += f"📅 {current_time} (한국시간)\n"
    message += f"🎯 총 {len(news_list)}개 뉴스 중 주요 뉴스\n\n"
    
    if ai_news:
        message += f"🤖 <b>AI 뉴스 TOP {min(len(ai_news), max_news//2)}</b>\n\n"
        for i, news in enumerate(ai_news[:max_news//2], 1):
            title = smart_truncate(news['title'], 85)
            
            message += f"<b>{i}. {title}</b>\n"
            message += f"   📰 {news['source']}\n"
            
            # 향상된 요약 사용
            enhanced_summary = news.get('enhanced_summary', '')
            if enhanced_summary and len(enhanced_summary) > 5:
                message += f"   💡 {enhanced_summary}\n"
            
            # 매칭된 키워드 표시 (최대 3개)
            if news.get('matched_keywords'):
                keywords = news['matched_keywords'][:3]
                message += f"   🏷️ {', '.join(keywords)}\n"
            
            message += f"   🔗 <a href='{news['link']}'>기사 보기</a>\n\n"
    
    if quantum_news:
        message += f"⚛️ <b>양자 뉴스 TOP {min(len(quantum_news), max_news//2)}</b>\n\n"
        for i, news in enumerate(quantum_news[:max_news//2], 1):
            title = smart_truncate(news['title'], 85)
            
            message += f"<b>{i}. {title}</b>\n"
            message += f"   📰 {news['source']}\n"
            
            enhanced_summary = news.get('enhanced_summary', '')
            if enhanced_summary and len(enhanced_summary) > 5:
                message += f"   💡 {enhanced_summary}\n"
            
            if news.get('matched_keywords'):
                keywords = news['matched_keywords'][:3]
                message += f"   🏷️ {', '.join(keywords)}\n"
            
            message += f"   🔗 <a href='{news['link']}'>기사 보기</a>\n\n"
    
    # 텔레그램 메시지 길이 제한 (4096자)
    if len(message) > 3800:
        message = message[:3800] + "...\n\n📱 <i>더 많은 뉴스가 있습니다!</i>"
    
    # 통계 정보 추가
    total_ai = len(ai_news)
    total_quantum = len(quantum_news)
    message += f"\n📊 오늘의 뉴스 통계\n"
    message += f"   🤖 AI: {total_ai}개 | ⚛️ 양자: {total_quantum}개\n"
    message += f"\n🔄 <i>다음 업데이트: 12시간 후</i>\n"
    message += f"🤖 <i>스마트 뉴스봇 v2.0</i>"
    
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
