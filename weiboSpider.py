#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import codecs
import copy
import csv
import json
import os
import random
import re
import sys
import traceback
from collections import OrderedDict
from datetime import date, datetime, timedelta
from time import sleep

import requests
from lxml import etree
from requests.adapters import HTTPAdapter
from tqdm import tqdm


class Weibo(object):
    def __init__(self, config):
        """Weibo类初始化"""
        self.validate_config(config)
        self.filter = config[
            'filter']  # 取值范围为0、1,程序默认值为0,代表要爬取用户的全部微博,1代表只爬取用户的原创微博
        since_date = str(config['since_date'])
        if since_date.isdigit():
            since_date = str(date.today() - timedelta(int(since_date)))
        self.since_date = since_date  # 起始时间，即爬取发布日期从该值到现在的微博，形式为yyyy-mm-dd
        self.write_mode = config[
            'write_mode']  # 结果信息保存类型，为list形式，可包含txt、csv、mongo和mysql四种类型
        self.crawl_mode = config[
            'crawl_mode'    # 'follow': crawl follower and followings; 'weibo': crawl weibo data
        ]
        self.pic_download = config[
            'pic_download']  # 取值范围为0、1,程序默认值为0,代表不下载微博原始图片,1代表下载
        self.video_download = config[
            'video_download']  # 取值范围为0、1,程序默认为0,代表不下载微博视频,1代表下载
        self.cookie = {'Cookie': config['cookie']}
        self.mysql_config = config.get('mysql_config')  # MySQL数据库连接配置，可以不填
        user_id_list = config['user_id_list']
        if not isinstance(user_id_list, list):
            if not os.path.isabs(user_id_list):
                user_id_list = os.path.split(
                    os.path.realpath(__file__))[0] + os.sep + user_id_list
            user_id_list = self.get_user_list(user_id_list)
        self.user_id_list = user_id_list  # 要爬取的微博用户的user_id列表
        self.user_id = ''  # 用户id,如昵称为"Dear-迪丽热巴"的id为'1669879400'
        self.user = {}  # 存储爬取到的用户信息
        self.got_num = 0  # 存储爬取到的微博数
        self.weibo = []  # 存储爬取到的所有微博信息
        self.weibo_id_list = []  # 存储爬取到的所有微博id
        self.following_list = [] # store all following user's id and nickname
        self.follower_list = []           # store all fans id and nickname


    def validate_config(self, config):
        """验证配置是否正确"""

        # 验证filter、pic_download、video_download
        argument_lsit = ['filter', 'pic_download', 'video_download']
        for argument in argument_lsit:
            if config[argument] != 0 and config[argument] != 1:
                sys.exit(u'%s值应为0或1,请重新输入' % config[argument])

        # 验证since_date
        since_date = str(config['since_date'])
        if (not self.is_date(since_date)) and (not since_date.isdigit()):
            sys.exit(u'since_date值应为yyyy-mm-dd形式或整数,请重新输入')

        # 验证write_mode
        write_mode = ['txt', 'csv', 'mongo', 'mysql']
        if not isinstance(config['write_mode'], list):
            sys.exit(u'write_mode值应为list类型')
        for mode in config['write_mode']:
            if mode not in write_mode:
                sys.exit(u'%s为无效模式，请从txt、csv、mongo和mysql中挑选一个或多个作为write_mode' %
                         mode)

        # 验证user_id_list
        user_id_list = config['user_id_list']
        if (not isinstance(user_id_list,
                           list)) and (not user_id_list.endswith('.txt')):
            sys.exit(u'user_id_list值应为list类型或txt文件路径')
        if not isinstance(user_id_list, list):
            if not os.path.isabs(user_id_list):
                user_id_list = os.path.split(
                    os.path.realpath(__file__))[0] + os.sep + user_id_list
            if not os.path.isfile(user_id_list):
                sys.exit(u'不存在%s文件' % user_id_list)

    def is_date(self, since_date):
        """判断日期格式是否正确"""
        try:
            datetime.strptime(since_date, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def handle_html(self, url):
        """处理html"""
        try:
            html = requests.get(url, cookies=self.cookie).content
            selector = etree.HTML(html)
            return selector
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def handle_garbled(self, info):
        """处理乱码"""
        try:
            info = (info.xpath('string(.)').replace(u'\u200b', '').encode(
                sys.stdout.encoding, 'ignore').decode(sys.stdout.encoding))
            return info
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_nickname(self):
        """获取用户昵称"""
        try:
            url = 'https://weibo.cn/%s/info' % (self.user_id)
            selector = self.handle_html(url)
            nickname = selector.xpath('//title/text()')[0]
            nickname = nickname[:-3]
            if nickname == u'登录 - 新' or nickname == u'新浪':
                self.write_log()
                sys.exit(u'cookie错误或已过期,请按照README中方法重新获取')
            self.user['nickname'] = nickname
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def user_to_mongodb(self):
        """将爬取的用户信息写入MongoDB数据库"""
        user_list = [self.user]
        self.info_to_mongodb('user', user_list)
        print(u'%s信息写入MongoDB数据库完毕' % self.user['nickname'])

    def user_to_mysql(self):
        """将爬取的用户信息写入MySQL数据库"""
        # 创建'weibo'数据库
        create_database = """CREATE DATABASE IF NOT EXISTS weibo DEFAULT
                         CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"""
        self.mysql_create_database(create_database)
        # 创建'user'表
        create_user_table = """
            CREATE TABLE IF NOT EXISTS user (
            id varchar(12) NOT NULL,
            nickname varchar(30),
            weibo_num INT,
            following INT,
            followers INT,
            PRIMARY KEY (id),
            INDEX `user_idx` (`id` ASC)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
        # Create 'follow' table
        create_follow_table = """
            CREATE TABLE IF NOT EXISTS follow (
            fid varchar(12) NOT NULL,
            tid varchar(12),
            nickname varchar(40),
            url varchar(100),
            fans INT,
            PRIMARY KEY (fid, tid)       
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
        self.mysql_create_table(self.mysql_config, create_user_table)
        self.mysql_create_table(self.mysql_config, create_follow_table)
        self.mysql_insert(self.mysql_config, 'user', [self.user])
        print(u'%s信息写入MySQL数据库完毕' % self.user['nickname'])

    def user_to_database(self):
        """将用户信息写入数据库"""
        if 'mysql' in self.write_mode:
            self.user_to_mysql()
        if 'mongo' in self.write_mode:
            self.user_to_mongodb()

    def print_user_info(self):
        """打印微博用户信息"""
        print(u'用户昵称: %s' % self.user['nickname'])
        print(u'用户id: %s' % self.user['id'])
        print(u'微博数: %d' % self.user['weibo_num'])
        print(u'关注数: %d' % self.user['following'])
        print(u'粉丝数: %d' % self.user['followers'])

    def get_user_info(self, selector):
        """获取用户昵称、微博数、关注数、粉丝数"""
        try:
            self.get_nickname()  # 获取用户昵称
            user_info = selector.xpath("//div[@class='tip2']/*/text()")
            weibo_num = int(user_info[0][3:-1])
            following = int(user_info[1][3:-1])
            followers = int(user_info[2][3:-1])
            self.user['weibo_num'] = weibo_num
            self.user['following'] = following
            self.user['followers'] = followers
            self.user['id'] = self.user_id
            self.print_user_info()
            self.user_to_database()
            print('*' * 100)
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_page_num(self, selector):
        """获取微博总页数"""
        try:
            if selector.xpath("//input[@name='mp']") == []:
                page_num = 1
            else:
                page_num = int(
                    selector.xpath("//input[@name='mp']")[0].attrib['value'])
            return page_num
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_long_weibo(self, weibo_link):
        """获取长原创微博"""
        try:
            selector = self.handle_html(weibo_link)
            info = selector.xpath("//div[@class='c']")[1]
            wb_content = self.handle_garbled(info)
            wb_time = info.xpath("//span[@class='ct']/text()")[0]
            weibo_content = wb_content[wb_content.find(':') +
                                       1:wb_content.rfind(wb_time)]
            return weibo_content
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()
            return u'网络出错'

    def get_original_weibo(self, info, weibo_id):
        """获取原创微博"""
        try:
            weibo_content = self.handle_garbled(info)
            weibo_content = weibo_content[:weibo_content.rfind(u'赞')]
            a_text = info.xpath('div//a/text()')
            if u'全文' in a_text:
                weibo_link = 'https://weibo.cn/comment/' + weibo_id
                wb_content = self.get_long_weibo(weibo_link)
                if wb_content:
                    weibo_content = wb_content
            return weibo_content
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_long_retweet(self, weibo_link):
        """获取长转发微博"""
        try:
            wb_content = self.get_long_weibo(weibo_link)
            weibo_content = wb_content[:wb_content.rfind(u'原文转发')]
            return weibo_content
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_retweet(self, info, weibo_id):
        """获取转发微博"""
        try:
            wb_content = self.handle_garbled(info)
            wb_content = wb_content[wb_content.find(':') +
                                    1:wb_content.rfind(u'赞')]
            wb_content = wb_content[:wb_content.rfind(u'赞')]
            a_text = info.xpath('div//a/text()')
            if u'全文' in a_text:
                weibo_link = 'https://weibo.cn/comment/' + weibo_id
                weibo_content = self.get_long_retweet(weibo_link)
                if weibo_content:
                    wb_content = weibo_content
            retweet_reason = self.handle_garbled(info.xpath('div')[-1])
            retweet_reason = retweet_reason[:retweet_reason.rindex(u'赞')]
            original_user = info.xpath("div/span[@class='cmt']/a/text()")
            if original_user:
                original_user = original_user[0]
                wb_content = (retweet_reason + '\n' + u'原始用户: ' +
                              original_user + '\n' + u'转发内容: ' + wb_content)
            else:
                wb_content = retweet_reason + '\n' + u'转发内容: ' + wb_content
            return wb_content
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def is_original(self, info):
        """判断微博是否为原创微博"""
        is_original = info.xpath("div/span[@class='cmt']")
        if len(is_original) > 3:
            return False
        else:
            return True

    def get_weibo_content(self, info, is_original):
        """获取微博内容"""
        try:
            weibo_id = info.xpath('@id')[0][2:]
            if is_original:
                weibo_content = self.get_original_weibo(info, weibo_id)
            else:
                weibo_content = self.get_retweet(info, weibo_id)
            return weibo_content
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_publish_place(self, info):
        """获取微博发布位置"""
        try:
            div_first = info.xpath('div')[0]
            a_list = div_first.xpath('a')
            publish_place = u'无'
            for a in a_list:
                if ('place.weibo.com' in a.xpath('@href')[0]
                        and a.xpath('text()')[0] == u'显示地图'):
                    weibo_a = div_first.xpath("span[@class='ctt']/a")
                    if len(weibo_a) >= 1:
                        publish_place = weibo_a[-1]
                        if (u'视频' == div_first.xpath(
                                "span[@class='ctt']/a/text()")[-1][-2:]):
                            if len(weibo_a) >= 2:
                                publish_place = weibo_a[-2]
                            else:
                                publish_place = u'无'
                        publish_place = self.handle_garbled(publish_place)
                        break
            return publish_place
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_publish_time(self, info):
        """获取微博发布时间"""
        try:
            str_time = info.xpath("div/span[@class='ct']")
            str_time = self.handle_garbled(str_time[0])
            publish_time = str_time.split(u'来自')[0]
            if u'刚刚' in publish_time:
                publish_time = datetime.now().strftime('%Y-%m-%d %H:%M')
            elif u'分钟' in publish_time:
                minute = publish_time[:publish_time.find(u'分钟')]
                minute = timedelta(minutes=int(minute))
                publish_time = (datetime.now() -
                                minute).strftime('%Y-%m-%d %H:%M')
            elif u'今天' in publish_time:
                today = datetime.now().strftime('%Y-%m-%d')
                time = publish_time[3:]
                publish_time = today + ' ' + time
                if len(publish_time) > 16:
                    publish_time = publish_time[:16]
            elif u'月' in publish_time:
                year = datetime.now().strftime('%Y')
                month = publish_time[0:2]
                day = publish_time[3:5]
                time = publish_time[7:12]
                publish_time = year + '-' + month + '-' + day + ' ' + time
            else:
                publish_time = publish_time[:16]
            return publish_time
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_publish_tool(self, info):
        """获取微博发布工具"""
        try:
            str_time = info.xpath("div/span[@class='ct']")
            str_time = self.handle_garbled(str_time[0])
            if len(str_time.split(u'来自')) > 1:
                publish_tool = str_time.split(u'来自')[1]
            else:
                publish_tool = u'无'
            return publish_tool
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_weibo_footer(self, info):
        """获取微博点赞数、转发数、评论数"""
        try:
            footer = {}
            pattern = r'\d+'
            str_footer = info.xpath('div')[-1]
            str_footer = self.handle_garbled(str_footer)
            str_footer = str_footer[str_footer.rfind(u'赞'):]
            weibo_footer = re.findall(pattern, str_footer, re.M)

            up_num = int(weibo_footer[0])
            footer['up_num'] = up_num

            retweet_num = int(weibo_footer[1])
            footer['retweet_num'] = retweet_num

            comment_num = int(weibo_footer[2])
            footer['comment_num'] = comment_num
            return footer
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def extract_picture_urls(self, info, weibo_id):
        """提取微博原始图片url"""
        try:
            a_list = info.xpath('div/a/@href')
            first_pic = 'https://weibo.cn/mblog/pic/' + weibo_id + '?rl=0'
            all_pic = 'https://weibo.cn/mblog/picAll/' + weibo_id + '?rl=1'
            if first_pic in a_list:
                if all_pic in a_list:
                    selector = self.handle_html(all_pic)
                    preview_picture_list = selector.xpath('//img/@src')
                    picture_list = [
                        p.replace('/thumb180/', '/large/')
                        for p in preview_picture_list
                    ]
                    picture_urls = ','.join(picture_list)
                else:
                    if info.xpath('.//img/@src'):
                        preview_picture = info.xpath('.//img/@src')[-1]
                        picture_urls = preview_picture.replace(
                            '/wap180/', '/large/')
                    else:
                        sys.exit(
                            u"爬虫微博可能被设置成了'不显示图片'，请前往"
                            u"'https://weibo.cn/account/customize/pic'，修改为'显示'"
                        )
            else:
                picture_urls = u'无'
            return picture_urls
        except Exception as e:
            return u'无'
            print('Error: ', e)
            traceback.print_exc()

    def get_picture_urls(self, info, is_original):
        """获取微博原始图片url"""
        try:
            weibo_id = info.xpath('@id')[0][2:]
            picture_urls = {}
            if is_original:
                original_pictures = self.extract_picture_urls(info, weibo_id)
                picture_urls['original_pictures'] = original_pictures
                if not self.filter:
                    picture_urls['retweet_pictures'] = u'无'
            else:
                retweet_url = info.xpath("div/a[@class='cc']/@href")[0]
                retweet_id = retweet_url.split('/')[-1].split('?')[0]
                retweet_pictures = self.extract_picture_urls(info, retweet_id)
                picture_urls['retweet_pictures'] = retweet_pictures
                a_list = info.xpath('div[last()]/a/@href')
                original_picture = u'无'
                for a in a_list:
                    if a.endswith(('.gif', '.jpeg', '.jpg', '.png')):
                        original_picture = a
                        break
                picture_urls['original_pictures'] = original_picture
            return picture_urls
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_video_url(self, info, is_original):
        """获取微博视频url"""
        try:
            if is_original:
                div_first = info.xpath('div')[0]
                a_list = div_first.xpath('.//a')
                video_link = u'无'
                for a in a_list:
                    if 'm.weibo.cn/s/video/show?object_id=' in a.xpath(
                            '@href')[0]:
                        video_link = a.xpath('@href')[0]
                        break
                if video_link != u'无':
                    video_link = video_link.replace(
                        'm.weibo.cn/s/video/show', 'm.weibo.cn/s/video/object')
                    wb_info = requests.get(video_link,
                                           cookies=self.cookie).json()
                    video_url = wb_info['data']['object']['stream'].get(
                        'hd_url')
                    if not video_url:
                        video_url = wb_info['data']['object']['stream']['url']
                        if not video_url:  # 说明该视频为直播
                            video_url = u'无'
            else:
                video_url = u'无'
            return video_url
        except Exception as e:
            return u'无'
            print('Error: ', e)
            traceback.print_exc()

    def download_one_file(self, url, file_path, type, weibo_id):
        """下载单个文件(图片/视频)"""
        try:
            if not os.path.isfile(file_path):
                s = requests.Session()
                s.mount(url, HTTPAdapter(max_retries=5))
                downloaded = s.get(url, timeout=(5, 10))
                with open(file_path, 'wb') as f:
                    f.write(downloaded.content)
        except Exception as e:
            error_file = self.get_filepath(
                type) + os.sep + 'not_downloaded.txt'
            with open(error_file, 'ab') as f:
                url = weibo_id + ':' + url + '\n'
                f.write(url.encode(sys.stdout.encoding))
            print('Error: ', e)
            traceback.print_exc()

    def handle_download(self, file_type, file_dir, urls, w):
        """处理下载相关操作"""
        file_prefix = w['publish_time'][:11].replace('-', '') + '_' + w['id']
        if file_type == 'img':
            if ',' in urls:
                url_list = urls.split(',')
                for i, url in enumerate(url_list):
                    file_suffix = url[url.rfind('.'):]
                    file_name = file_prefix + '_' + str(i + 1) + file_suffix
                    file_path = file_dir + os.sep + file_name
                    self.download_one_file(url, file_path, file_type, w['id'])
            else:
                file_suffix = urls[urls.rfind('.'):]
                file_name = file_prefix + file_suffix
                file_path = file_dir + os.sep + file_name
                self.download_one_file(urls, file_path, file_type, w['id'])
        else:
            file_suffix = '.mp4'
            file_name = file_prefix + file_suffix
            file_path = file_dir + os.sep + file_name
            self.download_one_file(urls, file_path, file_type, w['id'])

    def download_files(self, file_type):
        """下载文件(图片/视频)"""
        try:
            if file_type == 'img':
                describe = u'图片'
                key = 'original_pictures'
            else:
                describe = u'视频'
                key = 'video_url'
            print(u'即将进行%s下载' % describe)
            file_dir = self.get_filepath(file_type)
            for w in tqdm(self.weibo, desc='Download progress'):
                if w[key] != u'无':
                    self.handle_download(file_type, file_dir, w[key], w)
            print(u'%s下载完毕,保存路径:' % describe)
            print(file_dir)
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_one_weibo(self, info):
        """获取一条微博的全部信息"""
        try:
            weibo = OrderedDict()
            is_original = self.is_original(info)
            if (not self.filter) or is_original:
                weibo['id'] = info.xpath('@id')[0][2:]
                weibo['content'] = self.get_weibo_content(info,
                                                          is_original)  # 微博内容
                picture_urls = self.get_picture_urls(info, is_original)
                weibo['original_pictures'] = picture_urls[
                    'original_pictures']  # 原创图片url
                if not self.filter:
                    weibo['retweet_pictures'] = picture_urls[
                        'retweet_pictures']  # 转发图片url
                    weibo['original'] = is_original  # 是否原创微博
                weibo['video_url'] = self.get_video_url(info,
                                                        is_original)  # 微博视频url
                weibo['publish_place'] = self.get_publish_place(info)  # 微博发布位置
                weibo['publish_time'] = self.get_publish_time(info)  # 微博发布时间
                weibo['publish_tool'] = self.get_publish_tool(info)  # 微博发布工具
                footer = self.get_weibo_footer(info)
                weibo['up_num'] = footer['up_num']  # 微博点赞数
                weibo['retweet_num'] = footer['retweet_num']  # 转发数
                weibo['comment_num'] = footer['comment_num']  # 评论数
            else:
                weibo = None
            return weibo
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def print_one_weibo(self, weibo):
        """打印一条微博"""
        print(weibo['content'])
        print(u'微博发布位置：%s' % weibo['publish_place'])
        print(u'发布发布时间：%s' % weibo['publish_time'])
        print(u'发布发布工具：%s' % weibo['publish_tool'])
        print(u'点赞数：%d' % weibo['up_num'])
        print(u'转发数：%d' % weibo['retweet_num'])
        print(u'评论数：%d' % weibo['comment_num'])

    def is_pinned_weibo(self, info):
        """判断微博是否为置顶微博"""
        kt = info.xpath(".//span[@class='kt']/text()")
        if kt and kt[0] == u'置顶':
            return True
        else:
            return False

    def get_he_follow_list(self):
        """get the follow list of the id"""
        he_follow_url = 'https://weibo.cn/%s/follow' % self.user_id
        selector = self.handle_html(he_follow_url)
        pagenum = self.get_page_num(selector)   # get he follow list page number
        followings = []
        for i in range(1, pagenum+1):
            he_follow_url = 'https://weibo.cn/%s/follow?page=%d' % (self.user_id, i)
            # print("crawl:", he_follow_url)
            selector = self.handle_html(he_follow_url)
            tables = selector.xpath('//table')
            for table in tables:
                following = table[0].xpath('td/a')[1]
                fans_numb_str = table[0].xpath('td/br')[0].tail
                followings.append(
                    {"id":following.attrib['href'].split('/')[-1],
                     "url": following.attrib['href'],
                     "nickname": following.text,
                     "fans": int(re.findall(r'\d+', fans_numb_str)[0])
                     })
            sleep(random.randint(5, 10) / 10)
        self.following_list = followings

    def get_follow_him_list(self):
        """get the follower list of the id"""
        fans_url = 'https://weibo.cn/%s/fans' % self.user_id
        selector = self.handle_html(fans_url)
        pagenum = self.get_page_num(selector)   # get he follow list page number
        fans = []
        for i in range(1, pagenum+1):
            fan_page_url = 'https://weibo.cn/%s/fans?page=%d' % (self.user_id, i)
            # print("crawl:", he_follow_url)
            selector = self.handle_html(fan_page_url)
            tables = selector.xpath('//table')
            for table in tables:
                following = table[0].xpath('td/a')[1]
                fans_numb_str = table[0].xpath('td/br')[0].tail
                fans.append(
                    {"id":following.attrib['href'].split('/')[-1],
                     "url": following.attrib['href'],
                     "nickname": following.text,
                     "fans": int(re.findall(r'\d+', fans_numb_str)[0])
                     })
            sleep(random.randint(5, 10) / 10)
        self.follower_list = fans

    def get_one_page(self, page):
        """获取第page页的全部微博"""
        try:
            url = 'https://weibo.cn/u/%s?page=%d' % (self.user_id, page)
            selector = self.handle_html(url)
            info = selector.xpath("//div[@class='c']")
            is_exist = info[0].xpath("div/span[@class='ctt']")
            if is_exist:
                for i in range(0, len(info) - 2):
                    weibo = self.get_one_weibo(info[i])
                    if weibo:
                        if weibo['id'] in self.weibo_id_list:
                            continue
                        publish_time = datetime.strptime(
                            weibo['publish_time'][:10], "%Y-%m-%d")
                        since_date = datetime.strptime(self.since_date,
                                                       "%Y-%m-%d")
                        if publish_time < since_date:
                            if self.is_pinned_weibo(info[i]):
                                continue
                            else:
                                return True
                        self.print_one_weibo(weibo)
                        self.weibo.append(weibo)
                        self.weibo_id_list.append(weibo['id'])
                        self.got_num += 1
                        print('-' * 100)
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_filepath(self, type, suffix=None):
        """获取结果文件路径"""
        try:
            file_dir = os.path.split(
                os.path.realpath(__file__)
            )[0] + os.sep + 'weibo' + os.sep + self.user['nickname']
            if type == 'img' or type == 'video':
                file_dir = file_dir + os.sep + type
            if not os.path.isdir(file_dir):
                os.makedirs(file_dir)
            if type == 'img' or type == 'video':
                return file_dir
            suf = suffix if suffix else ""
            file_path = file_dir + os.sep + self.user_id + suf + '.' + type
            return file_path
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def write_log(self):
        """当程序因cookie过期停止运行时，将相关信息写入log.txt"""
        file_dir = os.path.split(
            os.path.realpath(__file__))[0] + os.sep + 'weibo' + os.sep
        if not os.path.isdir(file_dir):
            os.makedirs(file_dir)
        file_path = file_dir + 'log.txt'
        content = u'cookie已过期，从%s到今天的微博获取失败，请重新设置cookie\n' % self.since_date
        with open(file_path, 'ab') as f:
            f.write(content.encode(sys.stdout.encoding))

    def write_csv(self, wrote_num):
        """将爬取的信息写入csv文件"""
        try:
            result_headers = [
                '微博id',
                '微博正文',
                '原始图片url',
                '微博视频url',
                '发布位置',
                '发布时间',
                '发布工具',
                '点赞数',
                '转发数',
                '评论数',
            ]
            if not self.filter:
                result_headers.insert(3, '被转发微博原始图片url')
                result_headers.insert(4, '是否为原创微博')
            result_data = [w.values() for w in self.weibo[wrote_num:]]
            with open(self.get_filepath('csv'),
                      'a',
                      encoding='utf-8-sig',
                      newline='') as f:
                writer = csv.writer(f)
                if wrote_num == 0:
                    writer.writerows([result_headers])
                writer.writerows(result_data)
            print(u'%d条微博写入csv文件完毕,保存路径:' % self.got_num)
            print(self.get_filepath('csv'))
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def write_txt(self, wrote_num):
        """将爬取的信息写入txt文件"""
        try:
            temp_result = []
            if wrote_num == 0:
                if self.filter:
                    result_header = u'\n\n原创微博内容: \n'
                else:
                    result_header = u'\n\n微博内容: \n'
                result_header = (u'用户信息\n用户昵称：' + self.user['nickname'] +
                                 u'\n用户id: ' + str(self.user_id) + u'\n微博数: ' +
                                 str(self.user['weibo_num']) + u'\n关注数: ' +
                                 str(self.user['following']) + u'\n粉丝数: ' +
                                 str(self.user['followers']) + result_header)
                temp_result.append(result_header)
            for i, w in enumerate(self.weibo[wrote_num:]):
                temp_result.append(
                    str(wrote_num + i + 1) + ':' + w['content'] + '\n' +
                    u'微博位置: ' + w['publish_place'] + '\n' + u'发布时间: ' +
                    w['publish_time'] + '\n' + u'点赞数: ' + str(w['up_num']) +
                    u'   转发数: ' + str(w['retweet_num']) + u'   评论数: ' +
                    str(w['comment_num']) + '\n' + u'发布工具: ' +
                    w['publish_tool'] + '\n\n')
            result = ''.join(temp_result)
            with open(self.get_filepath('txt'), 'ab') as f:
                f.write(result.encode(sys.stdout.encoding))
            print(u'%d条微博写入txt文件完毕,保存路径:' % self.got_num)
            print(self.get_filepath('txt'))
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def info_to_mongodb(self, collection, info_list):
        """将爬取的信息写入MongoDB数据库"""
        try:
            import pymongo
        except ImportError:
            sys.exit(u'系统中可能没有安装pymongo库，请先运行 pip install pymongo ，再运行程序')
        try:
            from pymongo import MongoClient
            client = MongoClient()
            db = client['weibo']
            collection = db[collection]
            if len(self.write_mode) > 1:
                new_info_list = copy.deepcopy(info_list)
            else:
                new_info_list = info_list
            for info in new_info_list:
                if not collection.find_one({'id': info['id']}):
                    collection.insert_one(info)
                else:
                    collection.update_one({'id': info['id']}, {'$set': info})
        except pymongo.errors.ServerSelectionTimeoutError:
            sys.exit(u'系统中可能没有安装或启动MongoDB数据库，请先根据系统环境安装或启动MongoDB，再运行程序')

    def weibo_to_mongodb(self, wrote_num):
        """将爬取的微博信息写入MongoDB数据库"""
        weibo_list = []
        for w in self.weibo[wrote_num:]:
            w['user_id'] = self.user_id
            weibo_list.append(w)
        self.info_to_mongodb('weibo', weibo_list)
        print(u'%d条微博写入MongoDB数据库完毕' % self.got_num)

    def mysql_create(self, connection, sql):
        """创建MySQL数据库或表"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
        finally:
            connection.close()

    def mysql_create_database(self, sql):
        """创建MySQL数据库"""
        try:
            import pymysql
        except ImportError:
            sys.exit(u'系统中可能没有安装pymysql库，请先运行 pip install pymysql ，再运行程序')
        try:
            connection = pymysql.connect(**self.mysql_config)
            self.mysql_create(connection, sql)
        except pymysql.OperationalError:
            sys.exit(u'系统中可能没有安装或正确配置MySQL数据库，请先根据系统环境安装或配置MySQL，再运行程序')

    def mysql_create_table(self, mysql_config, sql):
        """创建MySQL表"""
        import pymysql

        if self.mysql_config:
            mysql_config = self.mysql_config
        mysql_config['db'] = 'weibo'
        connection = pymysql.connect(**mysql_config)
        self.mysql_create(connection, sql)

    def mysql_insert(self, mysql_config, table, data_list):
        """向MySQL表插入或更新数据"""
        import pymysql

        if len(data_list) > 0:
            keys = ', '.join(data_list[0].keys())
            values = ', '.join(['%s'] * len(data_list[0]))
            if self.mysql_config:
                mysql_config = self.mysql_config
            mysql_config['db'] = 'weibo'
            connection = pymysql.connect(**mysql_config)
            cursor = connection.cursor()
            sql = """INSERT INTO {table}({keys}) VALUES ({values}) ON
                     DUPLICATE KEY UPDATE""".format(table=table,
                                                    keys=keys,
                                                    values=values)
            update = ','.join([
                " {key} = values({key})".format(key=key)
                for key in data_list[0]
            ])
            sql += update
            try:
                cursor.executemany(
                    sql, [tuple(data.values()) for data in data_list])
                connection.commit()
            except Exception as e:
                connection.rollback()
                print('Error: ', e)
                traceback.print_exc()
            finally:
                connection.close()

    def follow_to_mysql(self):
        """write following list to mysql"""
        for u in range(len(self.following_list)):
            self.following_list[u]['fid'] = self.user_id
            idlyst = re.findall(r'\d+', self.following_list[u]['url'])
            if idlyst:
                self.following_list[u]['tid'] = idlyst[0]
            else:
                o = self.following_list[u]['url']
                selector = self.handle_html(o)
                if selector is None:
                    self.following_list[u]['tid'] = 'null'
                    continue
                url, alist = '', selector.xpath("//div[@class='u']/*/a")
                if alist:
                    url = alist[0].attrib['href']
                else:
                    url = self.handle_html(o).xpath("//div[@class='u']/*/a")[0].attrib['href']
                idlyst = re.findall(r'\d+', url)[0]
                self.following_list[u]['tid'] = idlyst
        self.mysql_insert(self.mysql_config, 'follow', self.following_list)
        print(u'%d followings info loaded into MySQL!' % len(self.following_list))

    def weibo_to_mysql(self, wrote_num):
        """将爬取的微博信息写入MySQL数据库"""
        # 创建'weibo'表
        create_table = """
                CREATE TABLE IF NOT EXISTS weibo (
                id varchar(10) NOT NULL,
                user_id varchar(12),
                content varchar(2000),
                original_pictures varchar(1000),
                retweet_pictures varchar(1000),
                original BOOLEAN NOT NULL DEFAULT 1,
                video_url varchar(300),
                publish_place varchar(100),
                publish_time DATETIME NOT NULL,
                publish_tool varchar(30),
                up_num INT NOT NULL,
                retweet_num INT NOT NULL,
                comment_num INT NOT NULL,
                PRIMARY KEY (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
        self.mysql_create_table(self.mysql_config, create_table)
        # 在'weibo'表中插入或更新微博数据
        weibo_list = []
        if len(self.write_mode) > 1:
            info_list = copy.deepcopy(self.weibo[wrote_num:])
        else:
            info_list = self.weibo[wrote_num:]
        for weibo in info_list:
            weibo['user_id'] = self.user_id
            weibo_list.append(weibo)
        self.mysql_insert(self.mysql_config, 'weibo', weibo_list)
        print(u'%d条微博写入MySQL数据库完毕' % self.got_num)

    def write_data(self, wrote_num):
        """将爬取到的信息写入文件或数据库"""
        if self.got_num > wrote_num:
            if 'csv' in self.write_mode:
                self.write_csv(wrote_num)
            if 'txt' in self.write_mode:
                self.write_txt(wrote_num)
            if 'mysql' in self.write_mode:
                if self.crawl_mode == 'weibo':
                    self.weibo_to_mysql(wrote_num)
                elif self.crawl_mode == 'follow':
                    self.follow_to_mysql()
            if 'mongo' in self.write_mode:
                self.weibo_to_mongodb(wrote_num)

    def follow_list_to_json(self):
        """Convert Follower and Following list to json file"""
        import json
        if self.crawl_mode == 'follower' or self.crawl_mode == 'follow':
            follow_json = self.get_filepath('json', "_following")
            with open(follow_json, 'w+', encoding='utf-8', newline='\n') as f:
                content = json.dump(self.follower_list, f, indent=2, ensure_ascii=False)
            print(u'writing %d follower data to ' % len(self.follower_list) + follow_json)
        if self.crawl_mode == 'following' or self.crawl_mode == 'follow':
            fans_json = self.get_filepath('json', "_follower")
            with open(fans_json, 'w+', encoding='utf-8', newline='\n') as f:
                content = json.dump(self.following_list, f, indent=2, ensure_ascii=False)
            print(u'writing %d following data to ' % len(self.following_list) + fans_json)

    def get_weibo_info_follow(self):
        """get weibo info mainly about following and folloers"""
        try:
            profile_url = 'https://weibo.cn/u/%s' % self.user_id
            selector = self.handle_html(profile_url)
            self.get_user_info(selector)  # get nickname, weibo number, following number and fans number
            if self.crawl_mode == 'follow' or self.crawl_mode == 'following':
                self.get_he_follow_list()
            if self.crawl_mode == 'follow' or self.crawl_mode == 'following':
                self.get_follow_him_list()
            self.follow_list_to_json()
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()


    def get_weibo_info(self):
        """获取微博信息"""
        try:
            url = 'https://weibo.cn/u/%s' % (self.user_id)
            selector = self.handle_html(url)
            self.get_user_info(selector)  # 获取用户昵称、微博数、关注数、粉丝数
            page_num = self.get_page_num(selector)  # 获取微博总页数
            wrote_num = 0
            page1 = 0
            random_pages = random.randint(1, 5)
            for page in tqdm(range(1, page_num + 1), desc='Progress'):
                is_end = self.get_one_page(page)  # 获取第page页的全部微博
                if is_end:
                    break

                if page % 20 == 0:  # 每爬20页写入一次文件
                    self.write_data(wrote_num)
                    wrote_num = self.got_num

                # 通过加入随机等待避免被限制。爬虫速度过快容易被系统限制(一段时间后限
                # 制会自动解除)，加入随机等待模拟人的操作，可降低被系统限制的风险。默
                # 认是每爬取1到5页随机等待6到10秒，如果仍然被限，可适当增加sleep时间
                if page - page1 == random_pages and page < page_num:
                    sleep(random.randint(6, 10))
                    page1 = page
                    random_pages = random.randint(1, 5)

            self.write_data(wrote_num)  # 将剩余不足20页的微博写入文件
            if not self.filter:
                print(u'共爬取' + str(self.got_num) + u'条微博')
            else:
                print(u'共爬取' + str(self.got_num) + u'条原创微博')
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_user_list(self, file_name):
        """获取文件中的微博id信息"""
        with open(file_name, 'rb') as f:
            lines = f.read().splitlines()
            lines = [line.decode('utf-8') for line in lines]
            user_id_list = [
                line.split(' ')[0] for line in lines
                if len(line.split(' ')) > 0 and line.split(' ')[0].isdigit()
            ]
        return user_id_list

    def initialize_info(self, user_id):
        """初始化爬虫信息"""
        self.got_num = 0
        self.weibo = []
        self.user = {}
        self.user_id = user_id
        self.weibo_id_list = []

    def start(self):
        """运行爬虫"""
        try:
            for user_id in self.user_id_list:
                self.initialize_info(user_id)
                print('*' * 100)
                self.pic_download = self.video_download = 0     # default not download
                if self.crawl_mode == 'weibo':
                    self.get_weibo_info()
                    self.pic_download = self.video_download = 1
                elif self.crawl_mode == 'follow' or self.crawl_mode == 'following' or self.crawl_mode == 'follower':
                    self.get_weibo_info_follow()
                print(u'信息抓取完毕')
                print('*' * 100)
                if self.pic_download == 1:
                    self.download_files('img')
                if self.video_download == 1:
                    self.download_files('video')
        except Exception as e:
            print('Error: ', e)
            traceback.print_exc()

    def get_usermeta(self):
        """get name-id pair from crawled users"""
        if not self.user:
            try:
                self.user_id = self.user_id_list[0]
                self.get_nickname()
            except Exception as e:
                print('Error: ', e)
                traceback.print_exc()
        return self.user['nickname'], self.user_id

    def seed_user(self, uid):
        """ update seed user for crawl """
        self.user_id = uid
        self.user_id_list = [self.user_id]


def crawl_followings_to_mysql(userid=None):
    try:
        config_path = os.path.split(
            os.path.realpath(__file__))[0] + os.sep + 'config.json'
        if not os.path.isfile(config_path):
            sys.exit(u'当前路径：%s 不存在配置文件config.json' %
                     (os.path.split(os.path.realpath(__file__))[0] + os.sep))
        with open(config_path) as f:
            config = json.loads(f.read())
        wb = Weibo(config)
        if userid is not None:
            wb.user_id_list = [userid]
        wb.start()  # 爬取微博信息
    except ValueError:
        print(u'config.json 格式不正确，请参考 '
              u'https://github.com/dataabc/weiboSpider#3程序设置')
    except Exception as e:
        print('Error: ', e)
        traceback.print_exc()



if __name__ == '__main__':
    crawl_followings_to_mysql()
