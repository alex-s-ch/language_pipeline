##
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from youtube_description import description, tags
from config import thumbnail_path_, video_path, youtube_key_path


class YoutubeVideoPublisher:

    def __init__(self, client_secrets_file: str):
        self.client_secrets_file = client_secrets_file
        self.scopes = ["https://www.googleapis.com/auth/youtube.upload",
                       "https://www.googleapis.com/auth/youtube"]
        self.youtube = self.authenticate_youtube_api()

    def authenticate_youtube_api(self):
        flow = InstalledAppFlow.from_client_secrets_file(
            self.client_secrets_file, self.scopes)
        credentials = flow.run_local_server(port=0)
        return build("youtube", "v3", credentials=credentials)

    def upload_video(
            self, video_file_path: str, title: str, thumbnail_path: str, playlist_id: str, visibility="private",
    ) -> None:
        request_body = {
            "snippet": {
                "categoryId": "27",
                "title": title,
                "description": description,
                "tags": tags,
                "defaultAudioLanguage": "en"
            },
            "status": {
                "privacyStatus": visibility,
                "madeForKids": False,
            }
        }

        media = MediaFileUpload(video_file_path, chunksize=-1, resumable=True)
        request = self.youtube.videos().insert(
            part="snippet,status",
            body=request_body,
            media_body=media,
        )
        response = request.execute()

        video_id = response["id"]

        request = self.youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        )
        request.execute()

        playlist_item_body = {
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id
                }
            }
        }
        request = self.youtube.playlistItems().insert(
            part="snippet",
            body=playlist_item_body
        )
        request.execute()

        print(f"Video uploaded and added to playlist with video id: {video_id}")


publisher = YoutubeVideoPublisher(youtube_key_path)

publisher.upload_video(
    video_file_path=f"{video_path}/combined_video_2_2slides_EN_DE.mp4",
    title="🎯 Get Fluent in German Faster: 10 German A1 Verbs | usage in sentence 🗣️ [2 Slides]",
    thumbnail_path=thumbnail_path_,
    playlist_id="PLAjw2wTAAz0b8HMusQdL2hQFXwnzMiOBV",
    visibility="public"
)
