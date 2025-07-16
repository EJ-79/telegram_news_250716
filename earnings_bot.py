import requests
import feedparser
import json
from datetime import datetime, timedelta
import re
from config import (
    EARNINGS_COMPANIES, EARNINGS_RSS_FEEDS, EARNINGS_KEYWORDS,
    send_telegram_message
)

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
    """이번 주 실적 발표 예정 기업들 (간단 버전)"""
    # 실제로는 earnings calendar API를 사용해야 하지만
    # 일단 RSS에서 "earnings" + "this week" 같은 키워드로 추정
    upcoming = []
    current_week = datetime.now().strftime("Week of %B %d")
    
    # 임시로 주요 기업들 중 일부를 표시
    # 실제로는 Yahoo Finance나 Earnings Calendar API 사용 권장
    sample_upcoming = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA'][:3]
    
    message = f"📅 <b>이번 주 실적 발표 예정</b>\n"
    message += f"🗓️ {current_week}\n\n"
    
    for i, ticker in enumerate(sample_upcoming, 1):
        message += f"{i}. <b>{ticker}</b> - 실적 발표 예정\n"
    
    message += f"\n💡 정확한 일정은 각 기업 IR 페이지를 확인하세요.\n"
    message += f"🔔 실적 발표 시 자동으로 요약을 보내드립니다!"
    
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
