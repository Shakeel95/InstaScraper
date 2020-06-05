import pandas as pd

from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.by import By

import os
import getpass
import time
import re


class insta_scraper:
    """
    Data collection class for Lorenzo's thesis...
    Usage: login to insta, collect target_accout meta-data, for specified posts on target_accout collect data on user
    interactions and data on the users themselves.
    =====

    Functions:
        - start_driver: starts webdriver and performs login
        - quit_driver: quits webdriver; use when done
        - set_follower_list: sets follower list for target account; list must be collected externally.
        - target_accout: collects target account meta-data
        - scrape_post_data: scrapes posts for target account
    """

    def __init__(self,):

        self.driver = None
        self.insta_url = "https://www.instagram.com"

        self.target_metadata = dict(post=None, followers=None, following=None)
        self.target_handle = None
        self.target_url = None
        self.target_follower_list = None
        self.posts_scraped = []

        self.df = None
        self.dff = None
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

        self.driver.get(self.insta_ulr)

        WebDriverWait(self.driver, 5).until(
            ec.presence_of_element_located((By.NAME, "username"))
        ).send_keys(uname)
        self.driver.find_element_by_name("password").send_keys(
            getpass.getpass("Password: ")
        )
        self.driver.find_element_by_xpath("//*[contains(text(), 'Log In')]").click()

    def quit_driver(self,):
        """
        Quits webdriver. Use when done.
        """

        self.driver.quit()

    def set_follower_list(self, path):
        """
        Sets follower list for target account; must be collected externally.
        -----
        Args:
            - path: path to follower list file.
            - col_index:
            - header:
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

        self.driver.get(os.path.join(self.insta_ulr, account))

        self.target_handle = account
        self.target_url = self.driver.current_url

        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        banner = soup.find_all(class_="g47SY")

        self.target_metadatap["post"] = banner[0].text.replace(",", "")
        self.target_metadatap["followers"] = banner[1].text.replace(",", "")
        self.target_metadatap["following"] = banner[2].text.replace(",", "")

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
        self.driver.get(os.path.join(self.insta_ulr, post.find(href=True)["href"][1:]))

        # set up data collection
        self.dff = pd.DataFrame(
            columns=df_colnames
            + [
                "likes_post_{}".format(post_index),
                "comments_post_{}".format(post_index),
            ]
        )

        # find users commenting
        soup = BeautifulSoup(self.driver.page_source, "html.parser")
        users = soup.find("ul", {"class": "Mr508"})

        for user in users:

            handle = user.find(href=True)["href"].strip("/")
            self.dff.loc[handle] = [0 for i in range(len(self.dff.columns))]
            self.dff["comments_post_{}".format(post_index)][handle] = user.find(
                "div", {"class": "C4VMK"}
            ).text.strip(handle)

            if handle in self.target_follower_list:
                self_df["follows_target"][handle] = 1

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

        while len(self.dff) < min(max_likes, int(likes)):

            scroll_bar = WebDriverWait(self.driver, 5).until(
                ec.presence_of_element_located(
                    (By.XPATH, "//div[@style='height: 356px; overflow: hidden auto;']")
                )
            )

            soup = BeautifulSoup(self.driver.page_source, "html.parser")
            users = soup.find_all("div", {"aria-labelledby": re.compile(r".*")})

            for user in users:
                handle = user.find("a")["href"].strip("/")

                if (self.dff.index == handle).any():
                    self.df["likes_post_1"][handle] = 1

                else:
                    self.dff.loc[handle] = [0 for i in range(len(self_df.columns))]
                    self.dff["likes_post_1"][handle] = 1
                    if handle in self.target_follower_list:
                        self.dff["follows_target"][handle] = 1

            old_len = new_len
            new_len = len(self_df)
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
