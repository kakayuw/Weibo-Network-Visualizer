import os
import sys
import json
import traceback

from NetworkPerformer import NetworkPerformer, Node
from weiboSpider import Weibo


class SpiderController:

    def __init__(self, path: str=None):
        # init two dictionary for bidirectional index
        self.name2id = {}
        self.id2name = {}
        self.wb = None
        self.json_path = path
        self.graph = NetworkPerformer(path=path)
        try:
            config_path = os.path.split(
                os.path.realpath(__file__))[0] + os.sep + 'config.json'
            if not os.path.isfile(config_path):
                sys.exit(u'当前路径：%s 不存在配置文件config.json' %
                         (os.path.split(os.path.realpath(__file__))[0] + os.sep))
            with open(config_path) as f:
                config = json.loads(f.read())
            self.wb = Weibo(config)
        except ValueError:
            print('Wrong config json format.')
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def update_dic(self, uuid, name):
        self.name2id[name] = uuid
        self.id2name[uuid] = name

    def run_spider(self):
        """ run spider as configured in cfg file """
        name, wbid = self.wb.get_usermeta()
        if not self.check_follow_file_exists(wbid, name):
            self.wb.start()
        self.name2id[name] = wbid
        self.id2name[wbid] = name
        return wbid

    def format_layer1_json(self, uuid: str):
        """ get first layer cluster json configuration from context """
        nickname = self.id2name[uuid]
        centroid = self.graph.center(uuid, nickname)       # load and centering
        nodes, edges = [self.dicfy_node(centroid)], []
        intersection = set(centroid.follows) & set(centroid.fans)
        follow_set = set(centroid.follows) - intersection
        for n in set(centroid.follows + centroid.fans):         # form node dict
            seq = 1 if n in follow_set else 2 if n in intersection else 3
            if self.valid_user(n.fans_num):
                nodes.append(self.dicfy_node(n, seq))
        for n in centroid.follows:                         # form edge dict
            seq = 1 if n in follow_set else 2 if n in intersection else 3
            if self.valid_user(n.fans_num):
                edges.append(self.dicfy_edge(centroid, n, seq))
        for n in centroid.fans:
            seq = 1 if n in follow_set else 2 if n in intersection else 3
            if self.valid_user(n.fans_num):
                edges.append(self.dicfy_edge(centroid, n, seq))
        return {"nodes": nodes, "links": edges}            # form json string

    def format_layer2_json(self, uuid: int):
        """ run spider as configured in cfg file exploring 1 degree"""
        # get degree 0 and degree 1
        self.wb.seed_user(uuid)
        name, wbid = self.wb.get_usermeta()
        self.update_dic(wbid, name)
        if not self.check_follow_file_exists(wbid, name):
            self.wb.start()
        miserables = [self.format_layer1_json(wbid)]
        neighbors = self.get_layer1_list(wbid, name)
        # crawl degree 2
        for k, v in neighbors.items():
            if not self.check_follow_file_exists(k, v):
                self.wb.seed_user(k)
                self.wb.start()
            self.update_dic(k, neighbors[k])
            miserable = self.format_layer1_json(k)
            miserables.append(miserable)
        miserables = self.dic_join(miserables)
        miserables = self.graph.cluster_purifier(miserables)
        return miserables

    def get_layer1_list(self, uuid, nickname):
        """ load 1 degree neighbor id """
        layer1 = dict()
        follows_path = self.json_path + "\\%s\\%s_following.json" % (nickname, uuid)
        fans_path = self.json_path + "\\%s\\%s_follower.json" % (nickname, uuid)
        with open(follows_path) as follow_file, open(fans_path) as fan_file:
            # load nodes from json
            follows_json = follow_file.read()
            follows_dic_list = json.loads(follows_json)
            fans_json = (fan_file.read())
            fans_dic_list = json.loads(fans_json)
            # update dict
            layer1.update({dic['id']: dic['nickname'] for dic in follows_dic_list if dic['id'].isdigit() and self.valid_user(dic['fans'])})
            layer1.update({dic['id']: dic['nickname'] for dic in fans_dic_list if dic['id'].isdigit() and self.valid_user(dic['fans'])})
        return layer1

    def check_follow_file_exists(self, uuid, name):
        """ check whether given filepath is a file """
        if "follow" in self.wb.crawl_mode and \
            os.path.isfile(self.json_path + '\\%s\\%s_following.json' % (name, uuid)) \
                and os.path.isfile(self.json_path + '\\%s\\%s_follower.json'% (name, uuid)):
                return True
        return False

    # static methods
    @staticmethod
    def valid_user(num: int):
        if num == 0 or 20 < num < 550:
            return True
        else:
            return False

    @staticmethod
    def dicfy_node(node: Node, layer:int = 0):
        n = dict()
        n['id'] = node.wbid
        n['group'] = layer
        return n

    @staticmethod
    def dicfy_edge(node: Node, moon: Node, layer:int = 0):
        e = dict()
        e['source'] = node.wbid
        e['target'] = moon.wbid
        e['value'] = layer
        return e

    @staticmethod
    def dic_join(dic_list: list):
        nodedic, edgedic = set(), set()
        nodes, links = list(), list()
        for dic in dic_list:
            for node in dic['nodes']:
                if node['id'] not in nodedic:
                    nodedic.add(node['id'])
                    nodes.append(node)
            for link in dic['links']:
                a, b, w = link['source'], link['target'], link['value']
                if (b, a) in edgedic and w != 2:    link['value'] = 2
                if (a, b) not in edgedic:
                    edgedic.add((a, b))
                    links.append(link)
        return {"nodes": nodes, "links": links}


if __name__ == '__main__':
    sc = SpiderController("C:\\Users\\kakay\\PycharmProjects\\Weibo-Network-Visualizer\\weibo")
    print(sc.check_follow_file_exists("6015415191", "小路斯吖"))









