##
from typing import List, Dict, Tuple
import pandas as pd
import os
from dotenv import load_dotenv, find_dotenv
import openai
from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import ResponseSchema
from langchain.output_parsers import StructuredOutputParser
from config import path_vocabulary, path_project


_ = load_dotenv(find_dotenv())
openai.api_key = os.environ['OPENAI_API_KEY']


class SentenceGenerator:
    template_string = """
        For the German word ```{german_word}``` which is of type ```{word_type}```, please follow these steps:

        Steps:
        1. german_word: Return the German word as a list of strings, repeating it only if it has distinctly different \
        meanings that are not synonymous or interchangeable. \
        For example, if the word "annehmen" has two distinct meanings "to accept" and "to assume", list it twice.

        2. english_word: Translate the German word to English, and list only the distinctly different and \
        most important (frequently used) meanings as a list of strings. \
        Do not include meanings that are synonymous or interchangeable.

        3. german_sentence: Create a sentence in German using the word ```{german_word}``` that reflects \
        each distinct meaning. The sentence should be at difficulty level ```{level}```. \
        Return these sentences as a list of strings.

        4. english_sentence: Translate the sentences in the 'german_sentence' list to English, \
        and return them as a list of strings.

        Ensure that all the lists have the same length. Make sure the sentences are a little creative, interesting, fun.

        {format_instructions}
        """

    model_original = 'gpt-3.5-turbo'
    model_better = 'gpt-3.5-turbo-16k'

    def __init__(self):
        self.chunks = dict()

    @staticmethod
    def _get_output_parser_and_format_instructions() -> Tuple[StructuredOutputParser, str]:
        """
        Creates a StructuredOutputParser object and a string of format instructions for the API
        response and returns them as a tuple.

        :return:
        A tuple of a StructuredOutputParser object and a string of format instructions for the API response.
        """
        german_word_schema = ResponseSchema(
            name="german_word",
            description='Return the German word as a list of strings, repeating it only if it has distinctly different \
            meanings that are not synonymous or interchangeable. \
            For example, if the word "annehmen" has two distinct meanings "to accept" and "to assume", list it twice.',
        )
        english_word_schema = ResponseSchema(
            name="english_word",
            description="Translate the German word to English, and list only the distinctly different and \
            most important (frequently used) meanings as a list of strings. \
            Do not include meanings that are synonymous or interchangeable.",
        )
        german_sentence_schema = ResponseSchema(
            name="german_sentence",
            description="Create a sentence in German using the word ```{german_word}``` that reflects \
            each distinct meaning. The sentence should be at difficulty level ```{level}```. \
            Return these sentences as a list of strings.",
        )
        english_sentence_schema = ResponseSchema(
            name="english_sentence",
            description="Translate the sentences in the 'german_sentence' list to English, \
            and return them as a list of strings.",
        )
        response_schemas = [german_word_schema, english_word_schema, german_sentence_schema, english_sentence_schema]
        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
        format_instructions = output_parser.get_format_instructions()
        return output_parser, format_instructions

    def _get_api_response(self, word: str, wordtype: str, level: str) -> Dict:
        """
        Sends a prompt to the GPT-3.5 API containing a German word, its type, and CEFR level, and
        returns a dictionary of sentences and their translations.

        :param word: a string representing the German word to be used in the prompt
        :param wordtype: a string representing the type of the German word (e.g. noun, verb, adjective)
        :param level: a string representing the CEFR level of the word (e.g. A1, A2, B1, B2, C1)

        :return:
        A dictionary containing lists of German sentences, English translations, and other information.
        """
        chat = ChatOpenAI(temperature=0.0, model_name=self.model_better)

        prompt_template = ChatPromptTemplate.from_template(self.template_string)

        output_parser, format_instructions = self._get_output_parser_and_format_instructions()

        translation = prompt_template.format_messages(
            german_word=word,
            word_type=wordtype,
            level=level,
            format_instructions=format_instructions,
        )

        response = chat(translation)
        output_dict = output_parser.parse(response.content)
        return output_dict

    def _get_api_responses_for_dataframe(self, df: pd.DataFrame, col_name: str) -> List:
        """
        Iterates over a DataFrame containing German words and their CEFR levels, calls the
        _get_api_response() method for each row, and returns a list of dictionaries of sentences and their translations.

        :param df: a pandas DataFrame containing German words and their CEFR levels
        :param col_name: a string representing the name of the column containing the German words in the DataFrame

        :return:
        A list of dictionaries containing lists of German sentences, English translations, and other information.
        """
        results = []
        for index, row in df.iterrows():
            word = row[col_name]
            wordtype = row['word_type']
            level = row['level']
            output_dict = self._get_api_response(word=word, wordtype=wordtype, level=level)
            print(output_dict)
            results.append(output_dict)
        return results

    @staticmethod
    def _create_dataframe_from_list_of_dict(list_of_dicts: List) -> pd.DataFrame:
        """
        Flattens a list of dictionaries containing lists of German sentences,
        English translations, and other information into a pandas DataFrame.

        :param list_of_dicts: a list of dictionaries containing lists of German sentences, English translations,
        and other information.

        :return:
        A flattened pandas DataFrame containing German sentences, English translations, and other information.
        """
        flat_data = []
        for item in list_of_dicts:
            num_entries = len(item["german_word"])
            for i in range(num_entries):
                flat_data.append({
                    "german_word": item["german_word"][i],
                    "english_word": item["english_word"][i],
                    "german_sentence": item["german_sentence"][i],
                    "english_sentence": item["english_sentence"][i]
                })
        df = pd.DataFrame(flat_data)
        return df

    @staticmethod
    def _upload_df(df_path: str) -> pd.DataFrame:
        """
        Reads a CSV file containing German words and their CEFR levels, and returns a pandas DataFrame.

        :param df_path: a string representing the path to the CSV file containing the German words and their CEFR levels

        :return:
        A pandas DataFrame containing German words and their CEFR levels.
        """
        df = pd.read_csv(df_path, delimiter=',', encoding='utf-16')
        df[['level', 'word_type']] = df['level_type'].str.split('_', expand=True)
        return df

    def get_chunks(self, word_type: str, df_path: str):
        """
        A public method that reads a CSV file containing German words and their CEFR levels, filters them by CEFR level
        and word type, and stores them in the chunks attribute of the SentenceGenerator instance.

        :param word_type: a string representing the type of German words to filter by (e.g. noun, verb, adjective)
        :param df_path: a string representing the path to the CSV file containing the German words and their CEFR levels
        """
        df = self._upload_df(df_path=df_path)
        filter_through = [f'a1_{word_type}', f'a2_{word_type}', f'b1_{word_type}', f'b2_{word_type}', f'c1_{word_type}']
        for filtering in filter_through:
            df_subset = df[df['level_type'] == filtering]
            self.chunks[filtering] = df_subset

    def get_df_level(self, level_word_type: str) -> pd.DataFrame:
        """
        A public method that returns a pandas DataFrame containing German words and their CEFR levels
        for a given CEFR level and word type.

        :param level_word_type

        :return: A pandas DataFrame containing German words and their CEFR levels.
        """
        return self.chunks[level_word_type]

    def process_data(self, df: pd.DataFrame, col_name: str) -> pd.DataFrame:
        """
        Generate sentences and their translations for a DataFrame of word chunks, and returns the flattened DataFrame.

        :param df: a pandas DataFrame containing German words and their CEFR levels
        :param col_name: a string representing the name of the column containing the German words in the DataFrame

        :return: A flattened pandas DataFrame containing German sentences, English translations, and other information.
        """
        list_of_dicts = sentence_generator._get_api_responses_for_dataframe(df=df, col_name=col_name)
        result_df = self._create_dataframe_from_list_of_dict(list_of_dicts=list_of_dicts)
        return result_df

##


sentence_generator = SentenceGenerator()
word_types = ['verb', 'noun', 'adjective', 'adverb', 'number']

for word_ in word_types:
    level_wordtype = 'a1_' + word_
    sentence_generator.get_chunks(word_type=word_, df_path=f'{path_vocabulary}/{word_}.csv')
    data = sentence_generator.get_df_level(level_word_type=level_wordtype)
    res_df = sentence_generator.process_data(df=data, col_name=word_)
    res_df.to_excel(f'{path_project}/{level_wordtype}.xlsx', index=False)
