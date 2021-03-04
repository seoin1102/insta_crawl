# -*- coding: utf-8 -*-
import scrapy
import json
user_accounts = ['jyjyy0926', 'im_in43','hae_jooooo_','fresh_bizzy','jio_o512','sunbaakim']

class InstaCrawlSpider(scrapy.Spider):
    name = 'insta_crawl'
    allowed_domains = ['www.instagram.com/']
    

    def start_requests(self):
        for username in user_accounts:
            url = f'https://www.instagram.com/{username}'
            yield scrapy.Request(url, callback=self.parse)

    def parse(self, response):
        x = response.xpath("//script[starts-with(.,'window._sharedData')]/text()").extract_first()
        json_string = "{" + x.strip().split('= {')[1][:-1]
        data = json.loads(json_string)
        
        # 사용자 이름, 팔로워, 팔로잉 수, 프로필 사진을 json으로 파싱
        user_name = data['entry_data']['ProfilePage'][0]['graphql']['user']['username']
        follower = data['entry_data']['ProfilePage'][0]['graphql']['user']['edge_followed_by']['count']
        following= data['entry_data']['ProfilePage'][0]['graphql']['user']['edge_follow']['count']
        profile_pic = data['entry_data']['ProfilePage'][0]['graphql']['user']['profile_pic_url']
        item = {'user_name':user_name, 'follower':follower,'following':following, 'profile_pic': profile_pic}
        
        yield item