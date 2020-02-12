#-*- coding: utf-8 -*-

from flask import Flask, request, jsonify, Response
import sys
import requests
import math
from opengraph_py3 import OpenGraph
from bs4 import BeautifulSoup
import time
import threading
import re
import html
import json

app = Flask(__name__)
data = {
        "korea":{},
        "world":{},
        "mers":{
                "korea":{},
                "world":{}
                },
        "sars":{
                "korea":{},
                "world":{}
                },
        "youtube" : {},
        "naver" : {}
        }

def crawling():
    global data
    #한국 확진 완치 검사중
    r = requests.get('http://ncov.mohw.go.kr/index_main.jsp')
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.select(".co_cur > ul > li > a")
    infected = int(content[0].text.replace("명",""))
    cured = int(content[1].text.replace("명",""))
    inspection = int(content[2].text.replace("명",""))
    data['korea']['infected'] = infected
    data['korea']['cured'] = cured
    data['korea']['inspection'] = inspection

    #한국 의사환자 결과음성
    r = requests.get('https://www.cdc.go.kr/board/board.es?mid=a20501000000&bid=0015')
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.select("#listView > ul > li > a")
    for i in content:
        if i['title'].startswith("신종코로나바이러스감염증 국내 발생 현황(일일집계통계"):
            r_a = requests.get(f"https://www.cdc.go.kr/{i['href']}")
            break
        else:
            pass
    soup = BeautifulSoup(r_a.content, 'html.parser')
    content = soup.find("table")
    trs = content.find_all("tr")
    suspected = int(trs[3].find_all("td")[5].text.replace(",",""))
    negative = int(trs[3].find_all("td")[7].text.replace(",",""))
    data['korea']['suspected'] = suspected
    data['korea']['negative'] = negative

    #전세계 확진 사망 완치 치사율 발생국가
    r = requests.get('https://www.worldometers.info/coronavirus/')
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.select(".content-inner > div > div > span")
    cases = int(content[0].text.replace(",",""))
    death = int(content[1].text.replace(",",""))
    cured = int(content[2].text.replace(",",""))
    content = soup.find_all("div", {"class": "col-md-6"})[7].find_all("div", {"class": "panel-body"})
    countries = int(re.findall("\d+", content[0].text)[0])
    infected = cases - death - cured
    lethality = round(death/cases*100,2)
    data['world']['infected'] = infected
    data['world']['death'] = death
    data['world']['cured'] = cured
    data['world']['lethality'] = lethality
    data['world']['countries'] = countries

    #메르스2012(한국2015) 사스(2002)
    data['mers']['world']['infected'] = 2494
    data['mers']['world']['death'] = 858
    data['mers']['korea']['infected'] = 186
    data['mers']['korea']['death'] = 36
    data['mers']['world']['lethality'] = 34.4
    data['mers']['world']['countries'] = 27

    data['sars']['world']['infected'] = 8096
    data['sars']['world']['death'] = 774
    data['sars']['korea']['infected'] = 4
    data['sars']['korea']['death'] = 0
    data['sars']['world']['lethality'] = 9.6
    data['sars']['world']['countries'] = 26

    #유튜브 뉴스
    r = requests.get("https://www.googleapis.com/youtube/v3/search?part=snippet&key=토큰&q=%EC%8B%A0%EC%A2%85%EC%BD%94%EB%A1%9C%EB%82%98%EB%B0%94%EC%9D%B4%EB%9F%AC%EC%8A%A4&maxResults=20")
    j = r.json()
    news = []
    for i in j['items']:
	    if "News" in i['snippet']['channelTitle'] or "NEWS" in i['snippet']['channelTitle'] or "뉴스" in i['snippet']['channelTitle']:
		    news.append({
                "title" : html.unescape(i['snippet']['title']),
                "description" : html.unescape(i['snippet']['description']),
                "thumbnail" : i['snippet']['thumbnails']['high']['url'],
                "channelTitle" : i['snippet']['channelTitle'],
                "link" : f"https://www.youtube.com/watch?v={i['id']['videoId']}"
            })
    data['youtube'] = news

    #네이버 뉴스
    client_id = "아이디"
    client_secret = "시크릿"
    r = requests.get("https://openapi.naver.com/v1/search/news?query=신종%20코로나%20바이러스&display=10&start=1&sort=sim&filter=all", headers={"X-Naver-Client-Id":client_id, "X-Naver-Client-Secret":client_secret})
    j = json.loads(r.text)
    news = []
    for i in j['items']:
        news.append({
                "title" : html.unescape(i['title']).replace("<b>","").replace("</b>",""),
                "description" : html.unescape(i['description']).replace("<b>","").replace("</b>",""),
                "thumbnail" : OpenGraph(url=i['link']).image,
                "link" : i['link']
            })
    data['naver'] = news
    threading.Timer(1800, crawling).start()

@app.route('/coronaApi')
def coronaApi():
    json_response = json.dumps(data, ensure_ascii=False, indent=4)
    response = Response(json_response,content_type="application/json; charset=utf-8")
    return response

if __name__ == "__main__":
    crawling()
    app.run(host='0.0.0.0', port=52907, debug=True)