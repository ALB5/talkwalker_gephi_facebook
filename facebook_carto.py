#! /usr/bin/env python3
# coding: utf-8

import os
import pickle as pkl
import pandas as pd
import facebook
import requests

class Dataframe:
    """Get file, create dataframe and return a list of ids
    Initializes a list of ids"""
    #quels peuvent-être les attributs de ma class ? une list d'ids? a dataframe ?
    pd.set_option("display.max_rows", 16)
    LARGE_FIGSIZE = (12, 8)

    def __init__(self, data):
        #On pourrait imaginer que les données du dataframe puissent être segmentées autrement
        self.dataframe = pd.read_excel(data)
        self.dic_list_ids = []

    def create_newdf(self):
        """get the excel file and return a dataframe with only few columns.
        Then, we only keep lines where tags don't contain "isComment" """
        list_posts = self.dataframe
        list_posts.columns = [name.replace(".", "_") for name in list_posts.columns]
        df_list_posts = pd.DataFrame({"url": list_posts['url'],
                                      "tags": list_posts['tags_internal'],
                                      "content": list_posts['content'],
                                      "auteur":list_posts['extra_source_attributes_name']})
        regex_comments = r".+isComment.+|isComment|isComment.+|.+isComment"
        df_list_posts = df_list_posts.drop(df_list_posts[df_list_posts['tags'].str.contains(regex_comments)].index)
        return df_list_posts

    def get_id_post(self):
        """From the dataframe return all the ids of each post"""
        regex_id = r"id=(\d+)"
        df_list_posts = self.create_newdf()
        list_ids = df_list_posts['url'].str.findall(regex_id)
        list_ids = list_ids.str.join("_")
        #Maybe it is possible to create a dictionary without the dataframe
        df_list_ids = pd.DataFrame({"list_ids": list_ids,
                                    "auteur": df_list_posts['auteur']})
        self.dic_list_ids = df_list_ids.to_dict(orient='records')

class Facebook:

    """Get a token via Facebook Graph Explorer
        Améliorer en ajouter la case commentaire
    """
    TOKEN = 'EAACEdEose0cBAJpeiZAcvZC3ILvkVOANgpPARqRSn2E81sKTRs4Q3c2mH1R7UcYOZAVlE9mbHMgh1rwh1iUCj7w9UQSrjiFK9GunZCcmzsLYiwpaeEnq6fyaJ3ZAhDnxN3zwjOYcmXRQrAitaPxqVs8sL8xgj1ZCYLcgjrwtfcwj3SZCaUBAg9dvqrbzX543UUZD'

    def __init__(self):
        self.graph = facebook.GraphAPI(access_token=self.TOKEN, version='2.7')
        self.engagement_data = []
        self.connection_name = ''
        self.path_to_file = os.path.join("data", 'likes_list.pkl')

    def select_connection_name(self):
        connection_name = input("Choose a connection_name (likes or comments) : ")
        if connection_name == 'likes' or connection_name == 'comments':
            self.connection_name = connection_name
        else:
            print("Wrong input")
            return self.select_connection_name()

    def get_engagement(self, list_ids):
        """For each post id, get all web users's ids who likes the post"""
        for status in list_ids:
            try:
                #Ajouter la possibilité de récupérer soit les likes soit les commentaires
                likes = self.graph.get_connections(id=status['list_ids'],
                                                   connection_name=self.connection_name,
                                                   limit='1000')
                try:
                    while likes['data']:
                        self.engagement_data.append({"id_status":status['list_ids'],
                                                     "likes":likes['data'],
                                                     "nomPage": status['auteur']})
                        if 'next' in likes['paging'].keys():
                            likes = requests.get(likes['paging']['next']).json()
                        else:
                            break
                except KeyError:
                    break
            except facebook.GraphAPIError as e:
                print(e)
                continue

    def save_likes_list(self, likes_list):
        with open(self.path_to_file, 'wb') as f:
            pkl.dump(likes_list, f)

    def get_likes_list(self, path_to_file):
        with open(path_to_file, 'rb') as f:
            likes_list = pkl.load(f)
        return likes_list

class Graph:
    """xxx"""
    def __init__(self):
        self.nodes = []
        self.links = []

    @classmethod
    def get_all_likes(cls, likes_list):
        likes = []
        for like in likes_list:
            try:
                for idlike in like['likes']:
                    likes.append({'id_status': like['id_status'],
                                  'idlike':idlike['id'],
                                  'nomLike':idlike['name'],
                                  'nomPage':like['nomPage']})
            except KeyError as e:
                print(e)
                continue

        likes = pd.DataFrame(likes)
        return likes

class Nodes(Graph):
    """xxx"""
    def __init__(self):
        super().__init__()
        self.nodes = []

    def get_name_likers(self, likes_list):
        all_likes = self.get_all_likes(likes_list)
        name_likers = pd.DataFrame({"Id": all_likes['nomLike']})
        return name_likers

    @classmethod
    def get_name_pages(self, likes_list):
        df_page_names = pd.DataFrame(likes_list)
        df_page_names = pd.DataFrame({"Id": df_page_names['nomPage']})
        return df_page_names

    def concat_pages_likers(self, likes_list):
        list_ids = pd.concat([self.get_name_pages(likes_list),
                              self.get_name_likers(likes_list)])
        list_ids = list_ids.drop_duplicates(keep=False)
        list_ids = list_ids.reset_index(drop=True)
        list_ids['Label'] = list_ids['Id']
        self.nodes = list_ids

class Links(Graph):
    def __init__(self):
        super().__init__()
        self.links = []

    def create_links(self, likes_list):
        all_likes = self.get_all_likes(likes_list)
        all_likes = all_likes.rename(index=str, columns={"nomPage": "Target",
                                                         "nomLike": "Source"})
        self.links = all_likes


def main():
    facebook_cls = Facebook()
    facebook_cls.select_connection_name()
    try:
        list_likes_file = facebook_cls.path_to_file
        list_likes = facebook_cls.get_likes_list(list_likes_file)
    except FileNotFoundError:
        data = os.path.join("data", "sample.xlsx")
        dataframe = Dataframe(data)
        dataframe.get_id_post()
        list_ids = dataframe.dic_list_ids
        facebook_cls.get_engagement(list_ids)
        list_likes = facebook_cls.engagement_data
        facebook_cls.save_likes_list(list_likes)

    nodes = Nodes()
    nodes.concat_pages_likers(list_likes)
    nodes.nodes.to_csv("nodes.csv")
    links = Links()
    links.create_links(list_likes)
    links.links.to_csv("liens.csv")

if __name__ == '__main__':
    main()
