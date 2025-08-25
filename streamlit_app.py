# streamlit_app.py

import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import random
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# ----------------------------------
# 페이지 기본 설정
# ----------------------------------
st.set_page_config(
    page_title="생일 발매 K-Pop & 영화",
    page_icon="📀",
    layout="wide",
)

# ----------------------------------
# API 데이터 로딩 함수 (캐싱 적용)
# ----------------------------------
# @st.cache_data: 함수의 실행 결과를 캐시에 저장하여, 동일한 입력값으로 함수가 다시 호출될 때
#                 시간이 걸리는 작업을 반복하지 않고 저장된 결과를 즉시 반환합니다.
#                 API 호출 시 앱 성능을 크게 향상시킬 수 있습니다.

@st.cache_data
def get_spotify_releases(month, day, sp_client):
    """
    지정된 날짜(월, 일)에 발매된 K-Pop 앨범을 Spotify API를 통해 검색합니다.
    
    Args:
        month (int): 월
        day (int): 일
        sp_client (spotipy.Spotify): 인증된 Spotipy 클라이언트 객체

    Returns:
        list: 앨범 정보가 담긴 딕셔너리 리스트.
    """
    albums_found = []
    # 검색할 연도 범위를 지정 (예: 2000년부터 작년까지)
    current_year = datetime.now().year
    years_to_search = range(current_year - 1, 2000, -1)
    
    # 여러 해에 걸쳐 검색하여 더 많은 결과를 찾습니다.
    for year in random.sample(years_to_search, min(len(years_to_search), 10)): # 최대 10개 연도 랜덤 샘플링
        try:
            # Spotify 검색 쿼리: 특정 연도의 K-Pop 앨범 검색
            query = f'genre:"k-pop" year:{year}'
            results = sp_client.search(q=query, type='album', limit=50, market='KR')
            
            for album in results['albums']['items']:
                # 앨범의 발매일을 확인하고, 사용자가 입력한 월/일과 일치하는지 검사합니다.
                # release_date_precision이 'day'인 경우에만 정확한 날짜 비교가 가능합니다.
                if album['release_date_precision'] == 'day':
                    release_date = datetime.strptime(album['release_date'], '%Y-%m-%d')
                    if release_date.month == month and release_date.day == day:
                        albums_found.append(album)
            
            # 충분한 결과를 찾으면 검색을 조기 종료하여 속도를 높입니다.
            if len(albums_found) > 5:
                break
        except Exception:
            continue # API 오류 발생 시 해당 연도는 건너뜁니다.
            
    return albums_found

@st.cache_data
def get_movie_recommendations(month, day, api_key):
    """
    지정된 날짜(월, 일)에 개봉한 영화 목록을 TMDb API를 통해 가져옵니다.
    """
    if not api_key:
        st.error("TMDb API 키가 설정되지 않았습니다. .streamlit/secrets.toml 파일을 확인해주세요.")
        return []
    
    movies = []
    current_year = datetime.now().year
    # 최근 20년 동안 해당 날짜(MM-DD)에 개봉한 영화를 모두 탐색합니다.
    for year in range(current_year, current_year - 20, -1):
        try:
            release_date = f"{year}-{month:02d}-{day:02d}"
            url = (
                f"https://api.themoviedb.org/3/discover/movie?api_key={api_key}"
                f"&language=ko-KR&region=KR&sort_by=popularity.desc"
                f"&primary_release_date.gte={release_date}&primary_release_date.lte={release_date}"
            )
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("results"):
                movies.extend(data["results"])
        except requests.exceptions.RequestException:
            continue
            
    return movies

# ----------------------------------
# 앱 UI 및 로직
# ----------------------------------
st.title("📀 당신의 생일, K-Pop & 영화 발매 뉴스")
st.markdown("생일(월/일)을 입력하면, 역대 당신의 생일에 발매된 K-Pop 앨범과 영화들을 찾아드립니다!")
st.markdown("---")

# --- 사이드바: 날짜 입력 ---
with st.sidebar:
    st.header("🎂 생일 입력")
    today = datetime.now()
    with st.form("birth_form"):
        month = st.selectbox("**월(Month)**", range(1, 13), index=today.month - 1)
        day = st.selectbox("**일(Day)**", range(1, 32), index=today.day - 1)
        submitted = st.form_submit_button("🎉 내 생일 뉴스 확인하기!")

# --- 메인 로직: 버튼 클릭 후 뉴스 생성 ---
if submitted:
    # --- API 키 및 클라이언트 설정 ---
    try:
        tmdb_api_key = st.secrets["tmdb"]["api_key"]
        spotify_client_id = st.secrets["spotify"]["client_id"]
        spotify_client_secret = st.secrets["spotify"]["client_secret"]
        
        # Spotify 클라이언트 인증
        auth_manager = SpotifyClientCredentials(client_id=spotify_client_id, client_secret=spotify_client_secret)
        sp = spotipy.Spotify(auth_manager=auth_manager)
    except (KeyError, FileNotFoundError):
        st.error("API 키를 찾을 수 없습니다. `.streamlit/secrets.toml` 파일에 TMDb와 Spotify 키를 모두 설정해주세요.")
        st.stop()

    # 두 정보를 동시에 보여주기 위해 컬럼 레이아웃 사용
    col1, col2 = st.columns(2)

    # --- K-Pop 발매 앨범 섹션 ---
    with col1:
        st.subheader(f"🎤 역대 {month}월 {day}일에 발매된 K-Pop")
        with st.spinner('당신의 생일에 발매된 K-Pop 앨범을 찾고 있습니다...'):
            albums = get_spotify_releases(month, day, sp)
        
        if albums:
            st.success("당신의 생일에 이런 명반들이 발매되었어요!")
            # 중복 앨범 제거 및 발매일 순 정렬
            unique_albums = {album['id']: album for album in albums}.values()
            sorted_albums = sorted(unique_albums, key=lambda x: x['release_date'], reverse=True)

            for album in sorted_albums[:5]: # 최대 5개 표시
                artist_name = ", ".join([artist['name'] for artist in album['artists']])
                st.markdown(f"**{album['name']}** - {artist_name}")
                if album['images']:
                    st.image(album['images'][0]['url'])
                st.caption(f"발매일: {album['release_date']}")
                st.markdown(f"[🎧 Spotify에서 듣기]({album['external_urls']['spotify']})")
                st.divider()
        else:
            st.info("아쉽게도 당신의 생일에 발매된 K-Pop 앨범 정보를 찾지 못했어요.")

    # --- 영화 개봉작 섹션 ---
    with col2:
        st.subheader(f"🎬 역대 {month}월 {day}일에 개봉한 영화")
        with st.spinner('당신의 생일에 개봉한 영화들을 찾고 있습니다...'):
            movies = get_movie_recommendations(month, day, tmdb_api_key)
            
        if movies:
            st.success("당신의 생일에 이런 영화들이 개봉했어요!")
            # 중복 영화 제거 및 평점 순 정렬
            unique_movies = {movie['id']: movie for movie in movies}.values()
            sorted_movies = sorted(unique_movies, key=lambda x: x.get('vote_average', 0), reverse=True)

            for movie in sorted_movies[:5]: # 최대 5개 표시
                st.markdown(f"**{movie.get('title', '제목 없음')}**")
                if movie.get("poster_path"):
                    st.image(f"https://image.tmdb.org/t/p/w500{movie['poster_path']}")
                st.caption(f"개봉일: {movie.get('release_date', '정보 없음')} | 평점: ⭐ {movie.get('vote_average', 0):.1f}")
                st.divider()
        else:
            st.info("아쉽게도 당신의 생일에 개봉한 영화 정보를 찾지 못했어요.")

else:
    # 앱 초기 화면 안내
    st.info("⬅️ 왼쪽 사이드바에서 생일을 선택하고 버튼을 눌러주세요!")
    st.image("https://images.pexels.com/photos/374624/pexels-photo-374624.jpeg",
             caption="당신의 생일은 어떤 멋진 콘텐츠들과 함께했을까요?")