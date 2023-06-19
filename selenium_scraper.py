##
from typing import Dict, List
import pandas as pd
from selenium import webdriver
import time
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from pathlib import Path
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from config import page_url, my_email, my_password, csv_file_path


class ScrapeWords:
    """
    A class to scrape German, Spanish and French words from a website, based on word types and difficulty levels.
    """

    CHROMEDRIVER_PATH = Path('chromedriver.exe')
    EMAIL_XPATH = '//*[@id="new_user"]/div[3]/input'
    PASSWORD_XPATH = '//*[@id="new_user"]/div[4]/input'
    LOG_IN_BUTTON_XPATH = '//*[@id="new_user"]/button'
    VOCAB_BUTTON_XPATH = '//*[@id="root"]/div/div[1]/header/div/div[2]/div[1]/a[2]/div/div[2]'
    NEXT_BUTTON_XPATH = '/html/body/div/div/div[2]/div/div[3]/div/div/div[1]/div/div[4]/div/div[2]/div[21]/div[2]'
    DEFAULT_XPATH = '//*[@id="root"]/div/div[2]/div/div[2]/div[1]'

    levels = ['a1', 'a2', 'b1', 'b2', 'c1']
    word_types = ['adjective', 'adverb', 'noun', 'number', 'verb']

    def __init__(self):
        self.driver = None

    def navigate_to_main_page(self, url: str, email: str, password: str) -> None:
        """
        Navigates to the main page of the website.

        :param url: The url of the main page.
        :param email: Email to be used for logging in.
        :param password: Password to be used for logging in.
        """
        driver = webdriver.Chrome(executable_path=str(self.CHROMEDRIVER_PATH))
        driver.maximize_window()
        driver.get(url)
        email_path = driver.find_element(By.XPATH, self.EMAIL_XPATH)
        password_path = driver.find_element(By.XPATH, self.PASSWORD_XPATH)
        email_path.send_keys(email)
        password_path.send_keys(password)
        wait = WebDriverWait(driver, 10)
        self._click_button(wait=wait, find_by=By.XPATH, path=self.LOG_IN_BUTTON_XPATH)  # log in button
        self._click_button(wait=wait, find_by=By.XPATH, path=self.VOCAB_BUTTON_XPATH)  # vocab button
        self.driver = driver

    def _scrape_vocab_by_type_and_level(self) -> List[str]:
        """
        Scrape vocabulary by type and level.

        :return: A list of words.
        """
        wait = WebDriverWait(self.driver, 10)
        list_of_words = []
        while True:
            try:
                time.sleep(5)
                texts = self.driver.find_elements(By.CLASS_NAME, 'text.css-1x8qkb1')
                for i in range(len(texts)):
                    list_of_words.append(texts[i].text)
                current_url = self.driver.current_url
                try:
                    self._click_button(wait=wait, find_by=By.XPATH, path=self.NEXT_BUTTON_XPATH)  # next button
                    wait.until(ec.url_changes(current_url))
                except TimeoutException:
                    break
            except (NoSuchElementException, ElementNotInteractableException, IndexError):
                break
        return list_of_words

    def _hover_mouse_somewhere_and_click(self, find_by: By, path: str = None) -> None:
        """
        Hover the mouse over an element on the webpage and click it.

        :param find_by: The type of selector to be used for finding the element.
        :param path: The path of the element. Default is None.
        """
        if not path:
            path = self.DEFAULT_XPATH
        element = self.driver.find_element(find_by, path)
        action = ActionChains(self.driver).move_to_element(element)
        action.perform()
        element.click()

    @staticmethod
    def _click_button(wait: WebDriverWait, find_by: By, path: str) -> None:
        """
        Click a button on the webpage.

        :param wait: The WebDriverWait object.
        :param find_by: The type of selector to be used for finding the button.
        :param path: The path of the button.
        """
        button = wait.until(ec.element_to_be_clickable((find_by, path)))
        button.click()

    def _scroll_down(self, pixels: int) -> None:
        """
        Scroll down a webpage by a certain number of pixels.

        :param pixels: The number of pixels to scroll down.
        """
        element = self.driver.find_element(By.CLASS_NAME, 'css-i2r08k')
        self.driver.execute_script(f"arguments[0].scrollTop += {pixels}", element)

    def _perform_scraping_within_levels(self, word_type) -> Dict[str, str]:
        """
        Perform the scraping within levels.

        :param word_type: The type of word.
        :return: A dictionary containing the words.
        """
        wait = WebDriverWait(self.driver, 10)
        words_dict = {}

        for j, lvl in zip(range(2, 7), self.levels):
            if j >= 3:
                time.sleep(3)
                self._hover_mouse_somewhere_and_click(find_by=By.XPATH)
                self._click_button(wait=wait, find_by=By.CLASS_NAME, path='css-1kao6un')  # unclick previous
                time.sleep(3)
                self._hover_mouse_somewhere_and_click(find_by=By.CLASS_NAME, path='css-45ydyn')  # menu

            time.sleep(3)
            base_xpath_levels = f'//*[@id="root"]/div/div[2]/div/div[3]/div/div/div[1]/div/div[2]/div/div[1]/' \
                                f'div[2]/div[2]/div/div[1]/div[2]/div[1]/div[2]/div[{j}]/div[2]'
            time.sleep(3)
            self._hover_mouse_somewhere_and_click(find_by=By.XPATH, path=base_xpath_levels)  # click on level
            self._click_button(wait=wait, find_by=By.CLASS_NAME, path='css-1vb9g26')  # close menu button

            try:
                list_words = self._scrape_vocab_by_type_and_level()
            except (NoSuchElementException, ElementNotInteractableException, IndexError):
                continue

            value_name = [lvl + '_' + word_type]
            dictionary = {word: value_name[0] for word in list_words}
            words_dict.update(dictionary)
        return words_dict

    def _unclick_previous(self) -> None:
        """
        Unclick a previously clicked element.
        """
        wait = WebDriverWait(self.driver, 10)
        self._click_button(wait=wait, find_by=By.CLASS_NAME, path='css-1kao6un')
        self._click_button(wait=wait, find_by=By.CLASS_NAME, path='css-1kao6un')

    def _perform_scraping_word_types(self, word_type: str, path_number: int) -> Dict[str, str]:
        """
        Perform the scraping for different types of words.

        :param word_type: The type of word.
        :param path_number: The number of the path.
        :return: A dictionary containing the words.
        """
        wait = WebDriverWait(self.driver, 10)
        self._hover_mouse_somewhere_and_click(find_by=By.XPATH)
        self._click_button(wait=wait, find_by=By.CLASS_NAME, path='css-45ydyn')  # menu
        time.sleep(4)
        self._scroll_down(pixels=150)
        time.sleep(4)
        base_xpath_word_types = f'//*[@id="root"]/div/div[2]/div/div[3]/div/div/div[1]/div/div[2]/div/div[1]/' \
                                f'div[2]/div[2]/div/div[1]/div[2]/div[2]/div[2]/div[{path_number}]/div[2]'
        self._hover_mouse_somewhere_and_click(find_by=By.XPATH, path=base_xpath_word_types)  # click on word types
        words_dict = self._perform_scraping_within_levels(word_type=word_type)
        return words_dict

    def perform_scraping(self) -> List[Dict[str, str]]:
        """
        Perform the scraping operation.

        :return: A list of dictionaries containing the words.
        """
        list_of_dictionaries = []
        for i, word in zip(range(2, 7), self.word_types):
            if i >= 3:
                self._hover_mouse_somewhere_and_click(find_by=By.XPATH)
                self._unclick_previous()
            my_dict = self._perform_scraping_word_types(word_type=word, path_number=i)
            list_of_dictionaries.append(my_dict)
        return list_of_dictionaries

    def get_dataframe(self) -> pd.DataFrame:
        """
        Create a DataFrame from the scraped data.

        :return: A DataFrame containing the words.
        """
        my_dict = self.perform_scraping()
        my_df = pd.DataFrame(my_dict).T.reset_index()
        return my_df

    @staticmethod
    def get_csv(df: pd.DataFrame, csv_path: str) -> None:
        """
        Create a DataFrame from the scraped data.

        :return: A DataFrame containing the words.
        """
        df.to_csv(csv_path, index=False, encoding='utf-16')


perform_scraping = ScrapeWords()
perform_scraping.navigate_to_main_page(url=page_url, email=my_email, password=my_password)

##
driver_ = perform_scraping.driver
output_df = perform_scraping.get_dataframe()
perform_scraping.get_csv(output_df, csv_file_path)
