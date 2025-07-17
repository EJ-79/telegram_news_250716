import requests
import feedparser
import json
import re
import time
from datetime import datetime
from config import (
    NEWS_RSS_FEEDS as RSS_FEEDS,
    NEWS_AI_KEYWORDS as AI_KEYWORDS,
    NEWS_QUANTUM_KEYWORDS as QUANTUM_KEYWORDS,
    send_telegram_message
)

def check_keywords_in_text(text, keywords):
    """개선된 키워드 매칭 - 단어 경계 고려"""
    if not text:
        return False
    
    text_lower = text.lower()
    
    for keyword in keywords:
        keyword_lower = keyword.lower()
        
        # 단일 단어인 경우 단어 경계 체크
        if ' ' not in keyword_lower:
            # 단어 경계에서만 매칭 (예: "AI"가 "said"에 매칭되지 않도록)
            pattern = r'\b' + re.escape(keyword_lower) + r'\b'
            if re.search(pattern, text_lower):
                return True
        else:
            # 구문의 경우 그대로 체크
            if keyword_lower in text_lower:
                return True
    
    return False

def filter_news_by_keywords(entries, keywords, category_name):
    """향상된 키워드 필터링 - 품질 개선"""
    filtered_news = []
    
    for entry in entries:
        title = entry.title if hasattr(entry, 'title') else ""
        summary = entry.summary if hasattr(entry, 'summary') else ""
        full_text = f"{title} {summary}"
        
        # 개선된 키워드 매칭
        if not check_keywords_in_text(full_text, keywords):
            continue
            
        # 매칭된 키워드들 수집
        matched_keywords = []
        full_text_lower = full_text.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            if ' ' not in keyword_lower:
                # 단어 경계 체크
                pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                if re.search(pattern, full_text_lower):
                    matched_keywords.append(keyword)
            else:
                # 구문 체크
                if keyword_lower in full_text_lower:
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
                'enhanced_summary': enhanced_summary,
                'matched_keywords': matched_keywords,
                'category': category_name,
                'source': '',
                'importance_score': len(matched_keywords)
            })
    
    # 중요도 순으로 정렬
    filtered_news.sort(key=lambda x: x['importance_score'], reverse=True)
    return filtered_news

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
    """RSS 요약을 정리하고 개선 - 더 나은 첫 문장 추출"""
    title = news_item.get('title', '')
    summary = news_item.get('summary', '')
    
    # HTML 태그 제거
    summary = re.sub(r'<[^>]+>', '', summary)
    summary = summary.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&quot;', '"')
    
    # 요약이 있으면 스마트하게 처리
    if summary and len(summary) > 30:
        # 제목과 중복되는 내용 제거
        title_words = set(title.lower().split())
        
        # 문장들로 분리
        sentences = re.split(r'[.!?]+', summary)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        
        # 첫 번째로 의미있는 문장 찾기
        for sentence in sentences[:3]:  # 처음 3문장만 확인
            sentence_words = set(sentence.lower().split())
            
            # 제목과 너무 중복되지 않고, 키워드를 포함하는 문장 선호
            title_overlap = len(title_words & sentence_words) / max(len(title_words), 1)
            has_keyword = any(kw.lower() in sentence.lower() for kw in relevant_keywords)
            
            if title_overlap < 0.7 and (has_keyword or len(sentence) > 40):
                # 문장이 완전하지 않으면 보완
                if not sentence.endswith(('.', '!', '?')):
                    sentence += '.'
                return sentence
        
        # 적절한 문장이 없으면 첫 번째 문장 사용
        if sentences:
            first_sentence = sentences[0]
            if not first_sentence.endswith(('.', '!', '?')):
                first_sentence += '.'
            return first_sentence
    
    # 요약이 없거나 짧으면 키워드 기반 설명
    return f"{', '.join(relevant_keywords[:2])} 관련 뉴스입니다."

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
    """스마트하게 텍스트 자르기 - 더 관대한 설정"""
    if len(text) <= length:
        return text
    
    # 제목은 충분히 길게 표시 (기본 150자까지)
    if length < 150:
        length = 150
    
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

def create_ai_news_summary(ai_news):
    """AI 뉴스 전용 메시지 생성"""
    if not ai_news:
        return None
    
    ai_show = balance_news_by_source_advanced(ai_news, max_count=12, max_per_source=2)
    
    current_time = datetime.now().strftime('%m/%d %H:%M')
    message = f"🤖 <b>AI 뉴스 요약</b> ({current_time})\n"
    message += f"📊 총 {len(ai_news)}개 중 {len(ai_show)}개 선별 (사이트별 균형)\n\n"
    
    # 사이트별 통계
    ai_sources = {}
    for news in ai_show:
        source = news['source']
        ai_sources[source] = ai_sources.get(source, 0) + 1
    
    source_info = ", ".join([f"{source} {count}개" for source, count in ai_sources.items()])
    message += f"📰 출처: {source_info}\n\n"
    
    for i, news in enumerate(ai_show, 1):
        # 제목 전체 표시 (자르지 않음)
        title = news['title']
        
        message += f"<b>{i}. {title}</b>\n"
        message += f"   📰 {news['source']}"
        
        # 매칭된 키워드 표시
        if news.get('matched_keywords'):
            keywords = news['matched_keywords'][:3]
            message += f" | 🏷️ {', '.join(keywords)}"
        
        message += f"\n"
        
        # 향상된 요약(첫 문장) 표시
        enhanced_summary = news.get('enhanced_summary', '')
        if enhanced_summary and len(enhanced_summary) > 10:
            message += f"   💡 {enhanced_summary}\n"
        
        message += f"   🔗 <a href='{news['link']}'>기사 보기</a>\n\n"
    
    message += f"🔄 다음 업데이트: 12시간 후 | 🤖 AI뉴스봇 v3.2"
    
    return message

def create_quantum_news_summary(quantum_news):
    """양자 뉴스 전용 메시지 생성"""
    if not quantum_news:
        return None
    
    quantum_show = balance_news_by_source_advanced(quantum_news, max_count=6, max_per_source=2)
    
    current_time = datetime.now().strftime('%m/%d %H:%M')
    message = f"⚛️ <b>양자 뉴스 요약</b> ({current_time})\n"
    message += f"📊 총 {len(quantum_news)}개 중 {len(quantum_show)}개 선별 (사이트별 균형)\n\n"
    
    # 사이트별 통계
    quantum_sources = {}
    for news in quantum_show:
        source = news['source']
        quantum_sources[source] = quantum_sources.get(source, 0) + 1
    
    source_info = ", ".join([f"{source} {count}개" for source, count in quantum_sources.items()])
    message += f"📰 출처: {source_info}\n\n"
    
    for i, news in enumerate(quantum_show, 1):
        # 제목 전체 표시 (자르지 않음)
        title = news['title']
        
        message += f"<b>{i}. {title}</b>\n"
        message += f"   📰 {news['source']}"
        
        # 매칭된 키워드 표시
        if news.get('matched_keywords'):
            keywords = news['matched_keywords'][:3]
            message += f" | 🏷️ {', '.join(keywords)}"
        
        message += f"\n"
        
        # 향상된 요약(첫 문장) 표시
        enhanced_summary = news.get('enhanced_summary', '')
        if enhanced_summary and len(enhanced_summary) > 10:
            message += f"   💡 {enhanced_summary}\n"
        
        message += f"   🔗 <a href='{news['link']}'>기사 보기</a>\n\n"
    
    message += f"🔄 다음 업데이트: 12시간 후 | ⚛️ 양자뉴스봇 v3.2"
    
    return message

def create_news_summary(news_list, max_news=18):
    """뉴스 요약 메시지 생성 - 두 개 메시지 방식"""
    if not news_list:
        return "📰 오늘은 AI/양자 관련 뉴스가 없습니다.", None
    
    # 카테고리별로 분류
    ai_news = [n for n in news_list if n['category'] == 'AI']
    quantum_news = [n for n in news_list if n['category'] == 'Quantum']
    
    # 각각 별도 메시지 생성
    ai_message = create_ai_news_summary(ai_news)
    quantum_message = create_quantum_news_summary(quantum_news)
    
    return ai_message, quantum_message

def main():
    """메인 실행 함수 - 두 개 메시지 전송"""
    print("🚀 분할 메시지 뉴스봇 v3.2 시작!")
    print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 총 {len(RSS_FEEDS)}개 사이트 모니터링")
    print(f"📱 AI 뉴스와 양자 뉴스를 별도 메시지로 전송")
    
    try:
        # 1. 뉴스 수집
        news_list = collect_filtered_news()
        print(f"📊 총 수집된 뉴스: {len(news_list)}개")
        
        # 2. 카테고리별 분석
        ai_count = len([n for n in news_list if n['category'] == 'AI'])
        quantum_count = len([n for n in news_list if n['category'] == 'Quantum'])
        print(f"   🤖 AI 뉴스: {ai_count}개")
        print(f"   ⚛️ 양자 뉴스: {quantum_count}개")
        
        # 3. 메시지 생성 (두 개 별도)
        ai_message, quantum_message = create_news_summary(news_list)
        
        # 4. 메시지 길이 확인
        if ai_message:
            print(f"📝 AI 메시지 길이: {len(ai_message)}자")
        if quantum_message:
            print(f"📝 양자 메시지 길이: {len(quantum_message)}자")
        
        # 5. 텔레그램 전송 (순차적)
        success_count = 0
        
        if ai_message:
            print("📤 AI 뉴스 메시지 전송 중...")
            if send_telegram_message(ai_message):
                print("✅ AI 뉴스 전송 성공!")
                success_count += 1
            else:
                print("❌ AI 뉴스 전송 실패")
        
        # 잠깐 대기 (텔레그램 API 제한 고려)
        time.sleep(2)
        
        if quantum_message:
            print("📤 양자 뉴스 메시지 전송 중...")
            if send_telegram_message(quantum_message):
                print("✅ 양자 뉴스 전송 성공!")
                success_count += 1
            else:
                print("❌ 양자 뉴스 전송 실패")
        
        # 6. 결과 요약
        total_messages = (1 if ai_message else 0) + (1 if quantum_message else 0)
        print(f"🎯 전송 결과: {success_count}/{total_messages}개 메시지 성공")
        
        if success_count == 0:
            print("❌ 모든 메시지 전송 실패")
        elif success_count == total_messages:
            print("✅ 모든 뉴스 전송 완료!")
        else:
            print("⚠️ 일부 메시지 전송 실패")
            
    except Exception as e:
        error_msg = f"❌ 분할 메시지 뉴스봇 v3.2 실행 오류: {e}"
        print(error_msg)
        
        # 오류 발생 시 관리자에게 알림
        send_telegram_message(f"🚨 <b>뉴스봇 오류 발생</b>\n\n{error_msg}")

if __name__ == "__main__":
    main()
