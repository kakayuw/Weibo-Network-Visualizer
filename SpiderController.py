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

    def run_spider(self):
        """ run spider as configured in cfg file """
        name, wbid = self.wb.get_usermeta()
        if not self.check_follow_file_exists(wbid, name):
            self.wb.start()
        self.name2id[name] = wbid
        self.id2name[wbid] = name
        return wbid

    def run_spider_layer2(self):
        # TODO: LAYER2
        """ run spider as configured in cfg file exploring 1 degree"""
        name, wbid = self.wb.get_usermeta()
        if not self.check_follow_file_exists(wbid, name):
            self.wb.start()
        self.name2id[name] = wbid
        self.id2name[wbid] = name
        return wbid


    def check_follow_file_exists(self, uuid, name):
        """ check whether given filepath is a file """
        if "follow" in self.wb.crawl_mode and \
            os.path.isfile(self.json_path + '\\%s\\%s_following.json' % (name, uuid)) \
                and os.path.isfile(self.json_path + '\\%s\\%s_follower.json'% (name, uuid)):
                return True
        return False

    def format_layer1_json(self, uuid: str):
        """ get first layer cluster json configuration from context """
        nickname = self.id2name[uuid]
        centroid = self.graph.center(uuid, nickname)       # load and centering
        nodes, edges = [self.dicfy_node(centroid)], []
        intersection = set(centroid.follows) & set(centroid.fans)
        follow_set = set(centroid.follows) - intersection
        for n in set(centroid.follows + centroid.fans):         # form node dict
            seq = 1 if n in follow_set else 2 if n in intersection else 3
            if self.filter_user(n):
                nodes.append(self.dicfy_node(n, seq))
        for n in centroid.follows:                         # form edge dict
            seq = 1 if n in follow_set else 2 if n in intersection else 3
            if self.filter_user(n):
                edges.append(self.dicfy_edge(centroid, n, seq))
        for n in centroid.fans:
            seq = 1 if n in follow_set else 2 if n in intersection else 3
            if self.filter_user(n):
                edges.append(self.dicfy_edge(centroid, n, seq))
        return {"nodes": nodes, "links": edges}            # form json string

    @staticmethod
    def filter_user(n: Node):
        if n.fans_num == 0 or 10 < n.fans_num < 500:
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

if __name__ == '__main__':
    sc = SpiderController("C:\\Users\\kakay\\PycharmProjects\\Weibo-Network-Visualizer\\weibo")
    print(sc.check_follow_file_exists("6015415191", "小路斯吖"))









