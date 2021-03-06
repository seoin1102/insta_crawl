# -*- coding: utf-8 -*-
import scrapy
from urllib.parse import urlencode
import json
import requests
from datetime import datetime
API = '75d53510-8a3a-49e0-b44f-0151bea39e09'

import logging

token = 'a9151baac138bde82e0bf7fd342f741109bb3687'

headers= {'Authorization': 'token ' + token,
    'Accept': 'application/json',
    'Content-Type': 'application/json;charset=UTF-8'
    }
# api의 인플루언서 리스트를 가져옴.
def influencer_list():
    url ='https://api.staging.dabi-api.com/api/influencer/'

    user_list = {}
    i=760
    while 1:
        response = requests.get(url+'?offset='+str(i), headers=headers)
        data = response.json()
        result = data['results']
        
        for i2 in range(len(result)):
            user_list[result[i2]['insta_id']]=result[i2]['pk']    
        i+=20
        if data['next']==None:
            break   
    return user_list   

user_accounts = influencer_list()

# 중복되는 포스트가 있는지 api를 통해 확인함.
def post_url(influencer_id, post_url):
    influencer_dic = influencer_list()
    pk = influencer_dic[influencer_id]
    i = 0
    response = requests.get('https://api.staging.dabi-api.com/api/influencer/'+str(pk)+'/feedback/', headers=headers)
    data = response.json()
    result = data['results']
    for i in range(len(result)):
        if result[i]['post_url'] ==post_url:
            return 1
        else:
            return 0
         
        


def get_url(url):
    payload = {'api_key': API, 'proxy': 'residential', 'timeout': '20000', 'url': url}
    proxy_url = 'https://api.webscraping.ai/html?' + urlencode(payload)
    return proxy_url

class PostSpider(scrapy.Spider):
    name = 'post'
    allowed_domains = ['api.webscraping.ai']
    custom_settings = {'CONCURRENT_REQUESTS_PER_DOMAIN': 5, 'FEED_URI' : "user_accounts2.json"}    

    def start_requests(self):
        for username in user_accounts:
            url = f'https://www.instagram.com/{username}'
            yield scrapy.Request(get_url(url), callback=self.parse)



    
    def parse(self, response):
        x = response.xpath("//script[starts-with(.,'window._sharedData')]/text()").extract_first()
        json_string = "{" + x.strip().split('= {')[1][:-1]
        data = json.loads(json_string)
        
        # 사용자 id, 포스트 주소, 포스트 게시 날짜, 좋아요 수, 댓글 수, 캡션을 json으로 파싱
        user_id = data['entry_data']['ProfilePage'][0]['graphql']['user']['id']
        user_name = data['entry_data']['ProfilePage'][0]['graphql']['user']['username']
        next_page_bool = \
            data['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['page_info'][
                'has_next_page']
        edges = data['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['edges']
        for i in edges:
            url = 'https://www.instagram.com/p/' + i['node']['shortcode']
            if post_url(user_name,url) ==1:
                del(edges[i])
            
            date_posted_timestamp = i['node']['taken_at_timestamp']
            date_posted_human = datetime.fromtimestamp(date_posted_timestamp).strftime("%d/%m/%Y %H:%M:%S")
            like_count = i['node']['edge_media_preview_like']['count'] if "edge_media_preview_like" in i['node'].keys() else ''
            comment_count = i['node']['edge_media_to_comment']['count'] if 'edge_media_to_comment' in i[
                'node'].keys() else ''
            captions = ""
            
            if i['node']['edge_media_to_caption']:
                for i2 in i['node']['edge_media_to_caption']['edges']:
                    captions += i2['node']['text'] 
                captions = [i.replace('\n','') for i in captions]     
                captions = ''.join(captions)   
            item = {'postURL': url, 'date_posted': date_posted_human, 'likeCount': like_count, 'commentCount': comment_count, 'captions': captions}        
            yield item
        if next_page_bool:
            cursor = data['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['page_info'][
                    'end_cursor']
            di = {'id': user_id, 'first': 12, 'after': cursor}
            print(di)
            params = {'query_hash': 'e769aa130647d2354c40ea6a439bfc08', 'variables': json.dumps(di)}
            url = 'https://www.instagram.com/graphql/query/?' + urlencode(params)
            
         
            yield scrapy.Request(get_url(url), callback=self.parse_pages, meta={'pages_di': di})

    def parse_pages(self, response):
        di = response.meta['pages_di']
        data = json.loads(response.text)
        for i in data['data']['user']['edge_owner_to_timeline_media']['edges']:
            url = 'https://www.instagram.com/p/' + i['node']['shortcode']
            date_posted_timestamp = i['node']['taken_at_timestamp']
            captions = ""
            if i['node']['edge_media_to_caption']:
                for i2 in i['node']['edge_media_to_caption']['edges']:
                    captions += i2['node']['text']
                captions = [i.replace('\n','') for i in captions] 
                captions = ''.join(captions)            
            comment_count = i['node']['edge_media_to_comment']['count'] if 'edge_media_to_comment' in i['node'].keys() else ''
            date_posted_human = datetime.fromtimestamp(date_posted_timestamp).strftime("%d/%m/%Y %H:%M:%S")
            like_count = i['node']['edge_media_preview_like']['count'] if "edge_media_preview_like" in i['node'].keys() else ''
            item = {'postURL': url,  'date_posted': date_posted_human,
                    'likeCount': like_count, 'commentCount': comment_count, 'captions': captions}
            yield item
        next_page_bool = data['data']['user']['edge_owner_to_timeline_media']['page_info']['has_next_page']
        if next_page_bool:
            cursor = data['data']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
            di['after'] = cursor
            params = {'query_hash': 'e769aa130647d2354c40ea6a439bfc08', 'variables': json.dumps(di)}
            url = 'https://www.instagram.com/graphql/query/?' + urlencode(params)
            yield scrapy.Request(get_url(url), callback=self.parse_pages, meta={'pages_di': di})

    def get_item(self, response):
        # only from the first page
        item = response.meta['item']
        
        yield item
