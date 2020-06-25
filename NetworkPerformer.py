from weiboSpider import Weibo
import json


class Node:
    def __init__(self, wbid: str, nickname: str, fans:int=0):
        self.wbid = wbid      # uuid string of weibo id
        self.nickname = nickname
        self.follows = []     # follows node
        self.fans = []        # fans node
        self.fans_num = fans  # fans number

    def init_neighbors(self, follows: list, fans: list):
        self.follows = follows
        self.fans = fans
        if not self.fans_num and len(self.fans):
            self.fans_num = len(self.fans)

    def isloaded(self):
        return self.wbid and self.nickname and self.follows and self.fans


class NetworkPerformer:

    def __init__(self, center_node: Node=None, path: str=None):
        self.centroid = center_node
        self.dic = {}       # dic to store all nodes:   uuid -> Node
        self.weibo_filepath = path

    def center(self, uuid, nickname):
        """ center a node with given uuid """
        self.centroid = self.load_node(uuid, nickname)
        self.centroid.fans_num *= 10
        return self.centroid

    def load_node_from_json(self, json_str: str):
        """ load a node into context from given json string """
        nodes = json.loads(json_str)
        for i in range(len(nodes)):
            # substitute existed Node object for json dic
            if nodes[i]['id'] in self.dic:
                nodes[i] = self.dic[nodes[i]['id']]
            else:   # add a new Node object
                uuid = nodes[i]['id']
                nickname = nodes[i]['nickname']
                num = nodes[i]['fans']
                nodes[i] = self.dic[uuid] = Node(uuid, nickname, num)
        return nodes

    def load_node(self, uuid, nickname):
        """ load a node into context from given uuid and unique nickname """
        if uuid in self.dic and self.dic[uuid].isloaded():        # check exist first
            return self.dic[uuid]
        else:                       # load from local json file
            follows_path = self.weibo_filepath + "%s\%s_following.json" % (nickname, uuid)
            fans_path = self.weibo_filepath + "%s\%s_follower.json" % (nickname, uuid)
            with open(follows_path) as follow_file, open(fans_path) as fan_file:
                # load nodes from json
                follows_json = (follow_file.read())
                follows_node = self.load_node_from_json(follows_json)
                fans_json = (fan_file.read())
                fans_node = self.load_node_from_json(fans_json)
                # init node
                node = Node(uuid, nickname)
                node.init_neighbors(follows_node, fans_node)
                # load node to storage
                self.dic[uuid] = node
                return node

    @staticmethod
    def cluster_purifier(dic: dict, cluster_size: int=0, filter_rate: float=1.0):
        """ reduce cluster size by random sampling """
        from collections import defaultdict
        from random import random
        # init threshold
        if cluster_size == 0:
            filter_rate = 0
        clusters = defaultdict(list)
        for e in dic['links']:
            s, t, w = e['source'], e['target'], e['value']
            clusters[s].append(t)
            clusters[t].append(s)
        # randomly sampling
        for k in tuple(clusters.keys()):
            if len(clusters[k]) == 1:
                if random() > filter_rate:
                    clusters.pop(k)
        # reconstruct dict
        dic['nodes'] = list(filter(lambda x: x['id'] in clusters, dic['nodes']))
        dic['links'] = list(filter(lambda x: x['source'] in clusters and x['target'] in clusters, dic['links']))
        return dic



# if __name__ == '__main__':
#     np = NetworkPerformer(path="C:\\Users\\kakay\\PycharmProjects\\Weibo-Network-Visualizer\\weibo");
#     np.load_node("6015415191", "小路斯吖")

