import requests
import feedparser
import json
import re
from datetime import datetime
from config import (
    NEWS_RSS_FEEDS as RSS_FEEDS,
    NEWS_AI_KEYWORDS as AI_KEYWORDS,
    NEWS_QUANTUM_KEYWORDS as QUANTUM_KEYWORDS,
    send_telegram_message
)

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

def collect_filtered_news():
    """모든 사이트에서 뉴스 수집 및 필터링 (멀티소스 버전)"""
    all_filtered_news = []
    
    print("🔍 멀티소스 뉴스 수집 시작...")
    print("="*60)
    
    for site_name, feed_url in RSS_FEEDS.items():
        print(f"\n📰 {site_name} 분석 중...")
        try:
            # RSS 피드 파싱
            feed = feedparser.parse(feed_url)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                print(f"   ❌ {site_name}: 뉴스가 없습니다.")
                continue
            
            print(f"   📊 전체 뉴스: {len(feed.entries)}개")
            
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
            
            # 양자 전문 사이트는 특별히 표시
            if 'quantum' in site_name.lower() or 'physics' in site_name.lower():
                if quantum_news:
                    print(f"   🎯 양자 전문 사이트 매칭: {len(quantum_news)}개")
                    for news in quantum_news[:2]:
                        keywords = news.get('matched_keywords', [])
                        print(f"      ⚛️ {news['title'][:40]}... → {keywords[:2]}")
            
            # 매칭된 키워드 상세 정보 (간략화)
            if ai_news and len(ai_news) <= 3:
                for news in ai_news[:1]:
                    keywords = news.get('matched_keywords', [])
                    print(f"   🎯 AI: {news['title'][:40]}... → {keywords[:2]}")
            
            # 매칭 안 된 경우 (양자 전문 사이트만)
            if (len(ai_news) == 0 and len(quantum_news) == 0 and 
                ('quantum' in site_name.lower() or 'physics' in site_name.lower())):
                print(f"   ❌ 양자 전문 사이트 매칭 실패. 최근 제목:")
                for i, entry in enumerate(feed.entries[:2], 1):
                    title = entry.title if hasattr(entry, 'title') else "제목 없음"
                    print(f"      {i}. {title[:50]}...")
            
            all_filtered_news.extend(ai_news)
            all_filtered_news.extend(quantum_news)
            
        except Exception as e:
            print(f"   💥 {site_name} 오류: {e}")
            continue
    
    print("\n" + "="*60)
    print(f"🎯 총 수집 결과: {len(all_filtered_news)}개 뉴스")
    
    # 사이트별 통계
    site_stats = {}
    ai_stats = {}
    quantum_stats = {}
    
    for news in all_filtered_news:
        source = news.get('source', 'Unknown')
        category = news.get('category', 'Unknown')
        
        site_stats[source] = site_stats.get(source, 0) + 1
        
        if category == 'AI':
            ai_stats[source] = ai_stats.get(source, 0) + 1
        elif category == 'Quantum':
            quantum_stats[source] = quantum_stats.get(source, 0) + 1
    
    print(f"\n📊 사이트별 전체 통계:")
    for site, count in site_stats.items():
        ai_count = ai_stats.get(site, 0)
        quantum_count = quantum_stats.get(site, 0)
        print(f"   {site}: {count}개 (AI {ai_count}개, 양자 {quantum_count}개)")
    
    # 양자 전문 사이트 성과
    quantum_sites = [s for s in site_stats.keys() if 'quantum' in s.lower() or 'physics' in s.lower()]
    if quantum_sites:
        print(f"\n⚛️ 양자 전문 사이트 성과:")
        for site in quantum_sites:
            q_count = quantum_stats.get(site, 0)
            total = site_stats.get(site, 0)
            print(f"   {site}: 양자 {q_count}개 / 전체 {total}개")
    
    return all_filtered_news

def balance_news_by_source_advanced(news_list, max_count, max_per_source=2):
    """고급 사이트별 균형 배분 - 라운드 로빈 방식"""
    if not news_list:
        return []
    
    # 사이트별로 뉴스 그룹핑
    news_by_source = {}
    for news in news_list:
        source = news['source']
        if source not in news_by_source:
            news_by_source[source] = []
        news_by_source[source].append(news)
    
    # 각 사이트의 뉴스를 중요도순으로 정렬
    for source in news_by_source:
        news_by_source[source].sort(key=lambda x: x['importance_score'], reverse=True)
    
    balanced = []
    source_count = {source: 0 for source in news_by_source}
    
    # 라운드 로빈으로 각 사이트에서 순차적으로 선택
    round_num = 0
    sources = list(news_by_source.keys())
    
    while len(balanced) < max_count and round_num < max_per_source:
        added_this_round = False
        
        for source in sources:
            if len(balanced) >= max_count:
                break
                
            # 해당 사이트에서 이번 라운드에 선택할 뉴스가 있는지 확인
            if (round_num < len(news_by_source[source]) and 
                source_count[source] < max_per_source):
                
                news_item = news_by_source[source][round_num]
                balanced.append(news_item)
                source_count[source] += 1
                added_this_round = True
        
        if not added_this_round:
            break
            
        round_num += 1
    
    return balanced

def create_news_summary(news_list, max_news=18):
    """뉴스 요약 메시지 생성 (고급 사이트별 균형 버전)"""
    if not news_list:
        return "📰 오늘은 AI/양자 관련 뉴스가 없습니다."
    
    # 카테고리별로 분류 (이미 중요도순 정렬됨)
    ai_news = [n for n in news_list if n['category'] == 'AI']
    quantum_news = [n for n in news_list if n['category'] == 'Quantum']
    
    # 고급 사이트별 균형 맞추기
    ai_show = balance_news_by_source_advanced(ai_news, max_count=12, max_per_source=2)
    quantum_show = balance_news_by_source_advanced(quantum_news, max_count=6, max_per_source=2)
    
    # 메시지 구성
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    message = f"🤖 <b>AI & 양자 뉴스 요약</b>\n"
    message += f"📅 {current_time} (한국시간)\n"
    message += f"🎯 총 {len(news_list)}개 뉴스 중 균형 선별 뉴스\n\n"
    
    if ai_show:
        # 사이트별 통계
        ai_sources = {}
        for news in ai_show:
            source = news['source']
            ai_sources[source] = ai_sources.get(source, 0) + 1
        
        source_info = ", ".join([f"{source} {count}개" for source, count in ai_sources.items()])
        message += f"🤖 <b>AI 뉴스 ({len(ai_show)}개)</b>\n"
        message += f"   📊 출처: {source_info}\n\n"
        
        for i, news in enumerate(ai_show, 1):
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
    
    if quantum_show:
        # 사이트별 통계
        quantum_sources = {}
        for news in quantum_show:
            source = news['source']
            quantum_sources[source] = quantum_sources.get(source, 0) + 1
        
        source_info = ", ".join([f"{source} {count}개" for source, count in quantum_sources.items()])
        message += f"⚛️ <b>양자 뉴스 ({len(quantum_show)}개)</b>\n"
        message += f"   📊 출처: {source_info}\n\n"
        
        for i, news in enumerate(quantum_show, 1):
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
    
    # 전체 사이트별 통계
    all_sources = {}
    for news in ai_show + quantum_show:
        source = news['source']
        all_sources[source] = all_sources.get(source, 0) + 1
    
    # 사이트 수 계산
    total_sources = len(set([n['source'] for n in news_list]))
    shown_sources = len(all_sources)
    
    message += f"\n📊 <b>오늘의 뉴스 통계</b>\n"
    message += f"   🤖 AI: {total_ai}개 → 표시 {len(ai_show)}개\n"
    message += f"   ⚛️ 양자: {total_quantum}개 → 표시 {len(quantum_show)}개\n"
    message += f"   📰 활성 사이트: {shown_sources}/{total_sources}개\n"
    message += f"   🎯 균형 배분: {', '.join([f'{s} {c}개' for s, c in all_sources.items()])}\n"
    message += f"\n🔄 <i>다음 업데이트: 12시간 후</i>\n"
    message += f"🤖 <i>멀티소스 뉴스봇 v3.0</i>"
    
    return message

def main():
    """메인 실행 함수"""
    print("🚀 멀티소스 뉴스봇 v3.0 시작!")
    print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 총 {len(RSS_FEEDS)}개 사이트 모니터링 중...")
    
    try:
        # 1. 뉴스 수집
        news_list = collect_filtered_news()
        print(f"📊 총 수집된 뉴스: {len(news_list)}개")
        
        # 2. 요약 생성
        summary = create_news_summary(news_list, max_news=18)
        
        # 3. 텔레그램 전송
        success = send_telegram_message(summary)
        
        if success:
            print("✅ 뉴스 요약 전송 완료!")
        else:
            print("❌ 전송 실패")
            
    except Exception as e:
        error_msg = f"❌ 멀티소스 뉴스봇 실행 오류: {e}"
        print(error_msg)
        
        # 오류 발생 시 관리자에게 알림
        send_telegram_message(f"🚨 <b>뉴스봇 오류 발생</b>\n\n{error_msg}")

if __name__ == "__main__":
    main()
