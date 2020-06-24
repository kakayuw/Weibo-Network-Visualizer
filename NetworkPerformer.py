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
        self.fans_num = len(self.fans)


class NetworkPerformer:

    def __init__(self, center_node: Node=None, path: str=None):
        self.centroid = center_node
        self.dic = {}       # dic to store all nodes:   uuid -> Node
        self.weibo_filepath = path

    def center(self, uuid, nickname):
        """ center a node with given uuid """
        self.centroid = self.load_node(uuid, nickname)
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
        if uuid in self.dic:        # check exist first
            return self.dic[uuid]
        else:                       # load from local json file
            follows_path = self.weibo_filepath + "/%s/%s_following.json" % (nickname, uuid)
            fans_path = self.weibo_filepath + "/%s/%s_follower.json" % (nickname, uuid)
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

# if __name__ == '__main__':
#     np = NetworkPerformer(path="C:\\Users\\kakay\\PycharmProjects\\Weibo-Network-Visualizer\\weibo");
#     np.load_node("6015415191", "小路斯吖")

