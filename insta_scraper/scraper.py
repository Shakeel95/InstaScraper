import pandas as pd
import numpy as np

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By

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

    def start_driver(self, path_to_driver, headless=False):
        """
        Starts webdriver and performs login.
        -----
        Args:
            - path_to_driver: e.g. from deom notebook use '../webdriver/win/chromedriver'
            - headless: bool, if True webdriver is headless
        """

        if not os.path.exists(path_to_driver):
            raise Warning(f"{path_to_driver} is not a valid path!")

        options = webdriver.ChromeOptions()
        options.add_argument("--ignore-certificate-errors")
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
        Jesus turned water into wine. This function turns trings into floats.
        Your move Jesus.
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

    def scrape_post_data(self, post_index, max_likes=300, scroll_pause=0.5):
        """
        What it does ....
        -----
        Args:
            - post_index: which post to scraper, if unsure check metadata
            - max_likes: to guarantee max set to float('inf')
            - scroll_pause: time to sleep between scrolling
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

        # SET VIDEO CONDITION!

        self.posts_scraped += [post_index]

        # set up data collection
        self.df["likes_post_{}".format(post_index)] = 0
        self.df["comments_post_{}".format(post_index)] = 0

        # find users commenting
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        users = soup.find_all("ul", {"class": "Mr508"})

        for user in users:
            handle = user.find(href=True)["href"].strip("/")

            if (self.df.index == handle).any():
                self.df.loc[handle, "comments_post_{}".format(post_index)] = user.find(
                    "div", {"class": "C4VMK"}
                ).text.strip(handle)
            else:
                self.df.loc[handle] = 0
                self.df.loc[handle, "comments_post_{}".format(post_index)] = user.find(
                    "div", {"class": "C4VMK"}
                ).text.strip(handle)

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
                    self.df.loc[handle] = 0
                    self.df.loc[handle, "likes_post_{}".format(post_index)] = 1
                    if handle in self.target_follower_list:
                        self.df.loc[handle, "follows_target"] = 1

            old_len = new_len
            new_len = len(self.df)
            if old_len == new_len:
                runs += [1]
            else:
                runs += [0]
            if sum(runs[-4:]) > 3:
                break

            self.driver.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollTop + arguments[0].offsetHeight;",
                scroll_bar,
            )

            if (i % 7) == 0:
                self.driver.execute_script("arguments[0].scrollTop -= 400;", scroll_bar)
            i += 1
            time.sleep(scroll_pause)

    def scrape_user_data(self,):
        """
        What it does...
        ---
        Args:
        """

        for handle in tqdm(self.df.index.to_list()):

            self.driver.get(os.path.join(self.insta_url, handle))
            time.sleep(np.random.exponential(1, 1))

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
                )
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
                        .text
                    )
                    i += 1
                    time.sleep(np.random.exponential(1, 1))
                except:
                    i += 1
                    self.df.loc[handle, "post_{}_content".format(i)] = os.path.join(
                        self.insta_url, url[1:]
                    )
                    continue

    def process_data_categorically(self,):
        """
        What it does...
        ---
        Args:
        """

    def process_data_PCA(slef,):
        """
        What it does...
        ---
        Args:
        """

    def visualise_data(self,):
        """
        What it does:
        ---
        Args:
        """
