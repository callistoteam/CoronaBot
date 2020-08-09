import requests
from opengraph_py3 import OpenGraph
from bs4 import BeautifulSoup
import re
import html
import json
import pymysql

youtube_key = ""
naver_id = ""
naver_key = ""

db = pymysql.connect(
    host='host',
    port=3306,
    user='user',
    passwd='passwd',
    db='db',
    charset='utf8',
    autocommit = True
    )
cursor = db.cursor()

def main():
    #한국
    r = requests.get('http://ncov.mohw.go.kr')
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.select("ul.liveNum > li > span")
    infected = {
        'infected' : int(re.findall(r"[-]?\d+",content[0].text.replace(",",""))[0]),
        'dod' : int(re.findall(r"[-]?\d+",content[1].text.replace(",",""))[0])
    }
    cured = {
        'cured' : int(re.findall(r"[-]?\d+",content[2].text.replace(",",""))[0]),
        'dod' : int(re.findall(r"[-]?\d+",content[3].text.replace(",",""))[0])
    }
    death = {
        'death' : int(re.findall(r"[-]?\d+",content[6].text.replace(",",""))[0]),
        'dod' : int(re.findall(r"[-]?\d+",content[7].text.replace(",",""))[0])
    }
    negative = int(re.findall(r"[-]?\d+",soup.select(".numinfo1 > span")[1].text.replace(",",""))[0])
    inspection = int(re.findall(r"[-]?\d+",soup.select(".suminfo > li > span")[1].text.replace(",",""))[0])
    suspected = negative + inspection
    uptime = re.findall(r"[-]?\d+",soup.select(".liveNumOuter > h2:nth-of-type(1) > a:nth-of-type(1) > span:nth-of-type(1)")[0].text)
    uptime = uptime[0]+"/"+uptime[1]
    lethality = round(death['death']/infected['infected']*100,2)
    cursor.execute("UPDATE `data` SET `korea`=%s", json.dumps({
        "infected" : infected,
        "cured" : cured,
        "death" : death,
        "lethality" : lethality,
        "negative" : negative,
        "suspected" : suspected,
        "inspection" : inspection,
        "uptime" : uptime}))

    #한국 - 지역별
    r = requests.get('http://ncov.mohw.go.kr')
    soup = BeautifulSoup(r.content, 'html.parser')
    region = {}
    for count, name in enumerate(["seoul","busan","daegu","incheon","gwangju","daejeon","ulsan","sejong","gg","gangwon","cb","cn","jb","jn","gb","gn","jeju"]):
        content = soup.select(f"#map_city{count+1} > div > ul > li > div > span")
        region[name] = {
            "infected" : int(re.findall(r"[-]?\d+",content[1].text.replace(",",""))[0]),
            "dod" : int(re.findall(r"[-]?\d+",content[3].text.replace(",",""))[0]),
            "death" : int(re.findall(r"[-]?\d+",content[5].text.replace(",",""))[0]),
            "cured" : int(re.findall(r"[-]?\d+",content[7].text.replace(",",""))[0])
        }
    cursor.execute("UPDATE `data` SET `region`=%s", json.dumps(region))
    
    #세계
    r = requests.get('https://www.worldometers.info/coronavirus/')
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.select(".content-inner > div > div > span")
    infected = int(content[0].text.replace(",",""))
    death = int(content[1].text.replace(",",""))
    cured = int(content[2].text.replace(",",""))
    countries = 213
    lethality = round(death/infected*100,2)
    cursor.execute("UPDATE `data` SET `world`=%s", json.dumps({
        "infected" : infected,
        "cured" : cured,
        "death" : death,
        "lethality" : lethality,
        "countries" : countries}))

    #메르스 사스
    cursor.execute("UPDATE `data` SET `mers`=%s", json.dumps({
        "world" : {
            "infected" : 2494,
            "death" : 858,
            "lethality" : 34.4,
            "countries" : 27
        },
        "korea" : {
            "infected" : 186,
            "death" : 36
        }}))

    cursor.execute("UPDATE `data` SET `sars`=%s", json.dumps({
        "world" : {
            "infected" : 8096,
            "death" : 774,
            "lethality" : 9.6,
            "countries" : 26
        },
        "korea" : {
            "infected" : 4,
            "death" : 0
        }}))

    #유튜브 뉴스
    r = requests.get(f"https://www.googleapis.com/youtube/v3/search?part=snippet&key={youtube_key}&q=코로나19&maxResults=5")
    j = r.json()
    youtube = []
    if list(j.keys())[0] != "error":
        for i in j['items']:
            youtube.append({
                    "title" : html.unescape(i['snippet']['title']),
                    "description" : html.unescape(i['snippet']['description']),
                    "thumbnail" : i['snippet']['thumbnails']['high']['url'],
                    "channelTitle" : i['snippet']['channelTitle'],
                    "link" : f"https://www.youtube.com/watch?v={i['id']['videoId']}"
                })
    cursor.execute("UPDATE `data` SET `youtube`=%s", json.dumps(youtube))

    #네이버 뉴스
    r = requests.get(f"https://openapi.naver.com/v1/search/news?query=코로나19&display=10&start=1&sort=sim&filter=all", headers={"X-Naver-Client-Id":naver_id, "X-Naver-Client-Secret":naver_key})
    j = json.loads(r.text)
    naver = []
    for i in j['items']:
        naver.append({
                "title" : html.unescape(i['title']).replace("<b>","").replace("</b>",""),
                "description" : html.unescape(i['description']).replace("<b>","").replace("</b>",""),
                "thumbnail" : OpenGraph(url=i['link']).image,
                "link" : i['link']
            })
    cursor.execute("UPDATE `data` SET `naver`=%s", json.dumps(naver))

    #성별 연령별
    r = requests.get("http://ncov.mohw.go.kr/bdBoardList_Real.do?brdId=1&brdGubun=11&ncvContSeq=&contSeq=&board_id=&gubun=")
    soup = BeautifulSoup(r.content, 'html.parser')
    content = soup.find_all("table")[4]
    trs = content.find_all("tr")
    male = {"infected" : {
        "infected" : int(trs[1].find_all("td")[0].find_all("span")[0].text.replace(",","")),
        "percent" : float(trs[1].find_all("td")[0].find_all("span")[1].text.replace("(","").replace(")",""))},
            "death" : {
        "death" : int(trs[1].find_all("td")[1].find_all("span")[0].text.replace(",","")),
        "percent" : float(trs[1].find_all("td")[1].find_all("span")[1].text.replace("(","").replace(")",""))},
            "lethality" : float(trs[1].find_all("td")[2].find_all("span")[0].text.replace(",",""))}
    female = {"infected" : {
        "infected" : int(trs[2].find_all("td")[0].find_all("span")[0].text.replace(",","")),
        "percent" : float(trs[2].find_all("td")[0].find_all("span")[1].text.replace("(","").replace(")",""))},
            "death" : {
        "death" : int(trs[2].find_all("td")[1].find_all("span")[0].text.replace(",","")),
        "percent" : float(trs[2].find_all("td")[1].find_all("span")[1].text.replace("(","").replace(")",""))},
            "lethality" : float(trs[2].find_all("td")[2].find_all("span")[0].text.replace(",",""))}
    cursor.execute('UPDATE `data` SET `korea`=JSON_SET(korea, "$.male", %s)', json.dumps(male))
    cursor.execute('UPDATE `data` SET `korea`=JSON_SET(korea, "$.female", %s)', json.dumps(female))
    content = soup.find_all("table")[5]
    trs = content.find_all("tr")
    for i in trs:
        try:
            name = i.find("th").text
            value = int(i.find("td").find("span").text.replace(",",""))
        except:
            pass
        if name == "0~9":
            cursor.execute("""UPDATE `data` SET `korea`=JSON_SET(korea, "$.child", %s)""", value)
        elif name == "10~19":
            cursor.execute("""UPDATE `data` SET `korea`=JSON_SET(korea, '$."10s"', %s)""", value)
        elif name == "20~29":
            cursor.execute("""UPDATE `data` SET `korea`=JSON_SET(korea, '$."20s"', %s)""", value)
        elif name == "30~39":
            cursor.execute("""UPDATE `data` SET `korea`=JSON_SET(korea, '$."30s"', %s)""", value)
        elif name == "40~49":
            cursor.execute("""UPDATE `data` SET `korea`=JSON_SET(korea, '$."40s"', %s)""", value)
        elif name == "50~59":
            cursor.execute("""UPDATE `data` SET `korea`=JSON_SET(korea, '$."50s"', %s)""", value)
        elif name == "60~69":
            cursor.execute("""UPDATE `data` SET `korea`=JSON_SET(korea, '$."60s"', %s)""", value)
        elif name == "70~79":
            cursor.execute("""UPDATE `data` SET `korea`=JSON_SET(korea, '$."70s"', %s)""", value)
        elif name == "80 이상":
            cursor.execute("""UPDATE `data` SET `korea`=JSON_SET(korea, '$."80s"', %s)""", value)

if __name__ == "__main__":
    main()