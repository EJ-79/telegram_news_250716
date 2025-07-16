import requests
import feedparser
import json
from datetime import datetime, timedelta
import re
from config import (
    EARNINGS_COMPANIES, EARNINGS_RSS_FEEDS, EARNINGS_KEYWORDS,
    FMP_API_KEY, send_telegram_message
)

# Financial Modeling Prep API 설정 (config.py에서 가져옴)

def get_real_earnings_calendar():
    """실제 실적 발표 일정 가져오기 (Financial Modeling Prep API)"""
    try:
        # 오늘부터 7일간의 실적 발표 일정
        today = datetime.now().strftime("%Y-%m-%d")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        url = f"https://financialmodelingprep.com/api/v3/earning_calendar"
        params = {
            'from': today,
            'to': next_week,
            'apikey': FMP_API_KEY
        }
        
        print(f"📡 실적 캘린더 API 호출 중... ({today} ~ {next_week})")
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            earnings_data = response.json()
            print(f"📊 API 응답: {len(earnings_data)}개 실적 발표 예정")
            
            # 관심 기업만 필터링
            relevant_earnings = []
            for earning in earnings_data:
                symbol = earning.get('symbol', '')
                if symbol in EARNINGS_COMPANIES:
                    relevant_earnings.append({
                        'symbol': symbol,
                        'date': earning.get('date', ''),
                        'time': earning.get('time', 'N/A'),
                        'eps_estimated': earning.get('epsEstimated', 'N/A'),
                        'eps_actual': earning.get('eps', 'N/A'),
                        'revenue_estimated': earning.get('revenueEstimated', 'N/A'),
                        'revenue_actual': earning.get('revenue', 'N/A')
                    })
            
            print(f"🎯 관심 기업 실적: {len(relevant_earnings)}개")
            return relevant_earnings
            
        else:
            print(f"❌ API 오류: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ 실적 캘린더 API 오류: {e}")
        return []

def get_earnings_with_fallback():
    """실적 일정 가져오기 (API + RSS 백업)"""
    # 1. 먼저 실제 API로 시도
    api_earnings = get_real_earnings_calendar()
    
    if api_earnings:
        return api_earnings, "API"
    
    # 2. API 실패 시 RSS에서 추출 시도
    print("🔄 API 실패, RSS에서 실적 정보 추출 시도...")
    rss_earnings = extract_earnings_from_rss()
    
    if rss_earnings:
        return rss_earnings, "RSS"
    
    # 3. 둘 다 실패하면 빈 리스트
    return [], "NONE"

def extract_earnings_from_rss():
    """RSS에서 실적 정보 추출"""
    earnings_found = []
    
    for source_name, feed_url in EARNINGS_RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            entries = feed.entries if hasattr(feed, 'entries') else []
            
            for entry in entries[:10]:  # 최신 10개만 확인
                title = entry.title if hasattr(entry, 'title') else ""
                summary = entry.summary if hasattr(entry, 'summary') else ""
                full_text = f"{title} {summary}"
                
                # 이번 주 실적 관련 키워드
                week_keywords = ['this week', 'upcoming earnings', 'earnings calendar', 
                               'earnings preview', 'earnings schedule']
                
                # 키워드 매칭
                has_week_keyword = any(kw.lower() in full_text.lower() for kw in week_keywords)
                
                if has_week_keyword:
                    # 기업 티커 추출
                    companies = extract_company_ticker(full_text)
                    
                    for company in companies:
                        earnings_found.append({
                            'symbol': company,
                            'date': 'This week',
                            'time': 'TBA',
                            'source': f"RSS: {source_name}",
                            'title': title[:100] + "..." if len(title) > 100 else title
                        })
                        
        except Exception as e:
            print(f"❌ RSS 추출 오류 ({source_name}): {e}")
            continue
    
    return earnings_found

def extract_company_ticker(text):
    """텍스트에서 기업 티커 심볼 추출"""
    tickers_found = []
    text_upper = text.upper()
    
    for ticker in EARNINGS_COMPANIES:
        # 티커 심볼이 단어 경계에서 나타나는지 확인
        pattern = r'\b' + re.escape(ticker) + r'\b'
        if re.search(pattern, text_upper):
            tickers_found.append(ticker)
    
    return tickers_found

def extract_earnings_metrics(text):
    """실적 관련 수치 추출"""
    metrics = {}
    
    # EPS 패턴
    eps_pattern = r'EPS.*?(\$?\d+\.?\d*)'
    eps_match = re.search(eps_pattern, text, re.IGNORECASE)
    if eps_match:
        metrics['EPS'] = eps_match.group(1)
    
    # Revenue 패턴 (억/조 단위)
    revenue_patterns = [
        r'revenue.*?(\$?\d+\.?\d*\s*billion)',
        r'revenue.*?(\$?\d+\.?\d*\s*million)',
        r'sales.*?(\$?\d+\.?\d*\s*billion)'
    ]
    
    for pattern in revenue_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            metrics['Revenue'] = match.group(1)
            break
    
    # Beat/Miss 패턴
    if re.search(r'beat.*?estimate', text, re.IGNORECASE):
        metrics['Performance'] = '📈 Beat Estimates'
    elif re.search(r'miss.*?estimate', text, re.IGNORECASE):
        metrics['Performance'] = '📉 Miss Estimates'
    elif re.search(r'inline.*?estimate', text, re.IGNORECASE):
        metrics['Performance'] = '🎯 Inline Estimates'
    
    return metrics

def filter_earnings_news(entries, companies, keywords):
    """실적 관련 뉴스 필터링 및 정리"""
    filtered_news = []
    
    for entry in entries:
        title = entry.title if hasattr(entry, 'title') else ""
        summary = entry.summary if hasattr(entry, 'summary') else ""
        full_text = f"{title} {summary}"
        
        # 키워드 매칭
        keyword_matches = [kw for kw in keywords if kw.lower() in full_text.lower()]
        
        # 회사 티커 매칭
        company_matches = extract_company_ticker(full_text)
        
        if keyword_matches and company_matches:
            # 실적 수치 추출
            metrics = extract_earnings_metrics(full_text)
            
            # HTML 태그 정리
            clean_summary = re.sub(r'<[^>]+>', '', summary)
            clean_summary = clean_summary.replace('&nbsp;', ' ').replace('&amp;', '&')
            
            # 첫 문장만 추출하여 요약으로 사용
            first_sentence = clean_summary.split('.')[0] + '.' if clean_summary else ""
            
            filtered_news.append({
                'title': title,
                'link': entry.link if hasattr(entry, 'link') else "",
                'published': entry.published if hasattr(entry, 'published') else 'Unknown',
                'summary': first_sentence[:150] + "..." if len(first_sentence) > 150 else first_sentence,
                'companies': company_matches,
                'keywords': keyword_matches,
                'metrics': metrics,
                'source': '',
                'importance_score': len(company_matches) + len(keyword_matches)
            })
    
    # 중요도 순으로 정렬
    filtered_news.sort(key=lambda x: x['importance_score'], reverse=True)
    return filtered_news

def collect_earnings_news():
    """모든 소스에서 실적 뉴스 수집"""
    all_earnings_news = []
    
    print("💼 실적 뉴스 수집 시작...")
    
    for source_name, feed_url in EARNINGS_RSS_FEEDS.items():
        print(f"📊 {source_name} 분석 중...")
        try:
            feed = feedparser.parse(feed_url)
            
            if not hasattr(feed, 'entries') or not feed.entries:
                print(f"   ⚠️ {source_name}: 뉴스가 없습니다.")
                continue
            
            # 실적 뉴스 필터링
            earnings_news = filter_earnings_news(
                feed.entries, EARNINGS_COMPANIES, EARNINGS_KEYWORDS
            )
            
            # 소스 정보 추가
            for news in earnings_news:
                news['source'] = source_name
            
            print(f"   💼 실적 관련: {len(earnings_news)}개")
            all_earnings_news.extend(earnings_news)
            
        except Exception as e:
            print(f"   ❌ {source_name} 오류: {e}")
            continue
    
    return all_earnings_news

def create_earnings_summary(earnings_list, max_news=6):
    """실적 요약 메시지 생성"""
    if not earnings_list:
        return "💼 오늘은 주요 기업 실적 뉴스가 없습니다."
    
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M')
    message = f"💼 <b>기업 실적 요약</b>\n"
    message += f"📅 {current_time} (한국시간)\n"
    message += f"🏢 {len(earnings_list)}개 실적 뉴스 중 주요 뉴스\n\n"
    
    # 회사별로 그룹핑
    company_news = {}
    for news in earnings_list:
        for company in news['companies']:
            if company not in company_news:
                company_news[company] = []
            company_news[company].append(news)
    
    # 상위 회사들만 표시
    top_companies = list(company_news.keys())[:max_news]
    
    for i, company in enumerate(top_companies, 1):
        news_items = company_news[company]
        main_news = news_items[0]  # 가장 중요도 높은 뉴스
        
        message += f"<b>{i}. {company}</b>\n"
        
        # 실적 수치가 있으면 표시
        if main_news['metrics']:
            metrics_text = []
            for key, value in main_news['metrics'].items():
                metrics_text.append(f"{key}: {value}")
            if metrics_text:
                message += f"   📊 {' | '.join(metrics_text)}\n"
        
        # 요약
        if main_news['summary']:
            message += f"   💡 {main_news['summary']}\n"
        
        # 출처 및 링크
        message += f"   📰 {main_news['source']}\n"
        message += f"   🔗 <a href='{main_news['link']}'>실적 보기</a>\n\n"
    
    # 통계 정보
    total_companies = len(company_news)
    message += f"📈 <b>실적 요약 통계</b>\n"
    message += f"   🏢 실적 발표 기업: {total_companies}개\n"
    message += f"   📊 총 실적 뉴스: {len(earnings_list)}개\n\n"
    
    # 다음 업데이트 정보
    message += f"🔄 <i>다음 업데이트: 매주 월요일 오전</i>\n"
    message += f"💼 <i>실적봇 v1.0</i>"
    
    return message

def get_upcoming_earnings():
    """이번 주 실적 발표 예정 기업들 (실제 API 데이터)"""
    current_week = datetime.now().strftime("Week of %B %d, %Y")
    
    # 실제 API 데이터 가져오기
    earnings_data, source_type = get_earnings_with_fallback()
    
    message = f"📅 <b>이번 주 실적 발표 예정</b>\n"
    message += f"🗓️ {current_week}\n"
    message += f"📡 데이터 출처: {source_type}\n\n"
    
    if not earnings_data:
        message += f"❌ <b>실적 데이터를 가져올 수 없습니다</b>\n\n"
        message += f"🔍 관심 기업들: {', '.join(EARNINGS_COMPANIES[:5])}...\n"
        message += f"💡 각 기업 IR 페이지에서 정확한 일정을 확인하세요.\n"
        message += f"🔔 실적 발표 시 자동으로 요약을 보내드립니다!"
        return message
    
    # API 데이터로 메시지 구성
    if source_type == "API":
        # 날짜별로 그룹핑
        by_date = {}
        for earning in earnings_data:
            date = earning['date']
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(earning)
        
        for date, companies in sorted(by_date.items()):
            formatted_date = datetime.strptime(date, "%Y-%m-%d").strftime("%m월 %d일 (%a)")
            message += f"📊 <b>{formatted_date}</b>\n"
            
            for earning in companies:
                symbol = earning['symbol']
                time_info = earning['time']
                eps_est = earning['eps_estimated']
                
                message += f"   🏢 <b>{symbol}</b>"
                
                if time_info and time_info != 'N/A':
                    time_kr = "장 시작 전" if time_info == "bmo" else "장 마감 후" if time_info == "amc" else time_info
                    message += f" ({time_kr})"
                
                if eps_est and eps_est != 'N/A':
                    message += f"\n      💰 예상 EPS: ${eps_est}"
                
                message += f"\n"
            
            message += f"\n"
            
    else:  # RSS 데이터
        message += f"📰 <b>RSS에서 발견된 실적 정보:</b>\n\n"
        
        unique_companies = list(set([e['symbol'] for e in earnings_data]))
        for i, company in enumerate(unique_companies[:8], 1):
            message += f"{i}. <b>{company}</b> - 이번 주 실적 발표 예정\n"
    
    message += f"\n💡 <b>정확한 시간과 날짜는 각 기업 IR 페이지를 확인하세요.</b>\n"
    message += f"🔔 실적 발표 시 자동으로 요약을 보내드립니다!\n\n"
    message += f"📈 관심 기업 목록: {', '.join(EARNINGS_COMPANIES[:5])} 외 {len(EARNINGS_COMPANIES)-5}개"
    
    return message

def main():
    """메인 실행 함수"""
    print("💼 실적봇 시작!")
    print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 실적 뉴스 수집
        earnings_list = collect_earnings_news()
        print(f"📊 총 수집된 실적 뉴스: {len(earnings_list)}개")
        
        if earnings_list:
            # 실적 요약 생성
            summary = create_earnings_summary(earnings_list, max_news=5)
        else:
            # 실적 뉴스가 없으면 이번 주 예정 표시
            summary = get_upcoming_earnings()
        
        # 텔레그램 전송
        success = send_telegram_message(summary)
        
        if success:
            print("✅ 실적 요약 전송 완료!")
        else:
            print("❌ 전송 실패")
            
    except Exception as e:
        error_msg = f"❌ 실적봇 실행 오류: {e}"
        print(error_msg)
        
        # 오류 발생 시 관리자에게 알림
        send_telegram_message(f"🚨 <b>실적봇 오류 발생</b>\n\n{error_msg}")

if __name__ == "__main__":
    main()
