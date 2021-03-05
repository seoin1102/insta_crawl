# -*- coding: utf-8 -*-
import scrapy
from urllib.parse import urlencode
import json
from datetime import datetime
API = '75d53510-8a3a-49e0-b44f-0151bea39e09'
user_accounts = ['jane_sooeun']
import logging


def get_url(url):
    payload = {'api_key': API, 'proxy': 'residential', 'timeout': '20000', 'url': url}
    proxy_url = 'https://api.webscraping.ai/html?' + urlencode(payload)
    return proxy_url

class PicSpider(scrapy.Spider):
    name = 'pic'
    allowed_domains = ['api.webscraping.ai']
    custom_settings = {'CONCURRENT_REQUESTS_PER_DOMAIN': 5}    

    def start_requests(self):
        for username in user_accounts:
            url = f'https://www.instagram.com/{username}'
            yield scrapy.Request(get_url(url), callback=self.parse)

    def parse(self, response):
        x = response.xpath("//script[starts-with(.,'window._sharedData')]/text()").extract_first()
        json_string = "{" + x.strip().split('= {')[1][:-1]
        data = json.loads(json_string)
        
        # 사용자 id, 포스트의 썸네일 사진을 json으로 파싱
        user_id = data['entry_data']['ProfilePage'][0]['graphql']['user']['id']
        next_page_bool = \
            data['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['page_info'][
                'has_next_page']
        edges = data['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['edges']
        for i in edges:
            image_url = i['node']['thumbnail_resources'][-1]['src']
            item = {'image_url': image_url}        
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
            image_url = i['node']['thumbnail_resources'][-1]['src']
            item = {'image_url': image_url}     
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
