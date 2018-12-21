# -*- coding: utf-8 -*-
import json
import os
import re
import urllib.request
import random
import giphy_client
import pickle

from bs4 import BeautifulSoup
from slackclient import SlackClient
from flask import Flask, request, make_response, render_template
from urllib import parse

app = Flask(__name__)

slack_token = ""
slack_client_id = ""
slack_client_secret = ""
slack_verification = ""
sc = SlackClient(slack_token)


# 크롤링 함수 구현하기
def _crawl_naver_keywords(text, user):
    # 전처리 : 잡코리아의 옵션값들을 가져와서 옵션들의 각 dictionary에 저장
    def preprocess():
        url = "http://www.jobkorea.co.kr/starter/"
        sourcecode = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(sourcecode, "html.parser")

        # 순서대로 지역, 직무, 학력, 근무형태가 담긴 dictionary
        locations = {}
        jobtypes = {}
        edus = {}
        works = {}

        for html_code in soup.find_all('li', class_='itemCheck'):
            html_str = str(html_code)
            if "Area" in html_str:
                locations[html_str.split()[5].split("=")[1].replace('>', '').replace('"', '').strip()] = \
                    html_str.split()[3].split('=')[1].replace('"', '').strip()
            elif "Jobtype" in html_str:
                jobtypes[html_str.split()[5].split("=")[1].replace('>', '').replace('"', '').strip()] = \
                    html_str.split()[3].split('=')[1].replace('"', '').strip()
            elif "Edu" in html_str:
                edus[html_str.split()[5].split("=")[1].replace('>', '').replace('"', '').strip()] = \
                    html_str.split()[3].split('=')[1].replace('"', '').strip()
            elif "Work" in html_str:
                works[html_str.split()[5].split("=")[1].replace('>', '').replace('"', '').strip()] = \
                    html_str.split()[3].split('=')[1].replace('"', '').strip()
        return locations, jobtypes, edus, works

    def saveUserSet(userData):
        file = open("userData.txt", "wb")
        pickle.dump(userData, file)
        file.close()

    def loadUserSet():
        file = open("userData.txt", "rb")
        content = pickle.load(file)
        return content

    # 개발 예정
    # userDAta{'usercode' : [['서울'], ['IT'], ['인턴']] }
    # if "설정" in text:
    #     userData = {user : [[],[],[]]}
    #     userData = loadUserSet()
    #     if user not in userData:
    #         userData[user]=[[],[],[]]
    #     locations, jobtypes, edus, works = preprocess()  # 전처리
    #     if "추가" in text:
    #         for location in locations:
    #             if location in text and location not in userData[user][0]:
    #                 userData[user][0].append(location)
    #         for jobtype in jobtypes:
    #             jobtypeList = jobtype.split('·')
    #             for jt in jobtypeList:
    #                 if jt in text and jobtype not in userData[user][1]:
    #                     userData[user][1].append(jobtype)
    #                     break
    #         for work in works:
    #             if len(work.split()) > 1:
    #                 if work.split[0].strip().replace('형','') in text:
    #                     pass
    #             else:
    #                 pass
    #     elif "삭제" in text:
    #         pass
    #     saveUserSet(userData)
    #     return u"<@" + user + ">님의 설정입니다\n"

    # 지역, 직무, 근무형태에 줄 수 있는 옵션값들을 출력
    if "채용명령어" in text or "채용 명령어" in text:
        locations, jobtypes, edus, works = preprocess() # 전처리 과정을 통해 옵션값을 각 dictionary에 저장

        location_str="[지역] : "
        for location in locations.keys():
            location_str+=location+" , "
        location_str = location_str[:-2]

        jobtype_str="[직무] : "
        for jobtype in jobtypes.keys():
            jobtypeList = jobtype.split('·')
            for jt in jobtypeList:
                jobtype_str += jt + " , "
        jobtype_str = jobtype_str[:-2]

        works_str="[근무형태] : "
        for work in works.keys():
            if len(work.split()) == 1: # 나머지
                works_str += work + " , "
            else : # 전환형 인턴에 대해 예외처리
                works_str += work.split()[0].replace("형", '') + ", "+work.split()[1]+", "
        works_str = works_str[:-2]

        return u""+location_str+"\n"+jobtype_str+"\n"+works_str+"\n"
    # 잡코리아의 검색 시스템을 활용하여 신입공채 검색
    elif "통합검색" in text or "통합 검색" in text:
        my_code = text.split()[0]
        searchName = text.replace(my_code, "").replace("통합검색", "").replace("통합 검색", "").strip() # 사용자가 입력한 키워드중 검색어만 추출
        if len(searchName) == 0: # 검색어가 없는 경우 예외처리
            keywords = []
            keyword = {"text": "키워드의 검색 결과가 없습니다.\n검색어를 확인하신 후 '통합검색 검색어' 형태로 검색 하세요",
                       "thumb_url": "https://lh3.googleusercontent.com/h1O_UBmBw5O4wBQV8H-sizD_gb0hqEwoqayIc7-cqxS--wCXORj3cyadVWo0FU2x7KBa-wIPqw=w128-h128-e365"}
            keywords.append(keyword)
            return (u"검색어가 없습니다.", keywords)

        pretext = ' 통합검색 검색어 : [' + searchName + ']'
        parseSearchName = parse.quote(searchName)

        url = "http://www.jobkorea.co.kr/starter/?schLocal=&schPart=&schMajor=&schEduLevel=&schWork=&schCType=&isSaved=1&LinkGubun=0&LinkNo=0&Page=1&schType=0&schGid=0&schOrderBy=1&schTxt=" + parseSearchName
        print(url)
        sourcecode = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(sourcecode, "html.parser")

        keywords = []
        names = []
        titles = []
        dates = []
        links = []
        # 검색된 결과중 기업명, 채용공고, 마감일 추출하여 출력
        for name in soup.find_all('a', class_='coLink'):
            names.append(name.get_text().strip())

        for title in soup.find_all('div', class_='tit'):
            titles.append(title.find('a', class_='link').get_text().strip())
            links.append(title.find('a', class_='link')['href'])

        for html_str in soup.find_all('ul', class_='filterList'):
            for date in html_str.find_all('div', class_='side'):
                dates.append(
                    date.get_text().strip().replace('채용시', '').replace('자소서 작성', '').replace('\n', '').replace('즉시지원', '').replace('공채자료', ''))

        # 하이퍼 링크 첨부하는 법
        for i in range(int(len(titles) if len(titles) < 19 else 19)):
            keyword = {}

            R = str(hex(random.randrange(0, 256)))[2:]
            G = str(hex(random.randrange(0, 256)))[2:]
            B = str(hex(random.randrange(0, 256)))[2:]

            # slack message builder 형식에 맞춰서 dictionary 생성
            keyword["color"] = '#' + R + G + B
            keyword["title"] = titles[i]
            keyword["title_link"] = "http://www.jobkorea.co.kr" + links[i]
            keyword["text"] = "[*{}*] _*|*_ *{}*".format(names[i], dates[i])
            # 생성된 dictionary를 list에 추가
            keywords.append(keyword)

        if len(keywords) == 0 :
            keyword = {"text": "*'"+searchName+"'*\n키워드의 검색 결과가 없습니다.\n검색어를 확인하신 후 '통합검색 검색어' 형태로 검색 하세요",
                       "thumb_url": "https://lh3.googleusercontent.com/h1O_UBmBw5O4wBQV8H-sizD_gb0hqEwoqayIc7-cqxS--wCXORj3cyadVWo0FU2x7KBa-wIPqw=w128-h128-e365"}
            keywords.append(keyword)
        # _event_handler함수에서 구별을 하기 위해 pretext, keywords형식의 튜플로 반환
        return (pretext, keywords)
    # 잡코리아 신입공채의 채용 검색 및 상세 검색
    elif "채용" in text:
        pretext = '실시간 채용 공고 (' # 제목
        locations, jobtypes, edus, works = preprocess() # 전처리
        url = "http://www.jobkorea.co.kr/starter/?schLocal="
        # 사용자가 입력한 옵션값을 토대로 URL에 옵션값 추가
        search_locations = []
        for location in locations.keys():
            if location in text:
                search_locations.append(locations[location])
                pretext += location + ","

        if len(search_locations) > 0:
            url += ",".join(search_locations)

        url += "&schPart="

        search_jobtypes = []
        for jobtype in jobtypes.keys():
            jobtypeList = jobtype.split('·')
            for jt in jobtypeList:
                if jt in text.upper():
                    search_jobtypes.append(jobtypes[jobtype])
                    pretext += jobtype + ","
                    break

        if len(search_jobtypes) > 0:
            url += ",".join(search_jobtypes)

        # EduLevel은 default 값
        url += "&schMajor=&schEduLevel=&schWork="

        search_works = []
        for work in works.keys():
            if len(work.split()) == 1 :
                if work in text:
                    search_works.append(works[work])
                    pretext += work + ","
            else :
                if work.split()[0].replace('형','') in text:
                    search_works.append(works[work])
                    pretext += work + ","

        if len(search_works) > 0:
            url += ",".join(search_works)

        url += "&schCType=&isSaved=1&LinkGubun=0&LinkNo=0&schOrderBy=1&Page=1"

        sourcecode = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(sourcecode, "html.parser")
        pretext = pretext[:-1] + ")\n" if len(search_works+search_jobtypes+search_locations) > 0 else pretext[:-1]+"\n"
        keywords = []
        names = []
        titles = []
        dates = []
        links = []
        for name in soup.find_all('a', class_='coLink'):
            names.append(name.get_text().strip())

        for title in soup.find_all('div', class_='tit'):
            titles.append(title.find('a', class_='link').get_text().strip())
            links.append(title.find('a', class_='link')['href'])

        for html_str in soup.find_all('ul', class_='filterList'):
            for date in html_str.find_all('div', class_='side'):
                dates.append(
                    date.get_text().strip().replace('채용시', '').replace('자소서 작성', '').replace('\n', '').replace('즉시지원', '').replace('공채자료', ''))

        # 하이퍼 링크 첨부하는 법
        for i in range(int(len(titles) if len(titles) < 19 else 19)):
            keyword = {}

            R = str(hex(random.randrange(0, 256)))[2:]
            G = str(hex(random.randrange(0, 256)))[2:]
            B = str(hex(random.randrange(0, 256)))[2:]

            # slack message builder 형식에 맞춰서 dictionary 생성
            keyword["color"] = '#' + R + G + B
            keyword["title"] = titles[i]
            keyword["title_link"] = "http://www.jobkorea.co.kr" + links[i]
            keyword["text"] = "[*{}*] _*|*_ *{}*".format(names[i], dates[i])
            # 생성된 dictionary를 list에 추가
            keywords.append(keyword)

        keyword = {"text": "*'채용명령어'*\n키워드를 입력하시면 채용의 자세한 검색 키워드를 알 수 있습니다.", "thumb_url": "https://lh3.googleusercontent.com/h1O_UBmBw5O4wBQV8H-sizD_gb0hqEwoqayIc7-cqxS--wCXORj3cyadVWo0FU2x7KBa-wIPqw=w128-h128-e365"}
        keywords.append(keyword)
        # _event_handler함수에서 구별을 하기 위해 pretext, keywords형식의 튜플로 반환
        return (pretext, keywords)
    # 벅스 사이트 실시간 음악 랭킹 상위 10개 출력
    elif "음악" in text:
        url = "https://music.bugs.co.kr/chart"
        req = urllib.request.Request(url)

        sourcecode = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(sourcecode, "html.parser")

        keywords = ['Bugs 실시간 음악 차트 Top 10\n']
        titles = []
        artists = []

        for bugs_str in soup.find_all('p', class_='title'):
            titles.append(bugs_str.get_text().strip())

        for bugs_str in soup.find_all('p', class_='artist'):
            artists.append(bugs_str.get_text().strip())

        for i in range(0, 10):
            keywords.append("{}위 : {} / {}".format(i + 1, titles[i], artists[i]))

        # 한글 지원을 위해 앞에 unicode u를 붙혀준다.
        return u'\n'.join(keywords)
    # 실검 [네이버], [다음]의 입력값에 따라 해당 사이트의 실시간 검색어 출력
    elif "실검" in text:
        url = ""
        keywords = []
        tagName = ""
        className = ""
        if "네이버" in text:
            tagName = "span"
            className = "ah_k"
            url = "https://www.naver.com"
        elif "다음" in text:
            tagName = "span"
            className = "txt_issue"
            url = "https://www.daum.net"
        else:
            return u"문장에 '네이버', '다음' 을 포함해 주세요\n"

        req = urllib.request.Request(url)
        sourcecode = urllib.request.urlopen(url).read()
        soup = BeautifulSoup(sourcecode, "html.parser")

        for html_text in soup.find_all(tagName, class_=className):
            hot_str = html_text.get_text()
            if hot_str not in keywords and len(keywords) < 10:
                keywords.append(hot_str)

        return u'\n'.join(keywords)
    # giphy api를 이용해 키워드로 검색해서 나온 gif 파일 출력
    elif "giphy" in text.lower():
        if len(text.strip().split()) == 3:
            api_instance = giphy_client.DefaultApi()
            api_key='dc6zaTOxFJmzC'
            q = text.strip().split()[2]
            limit = 25
            offset=0
            rating='g'
            lang='ko'
            fmt='json'
            print(q)
            gifData = None
            try:
                api_response = api_instance.gifs_search_get(api_key,q,limit=limit,offset=offset,rating=rating,lang=lang,fmt=fmt)
                gifData = api_response.data
            except giphy_client.rest.ApiException as e: # api함수 호출하다가 오류나는 경우
                return u"검색하다가 제가 죽었습니다.\n"

            if len(gifData) == 0:   # 검색 결과가 없을 경우 예외 처리
                return u"이미지 검색 결과가 없습니다.\n"

            idx = random.randrange(0, len(gifData))
            attach = []
            image_link = {}
            image_link['title'] = text.strip().split()[2]
            image_link['image_url'] = gifData[idx].images.downsized.url
            attach.append(image_link)

            return text.strip().split()[2], attach
        else:
            return u"'giphy 검색어' 형태로 입력해주세요.\n"
    # 사용할 수 있는 키워드 출력
    elif "명령" in text:
        return u"*_[사용할 수 있는 명령어]_ : 명령, 채용, 채용명령어, 통합검색, 음악, 실검, giphy*\n"
    # 잘못된 입력
    else:
        return u"해당하는 명령어를 입력하지 않으셨습니다. '명령' 을 입력하여 확인하세요.\n"


# 이벤트 핸들하는 함수
def _event_handler(event_type, slack_event):
    print(slack_event["event"])

    if event_type == "app_mention":
        channel = slack_event["event"]["channel"]
        text = slack_event["event"]["text"]
        user = slack_event["event"]["user"]

        keywords = _crawl_naver_keywords(text, user)
        # keywords의 타입이 튜플이면 hypertext형태로 출력하도록 api_call 인자 전달
        if type(keywords) is tuple:
            sc.api_call(
                "chat.postMessage",
                channel=channel,
                text=keywords[0],  # pretext
                attachments=keywords[1]  # dictionary list
            )
        # 그 외의 경우에는 일반적으로 처리
        else:
            sc.api_call(
                "chat.postMessage",
                channel=channel,
                text=keywords
            )

        return make_response("App mention message has been sent", 200, )

    # ============= Event Type Not Found! ============= #
    # If the event_type does not have a handler
    message = "You have not added an event handler for the %s" % event_type
    # Return a helpful error message
    return make_response(message, 200, {"X-Slack-No-Retry": 1})


@app.route("/listening", methods=["GET", "POST"])
def hears():
    slack_event = json.loads(request.data)

    if "challenge" in slack_event:
        return make_response(slack_event["challenge"], 200, {"content_type":"application/json"})

    if slack_verification != slack_event.get("token"):
        message = "Invalid Slack verification token: %s" % (slack_event["token"])
        make_response(message, 403, {"X-Slack-No-Retry": 1})

    if "event" in slack_event:
        event_type = slack_event["event"]["type"]
        return _event_handler(event_type, slack_event)

    # If our bot hears things that are not events we've subscribed to,
    # send a quirky but helpful error response
    return make_response("[NO EVENT IN SLACK REQUEST] These are not the droids\
                         you're looking for.", 404, {"X-Slack-No-Retry": 1})


@app.route("/", methods=["GET"])
def index():
    return "<h1>Server is ready.</h1>"


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000)
