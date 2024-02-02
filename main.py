# Run with: streamlit run main.py
# Importando bibliotecas
import streamlit as st
import pandas as pd
from langchain.document_loaders import YoutubeLoader
from langchain.chains.summarize import load_summarize_chain
from langchain import OpenAI
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# Função para obter vídeos do YouTube
def get_videos(api_key, term, date_string):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.search().list(
            part='snippet',
            q=term,
            order='viewCount',
            type='video',
            publishedAfter=date_string,
            maxResults=50
        )
        response = request.execute()
        videos = []
        for item in response['items']:
            video_id = item['id']['videoId']
            video_request = youtube.videos().list(
                part="statistics",
                id=video_id
            )
            video_response = video_request.execute()
            video = {
                'title': item['snippet']['title'],
                'published_at': item['snippet']['publishedAt'],
                'description': item['snippet']['description'],
                'channel_title': item['snippet']['channelTitle'],
                'video_id': video_id,
                'view_count': int(video_response['items'][0]['statistics']['viewCount']),
                'url': f'https://www.youtube.com/watch?v={video_id}'
            }
            videos.append(video)
        return videos
    except Exception as e:
        st.write(f"Error getting videos: {e}")
        return []

def get_transcript(video_url):
    loader = YoutubeLoader.from_youtube_url(video_url, add_video_info=True)
    return loader.load()

# Exibir a página inicial
def main():
    st.title('Analista Youtube TLDR')
    st.markdown("## Por favor, insira as chaves de API do YouTube e OpenAI")
    date = datetime.now() - timedelta(days=14)
    date_string = date.isoformat("T") + "Z"  # Convert to YouTube timestamp format

    # Create input fields for API keys
    youtube_api_key = st.text_input("Insira sua chave de API do YouTube aqui", type="password", type="password")
    openai_api_key = st.text_input("Insira sua chave de API da OpenAI aqui", type="password")  # Hide the key

    if st.button('Enviar'):
       st.session_state.youtube_api_key = youtube_api_key
       st.session_state.openai_api_key = openai_api_key  

    # Define the session state
    if 'init' not in st.session_state:
        st.session_state.init = True
        st.session_state.search_term = 'Notícias sobre Inteligência Artificial'
        st.session_state.videos = []
        st.session_state.transcript = []
        st.session_state.selected_video_url = "" # Initialize selected_video_url in session state

    search_term = st.text_input('Entre a expressão de busca', st.session_state.search_term, help = "Pressione Enter para enviar")

    if st.button('Pesquisar'):
        with st.spinner('Buscando vídeos...'):
            st.session_state.videos = get_videos(st.session_state.youtube_api_key, search_term, date_string)

    if st.session_state.videos:
        df = pd.DataFrame(st.session_state.videos)
        if st.checkbox('Mostrar todos os vídeos'):
            st.write(df)  # Debug print
            st.write(st.session_state.videos)  # Debug print
        df = df.sort_values('view_count', ascending=False).head(5)  # Get top 5 videos by view count

        st.subheader('Top 5 Vídeos')
        st.table(df[['title', 'url', 'view_count']].rename(columns={'title': 'título', 'url': 'url', 'view_count': 'visualizações'}))
        if 'selected_video_url' not in st.session_state:
            st.session_state.selected_video_url = ''

        selected_video_title = st.selectbox("Selecione o vídeo para transcrição", options=df['title'], key='video_title')
        selected_video_url = df[df['title'] == selected_video_title]['url'].iloc[0]
        st.session_state.selected_video_url = selected_video_url

       # Only load a new transcript if the URL has changed
        if st.session_state.selected_video_url:  # Use the value from session state
          if st.button('Fazer o resumo'):
            with st.spinner('Criando a transcrição...'):
                st.session_state.transcript = get_transcript(st.session_state.selected_video_url)
                st.write(st.session_state.transcript)

    # Load the summarizer and run it on the transcript
    if st.session_state.transcript:
        llm = OpenAI(openai_api_key=st.session_state.openai_api_key,temperature=0.5)  # Modify the temperature parameter as needed
        chain = load_summarize_chain(llm, chain_type="map_reduce")
        summary = chain.run(st.session_state.transcript)

        # Display the summary
        st.subheader('Resumo do Vídeo')
        st.write(summary)

if __name__ == "__main__":
    main()

