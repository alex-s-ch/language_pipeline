##
import json
from typing import List, Tuple
import pandas as pd
from google.oauth2.service_account import Credentials
from google.cloud import texttospeech
from moviepy.audio.AudioClip import concatenate_audioclips
from pydub import AudioSegment
import io
from moviepy.config import change_settings
from moviepy.editor import TextClip, concatenate_videoclips, AudioFileClip
from config import credential_path, words_file_path, ffmpeg_path


change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})


class TextToSpeechConverterAndVideoGenerator:
    """
    A class to convert text data to speech audio files using Google Text-to-Speech API and generates video based on
    text and the output audio.
    """

    def __init__(self, credentials_path: str):
        """
        Initializes the TextToSpeechConverter with Google API credentials.

        :param credentials_path: Path to the Google API credentials file.
        """
        with open(credentials_path) as key_file:
            key_data = json.load(key_file)
        self.creds = Credentials.from_service_account_info(key_data)
        self.client = texttospeech.TextToSpeechClient(credentials=self.creds)

    def _synthesize_text(self, text: str, language_code: str) -> AudioSegment:
        """
        Synthesize text to speech.

        :param text: Text to be synthesized.
        :param language_code: Language code for the text (e.g. "en-US" or "de-DE").
        :return: AudioSegment of the synthesized speech.
        """
        synthesis_input = texttospeech.SynthesisInput(text=text)
        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code, ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
        response = self.client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
        return AudioSegment.from_mp3(io.BytesIO(response.audio_content))

    @staticmethod
    def _add_silence(audio: AudioSegment, duration: int) -> AudioSegment:
        """
        Add silence before and after the audio.

        :param audio: AudioSegment to add silence to.
        :param duration: Duration of silence in milliseconds.
        :return: AudioSegment with silence added.
        """
        silence = AudioSegment.silent(duration=duration)
        return silence + audio + silence

    @staticmethod
    def _get_orders(language_mode: str) -> List[List[Tuple[str, str]]]:
        orders = [
            [("en-US", "english_word"), ("de-DE", "german_word"), ("en-US", "english_sentence"),
             ("de-DE", "german_sentence")],
            [("de-DE", "german_word"), ("en-US", "english_word"), ("de-DE", "german_sentence"),
             ("en-US", "english_sentence")]
        ]
        if language_mode not in ['EN_DE', 'DE_EN', 'BOTH']:
            raise ValueError("Invalid language_mode. Should be 'EN_DE', 'DE_EN', or 'BOTH'.")
        if language_mode == 'EN_DE':
            process_orders = [orders[0]]
        elif language_mode == 'DE_EN':
            process_orders = [orders[1]]
        else:
            process_orders = orders
        return process_orders

    def generate_audio(self, dataframe: pd.DataFrame, language_version: str) -> None:
        """
        Generate audio files from DataFrame containing text data.

        :param dataframe: DataFrame with columns ['english_word', 'german_word', 'english_sentence', 'german_sentence'].
        :param language_version: Language mode ('EN_DE', 'DE_EN', or 'BOTH').
        """
        process_orders = self._get_orders(language_mode=language_version)

        for i, row in dataframe.iterrows():
            for order_idx, order in enumerate(process_orders):
                combined_audio = None
                for lang, column in order:
                    audio = self._synthesize_text(row[column], lang)
                    audio_with_silence = self._add_silence(audio, 1500)
                    if combined_audio is None:
                        combined_audio = audio_with_silence
                    else:
                        combined_audio += audio_with_silence

                file_index = 0 if language_version != 'BOTH' else order_idx
                filename = f"{i}_{file_index}.mp3"
                combined_audio.export(filename, format="mp3")
                print(f'Audio file "{filename}" created')

    @staticmethod
    def _generate_text_clip(text, audio, duration_split) -> TextClip:
        clip = TextClip(
            text, fontsize=85, color='white', font='Calibri', size=(1920, 1080), method='caption'
        ).set_duration(audio.duration / duration_split)
        return clip

    def generate_video(
            self,
            dataframe: pd.DataFrame,
            words_per_video: int,
            slides_format: str,
            language_version: str,
    ) -> None:
        """
        Generate extended video files from DataFrame containing text data and corresponding audio.

        :param dataframe: DataFrame with columns ['german_word', 'english_word', 'german_sentence', 'english_sentence',
        'level', 'word_type'].
        :param words_per_video: Number of words to be included in one video.
        :param slides_format: Format of the slides ('2slides' or '4slides').
        :param language_version: Language version ('EN_DE' or 'DE_EN').
        """
        orders = {
            "EN_DE": [("en-US", "english_word"), ("de-DE", "german_word"), ("en-US", "english_sentence"),
                      ("de-DE", "german_sentence")],
            "DE_EN": [("de-DE", "german_word"), ("en-US", "english_word"), ("de-DE", "german_sentence"),
                      ("en-US", "english_sentence")]
        }

        if language_version not in orders:
            raise ValueError("Invalid language_version. Should be 'EN_DE' or 'DE_EN'.")

        video_clips = []
        audio_clips = []
        word_count = 0
        unique_words = set()

        for i, row in dataframe.iterrows():
            order = orders[language_version]
            order_idx = 0 if language_version == 'EN_DE' else 1  # 0 for EN_DE and 1 for DE_EN
            audio_filename = f"{i}_{order_idx}.mp3"
            audio = AudioFileClip(audio_filename)
            audio_clips.append(audio)

            clips = []
            if slides_format == '4slides':
                for lang, column in order:
                    text = row[column]
                    clip = self._generate_text_clip(text=text, audio=audio, duration_split=4)
                    clips.append(clip)
            elif slides_format == '2slides':
                text1 = f"{row[order[0][1]]}\n{row[order[1][1]]}"
                text2 = f"{row[order[2][1]]}\n{row[order[3][1]]}"
                clip1 = self._generate_text_clip(text=text1, audio=audio, duration_split=2)
                clip2 = self._generate_text_clip(text=text2, audio=audio, duration_split=2)
                clips.extend([clip1, clip2])
            else:
                raise ValueError("Invalid slides_format. Should be '2slides' or '4slides'.")

            video_clips.append(concatenate_videoclips(clips))

            current_word = row["german_word"]
            if current_word not in unique_words:
                unique_words.add(current_word)
                word_count += 1

            if word_count == words_per_video or i == len(dataframe) - 1:
                final_audio = concatenate_audioclips(audio_clips)
                final_video = concatenate_videoclips(video_clips).set_audio(final_audio)
                final_video.write_videofile(
                    f"combined_video_{i // words_per_video + 1}_{slides_format}_{language_version}.mp4",
                    codec='mpeg4', fps=24)

                video_clips = []
                audio_clips = []
                word_count = 0
                unique_words = set()


converter = TextToSpeechConverterAndVideoGenerator(credentials_path=credential_path)

data = pd.read_excel(words_file_path)
df = pd.DataFrame(data)

converter.generate_audio(dataframe=df, language_version='EN_DE')
converter.generate_video(
    dataframe=df, words_per_video=10, slides_format='2slides', language_version='EN_DE',
)
