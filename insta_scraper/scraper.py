import pandas as pd
import numpy as np

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By

import nltk

from tqdm import tqdm

import os
import getpass
import time
import re
import datetime


class insta_scraper:
    """
    Data collection class for Lorenzo's thesis...
    Usage: login to insta, collect target_accout meta-data, for specified posts on target_accout collect data on user
    interactions and data on the users themselves.
    =====

    Functions:
        - start_driver: starts webdriver and performs login
        - quit_driver: quits webdriver; use when done
        - string2float: turns strings to floats
        - TagDateRatio: calculates posts per day
        - set_follower_list: sets follower list for target account; list must be collected externally.
        - target_accout: collects target account meta-data
        - scrape_post_data: scrapes posts for target account
    """

    def __init__(self,):

        self.driver = None
        self.insta_url = "https://www.instagram.com"
        self.uname = None
        self.pwd = None

        self.target_metadata = dict(post=None, followers=None, following=None)
        self.target_handle = None
        self.target_url = None
        self.target_follower_list = None
        self.posts_scraped = []

        self.index_marker = 1

        self.df = None
        self.df_colnames = [
            "follows_target",
            "n_followers",
            "n_following",
            "n_posts",
            "posts_over_time",
            "bio",
            "post_1_content",
            "post_2_content",
            "post_3_content",
        ]

    def start_driver(self, path_to_driver, headless=False, incognito=False):
        """
        Starts webdriver and performs login.
        -----
        Args:
            - path_to_driver: e.g. from deom notebook use '../webdriver/win/chromedriver'
            - headless: bool, if True webdriver is headless
            - incognito: bool, if True browser is run incognito
        """

        if not os.path.exists(path_to_driver):
            raise Warning(f"{path_to_driver} is not a valid path!")

        options = webdriver.ChromeOptions()
        options.add_argument("--ignore-certificate-errors")
        if incognito:
            options.add_argument("--incognito")
        if headless:
            options.add_argument("--headless")

        self.driver = webdriver.Chrome(path_to_driver, options=options)

        self.driver.get(self.insta_url)

        self.uname = input("insta username: ")
        WebDriverWait(self.driver, 5).until(
            ec.presence_of_element_located((By.NAME, "username"))
        ).send_keys(self.uname)
        self.pwd = getpass.getpass("insta password: ")
        self.driver.find_element_by_name("password").send_keys(self.pwd)
        self.driver.find_element_by_xpath("//*[contains(text(), 'Log In')]").click()

    def quit_driver(self,):
        """
        Quits webdriver. Use when done.
        """

        self.driver.quit()

    def string2float(self, string):
        """
        Turns floats to strings as shown by instagram...
        -----
        Args:
            - string: a string
        """

        if "m" in string:
            return 1000000 * float(string.strip("m"))
        elif "k" in string:
            return 1000 * float(string.strip("k"))
        else:
            try:
                f = float(string)
                return f
            except:
                return np.Inf

    def TagDateRatio(self, tags, epsilon=0.1):
        """
        Calculates posts per day.
        -----
        Args:
            - tags: list of post tags foud with b42 ('div',{'class':'KL4Bh'})
            - epsilon: added stability, stops you dividing by zero!
        """
        if len(tags) == 0:
            return np.NaN

        if len(tags) == 1:
            return 1

        dates = []
        for tag in tags:
            try:
                dates += [
                    parser.parse(
                        re.search("on (.*)\. ", tag.find("img")["alt"]).group(1)
                    )
                ]
            except:
                pass

        if len(dates) == 0:
            return 1
        else:
            return len(dates) / ((dates[0] - dates[-1]).days + epsilon)

    def set_follower_list(self, path, header, col_index):
        """
        Sets follower list for target account; must be collected externally.
        -----
        Args:
            - path: path to follower list file.
            - col_index: column index in which necessary data is stored
            - header: whether the csv contains a header
        """

        self.target_follower_list = pd.read_csv(path, header=header)[
            col_index
        ].to_list()

    def target_accout(self, account):
        """
        Navigates to account and collects accoutn metadata
        -----
        Args:
            - account: string, inta handle
        """

        self.driver.get(os.path.join(self.insta_url, account))

        self.target_handle = account
        self.target_url = self.driver.current_url

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        banner = soup.find_all(class_="g47SY")

        self.target_metadata["post"] = banner[0].text.replace(",", "")
        self.target_metadata["followers"] = banner[1].text.replace(",", "")
        self.target_metadata["following"] = banner[2].text.replace(",", "")

        self.df = self.df = pd.DataFrame(columns=self.df_colnames)

    def scrape_post_data(self, post_index, max_likes=300, scroll_pause=0.5, max_runs=7):
        """
        Collect handles of of suers who have interacted with post.
        -----
        Args:
            - post_index: which post to scraper, if unsure check metadata
            - max_likes: to guarantee max set to float('inf')
            - scroll_pause: time to sleep between scrolling
            - max_runs: maximum attempted scrolls with no change in users collected
        """

        if self.target_handle == None or self.target_url == None:
            raise Warning("No user handle, run 'target_accout' to set metadata")

        if self.target_follower_list == None:
            raise Warning("No follower list found, run 'set_follower_list'")

        if not ("instagram" and self.target_handle in self.driver.current_url):
            print("Taking you to {} first ...".format(self.target_handle))
            self.driver.get(self.target_url)

        if post_index in self.posts_scraped:
            return "Data for post {} already collected".format(post_index)

        # navigate to indexed post
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        post = soup.find_all("div", class_="v1Nh3 kIKUG _bz0w")[post_index - 1]
        self.driver.get(os.path.join(self.insta_url, post.find(href=True)["href"][1:]))
        time.sleep(1)

        # mark post scraper
        self.posts_scraped += [post_index]
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        if "views" in soup.find("section", {"class": "EDfFK ygqzn"}).text:
            return "post {} is a video, likes canot be scraper".format(post_index)

        # set up data collection
        self.df["likes_post_{}".format(post_index)] = np.NaN
        self.df["comments_post_{}".format(post_index)] = np.NaN

        # find users commenting
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        users = soup.find_all("ul", {"class": "Mr508"})

        for user in users:
            handle = user.find(href=True)["href"].strip("/")

            if (self.df.index == handle).any():
                self.df.loc[handle, "comments_post_{}".format(post_index)] = (
                    user.find("div", {"class": "C4VMK"}).text.strip(handle).strip("#")
                )
            else:
                self.df.loc[handle] = np.NaN
                self.df.loc[handle, "comments_post_{}".format(post_index)] = (
                    user.find("div", {"class": "C4VMK"}).text.strip(handle).strip("#")
                )

            if handle in self.target_follower_list:
                self.df.loc[handle, "follows_target"] = 1

        # find users liking
        likes = self.driver.find_element_by_class_name("Nm9Fw").text.strip(" likes")
        WebDriverWait(self.driver, 5).until(
            ec.presence_of_element_located(
                (By.XPATH, "//button[@class='sqdOP yWX7d     _8A5w5    ']")
            )
        ).click()

        runs = []
        old_len = 0
        new_len = 0
        i = 0

        while len(self.df) < min(max_likes, int(likes)):

            scroll_bar = WebDriverWait(self.driver, 5).until(
                ec.presence_of_element_located(
                    (By.XPATH, "//div[@style='height: 356px; overflow: hidden auto;']")
                )
            )

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            users = soup.find_all("div", {"aria-labelledby": re.compile(r".*")})

            for user in users:
                handle = user.find("a")["href"].strip("/")

                if (self.df.index == handle).any():
                    self.df.loc[handle, "likes_post_{}".format(post_index)] = 1

                else:
                    self.df.loc[handle] = np.NaN
                    self.df.loc[handle, "likes_post_{}".format(post_index)] = 1
                    if handle in self.target_follower_list:
                        self.df.loc[handle, "follows_target"] = 1

            old_len = new_len
            new_len = len(self.df)
            if old_len == new_len:
                runs += [1]
            else:
                runs += [0]
            if sum(runs[-4:]) > max_runs:
                break

            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollTop + arguments[0].offsetHeight;",
                scroll_bar,
            )

            if (i % 7) == 0:
                self.driver.execute_script("arguments[0].scrollTop -= 400;", scroll_bar)
            i += 1
            time.sleep(scroll_pause)

    def scrape_user_data(self, frac_lambda=1):
        """
        Scrapes data from accounts accounts collected by last function.
        ---
        Args:
            - frac_lambda: param in exponential distribution for waits; bigger = longer
        """

        for handle in tqdm(self.df.index.to_list()):

            self.driver.get(os.path.join(self.insta_url, handle))
            time.sleep(np.random.exponential(frac_lambda))
            self.index_marker += 1

            # followers, following, posts
            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            banner = soup.find_all(class_="g47SY")
            self.df.loc[handle, "n_followers"] = self.string2float(
                banner[1].text.replace(",", "")
            )
            self.df.loc[handle, "n_following"] = self.string2float(
                banner[2].text.replace(",", "")
            )
            self.df.loc[handle, "n_posts"] = self.string2float(
                banner[0].text.replace(",", "")
            )

            # bio
            try:
                self.df.loc[handle, "bio"] = (
                    soup.find("div", {"class": "-vDIg"}).find("span").text
                ).strip("#")
            except:
                self.df.loc[handle, "bio"] = np.NaN

            # posts over time
            posts = soup.find_all("div", {"class": "KL4Bh"})
            self.df.loc[handle, "posts_over_time"] = self.TagDateRatio(posts)

            # post content
            if soup.find("div", {"class": "Nnq7C weEfm"}) == None:
                continue
            else:
                links = soup.find("div", {"class": "Nnq7C weEfm"}).find_all(href=True)

            i = 1
            for link in links[0:3]:
                try:
                    url = link["href"]
                    self.driver.get(os.path.join(self.insta_url, url[1:]))
                    self.df.loc[handle, "post_{}_content".format(i)] = (
                        WebDriverWait(self.driver, 5)
                        .until(
                            ec.presence_of_element_located(
                                (By.XPATH, "//div[@class='C7I1f X7jCj']")
                            )
                        )
                        .text.strip("#")
                    )
                    i += 1
                    time.sleep(np.random.exponential(frac_lambda))
                except:
                    i += 1
                    self.df.loc[handle, "post_{}_content".format(i)] = os.path.join(
                        self.insta_url, url[1:]
                    )
                    continue

        def pick_up_from_interuption(self,frac_lambda=1):
            """
            If you scrape too quickly insa throws you out!
            Use this function to pick up from where you left off.
            -----
            Args: 
                - frac_lambda: param in exponential distribution for waits; bigger = longer
            """

            for handle in tqdm(self.df.index[self.index_marker :]):

                self.driver.get(os.path.join(self.insta_url, handle))
                time.sleep(np.random.exponential(frac_lambda))
                self.index_marker += 1

                # followers, following, posts
                soup = BeautifulSoup(self.driver.page_source, "html.parser")
                banner = soup.find_all(class_="g47SY")
                self.df.loc[handle, "n_followers"] = self.string2float(
                    banner[1].text.replace(",", "")
                )
                self.df.loc[handle, "n_following"] = self.string2float(
                    banner[2].text.replace(",", "")
                )
                self.df.loc[handle, "n_posts"] = self.string2float(
                    banner[0].text.replace(",", "")
                )

                # bio
                try:
                    self.df.loc[handle, "bio"] = (
                        soup.find("div", {"class": "-vDIg"}).find("span").text
                    ).strip("#")
                except:
                    self.df.loc[handle, "bio"] = np.NaN

                # posts over time
                posts = soup.find_all("div", {"class": "KL4Bh"})
                self.df.loc[handle, "posts_over_time"] = self.TagDateRatio(posts)

                # post content
                if soup.find("div", {"class": "Nnq7C weEfm"}) == None:
                    continue
                else:
                    links = soup.find("div", {"class": "Nnq7C weEfm"}).find_all(
                        href=True
                    )

                i = 1
                for link in links[0:3]:
                    try:
                        url = link["href"]
                        self.driver.get(os.path.join(self.insta_url, url[1:]))
                        self.df.loc[handle, "post_{}_content".format(i)] = (
                            WebDriverWait(self.driver, 5)
                            .until(
                                ec.presence_of_element_located(
                                    (By.XPATH, "//div[@class='C7I1f X7jCj']")
                                )
                            )
                            .text.strip("#")
                        )
                        i += 1
                        time.sleep(np.random.exponential(frac_lambda))
                    except:
                        i += 1
                        self.df.loc[handle, "post_{}_content".format(i)] = os.path.join(
                            self.insta_url, url[1:]
                        )
                        continue

    def word_occurence_analysis(self, path_to_data):
        """
        Counts occurence of positive, and negative words in tokenized posts.
        Counts occurence of Maslow pyramid of needs words.
        -----
        Args:
            - path_to_data: path to folder containing sentiment analysis and Maslow words (e.g. from demo notebook use '../data')
        """

        # open Maslow words
        with open(os.path.join(path_to_data, "self_actualisation.txt")) as f:
            self_actualisation = f.readlines()[0].split(" ")
        with open(os.path.join(path_to_data, "esteem.txt")) as f:
            esteem = f.readlines()[0].split(" ")
        with open(os.path.join(path_to_data, "love.txt")) as f:
            love = f.readlines()[0].split(" ")
        with open(os.path.join(path_to_data, "psychology.txt")) as f:
            psychology = f.readlines()[0].split(" ")
        with open(os.path.join(path_to_data, "safety.txt")) as f:
            safety = f.readlines()[0].split(" ")

        # open sentiment analysis
        sentiment_words = pd.read_csv(
            os.path.join(path_to_data, "sentiment_words.csv"), encoding="ISO-8859-1"
        )
        positive_words = sentiment_words["POSITIVE"].to_list()
        negative_words = sentiment_words["NEGATIVE"].to_list()

        # make additional columns
        self.df["self_actualisation"] = np.NaN
        self.df["esteem"] = np.NaN
        self.df["love"] = np.NaN
        self.df["psychology"] = np.NaN
        self.df["safety"] = np.NaN

        self.df["positive_words"] = np.NaN
        self.df["negative_words"] = np.NaN

        for handle in tqdm(self.df.index.to_list()):

            handle_str = "".join(str(s) for s in self.df.loc[handle].to_list())
            tokens = nltk.word_tokenize(handle_str)

            act_maker = 0
            for token in tokens:
                if token in self_actualisation:
                    act_maker += 1
            self.df.loc[handle, "self_actualisation"] = act_maker

            esteem_marker = 0
            for token in tokens:
                if token in esteem:
                    esteem_marker += 1
            self.df.loc[handle, "esteem"] = esteem_marker

            love_marker = 0
            for token in tokens:
                if token in esteem:
                    love_marker += 1
            self.df.loc[handle, "love"] = love_marker

            psych_marker = 0
            for token in tokens:
                if token in psychology:
                    psych_marker += 1
            self.df.loc[handle, "psychology"] = psych_marker

            safe_marker = 0
            for token in tokens:
                if token in safety:
                    safe_marker += 1
            self.df.loc[handle, "safety"] = safe_marker

            pos_counter = 0
            for token in tokens:
                if token in positive_words:
                    pos_counter += 1
            self.df.loc[handle, "positive_words"] = pos_counter

            neg_counter = 0
            for token in tokens:
                if token in negative_words:
                    neg_counter += 1
            self.df.loc[handle, "negative_words"] = neg_counter
