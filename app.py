import streamlit as st
import googleapiclient.discovery
import google.generativeai as genai
import pandas as pd

# --- SECRETS SETUP (Cloud Ready) ---
# This block tells the app to look for keys in the "Secret Box"
try:
    YOUTUBE_API_KEY = st.secrets["YOUTUBE_API_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    st.error("Secrets not found! If running locally, make sure you have a .streamlit/secrets.toml file.")
    st.stop() # Stop the app if keys are missing

# --- CONFIGURE AI ---
genai.configure(api_key=GEMINI_API_KEY)

# --- FUNCTIONS (The Engine) ---
def get_channel_stats(youtube, channel_id):
    request = youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id=channel_id
    )
    response = request.execute()
    if response['items']:
        return response['items'][0]
    return None

def get_video_ids(youtube, playlist_id):
    video_ids = []
    request = youtube.playlistItems().list(
        part="contentDetails",
        playlistId=playlist_id,
        maxResults=10 # Fetching 10 videos for speed
    )
    response = request.execute()
    for item in response['items']:
        video_ids.append(item['contentDetails']['videoId'])
    return video_ids

def get_video_details(youtube, video_ids):
    all_video_info = []
    request = youtube.videos().list(
        part="snippet,statistics",
        id=','.join(video_ids)
    )
    response = request.execute()
    for video in response['items']:
        stats = video['statistics']
        snippet = video['snippet']
        video_data = {
            'Title': snippet['title'],
            'Views': int(stats.get('viewCount', 0)),
            'Likes': int(stats.get('likeCount', 0)),
            'Comments': int(stats.get('commentCount', 0)),
            'Thumbnail': snippet['thumbnails']['high']['url']
        }
        all_video_info.append(video_data)
    return all_video_info

def analyze_with_gemini(df):
    model = genai.GenerativeModel('gemini-2.5-flash')
    data_summary = df[['Title', 'Views', 'Likes']].head(5).to_string()
    
    prompt = f"""
    You are a viral content consultant. 
    Analyze these video stats:
    {data_summary}
    
    1. Identify the highest performing video.
    2. Suggest 3 follow-up video titles that would go viral based on this style.
    3. Keep it short and exciting.
    """
    response = model.generate_content(prompt)
    return response.text

# --- THE APP UI (The Face) ---
st.set_page_config(page_title="TubeMind AI", page_icon="🧠", layout="wide")

st.title("🧠 TubeMind AI")
st.subheader("The AI-Powered Content Strategist")

# Sidebar for Input
with st.sidebar:
    st.header("👇 Enter Channel Details")
    channel_id_input = st.text_input("YouTube Channel ID", value="UCeVMnSShP_Iviwkknt83cww")
    if st.button("Analyze Channel"):
        st.session_state['analyze'] = True

# Main Area
if st.session_state.get('analyze'):
    try:
        # 1. Connect
        youtube = googleapiclient.discovery.build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        
        # 2. Get Data
        with st.spinner("Fetching Channel Data..."):
            channel_info = get_channel_stats(youtube, channel_id_input)
            
        if channel_info:
            # Display Channel Header
            st.image(channel_info['snippet']['thumbnails']['medium']['url'], width=100)
            st.write(f"**Channel:** {channel_info['snippet']['title']}")
            st.write(f"**Subscribers:** {channel_info['statistics']['subscriberCount']}")
            
            # 3. Get Videos
            uploads_id = channel_info['contentDetails']['relatedPlaylists']['uploads']
            video_ids = get_video_ids(youtube, uploads_id)
            video_data = get_video_details(youtube, video_ids)
            df = pd.DataFrame(video_data)
            
            # Display Charts
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📈 View Count Analysis")
                st.bar_chart(df, x="Title", y="Views")
            with col2:
                st.subheader("👍 Likes Analysis")
                st.line_chart(df, x="Title", y="Likes")

            # 4. AI Analysis
            st.divider()
            st.subheader("🤖 AI Consultant Report")
            with st.spinner("Gemini is analyzing the trends..."):
                analysis = analyze_with_gemini(df)
                st.success("Analysis Complete!")
                st.markdown(analysis)
                
        else:
            st.error("Channel not found! Check the ID.")
            
    except Exception as e:
        st.error(f"Error: {e}")