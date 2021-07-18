import requests
import sys
import time
import os
import argparse
import pymysql
import configparser

# Connection to Mysql
config = configparser.RawConfigParser()
config.read(filenames= 'my.properties')
# print(config.sections())

# print(db)
scrap_db = pymysql.connect(host='127.0.0.1',user='root',password='',port=3306,db='scraping_trending_youtube',charset = "utf8")
cursor = scrap_db.cursor()
cursor.execute("DROP TABLE IF EXISTS trendings ")
sql = "CREATE TABLE trendings (id INT AUTO_INCREMENT PRIMARY KEY,channel_id VARCHAR(255),title VARCHAR(255),channel_title VARCHAR(255),published_at VARCHAR(255))"
cursor.execute(sql)


snippet_features = ["channelId",
                    "title",
                    "channelTitle",
                    "publishedAt"]

unsafe_characters = ['\n', '"']

header = snippet_features


def setup(api_path, code_path):
    with open(api_path, 'r') as file:
        api_key = file.readline()

    with open(code_path) as file:
        country_codes = [x.rstrip() for x in file]

    return api_key, country_codes


def prepare_feature(feature):
    for ch in unsafe_characters:
        feature = str(feature).replace(ch, "")
    return f'"{feature}"'


def api_request(page_token, country_code):
    request_url = f"https://www.googleapis.com/youtube/v3/videos?part=id,statistics,snippet{page_token}chart=mostPopular&regionCode={country_code}&maxResults=50&key="
#   // Anda perlu memasukan Api Key kedalam key=

    request = requests.get(request_url)
    if request.status_code == 429:
        print("Temp-Banned due to excess requests, please wait and continue later")
        sys.exit()
    return request.json()


def get_tags(tags_list):
    return prepare_feature("|".join(tags_list))


def get_videos(items):
    lines = []
    for video in items:
        snippet = video['snippet']

        features = [prepare_feature(snippet.get(feature, "")) for feature in snippet_features]

        line = features
        lines.append(",".join(line))

        # print(line)

        scrap_db = pymysql.connect(host='127.0.0.1', user='root', password='', port=3306,
                                   db='scraping_trending_youtube',
                                   charset="utf8")
        cursor = scrap_db.cursor()
        cursor.execute("INSERT INTO trendings (channel_id,title,channel_title,published_at) VALUES ({},{},{},{})".format(line[0],line[1],line[2],line[3]))
        scrap_db.commit()
        scrap_db.close()
        cursor.close()


    print("Record inserted successfully into Trendings table")
    return lines


def get_pages(country_code, next_page_token="&"):
    country_data = []
    while next_page_token is not None:
        video_data_page = api_request(next_page_token, country_code)

        next_page_token = video_data_page.get("nextPageToken", None)
        next_page_token = f"&pageToken={next_page_token}&" if next_page_token is not None else next_page_token

        items = video_data_page.get('items', [])
        country_data += get_videos(items)

    return country_data

def write_to_file(country_code, country_data):

    print(f"Writing {country_code} data to file...")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(f"{output_dir}/Data Trending_{time.strftime('%y.%d.%m')}_{country_code}.csv", "w+", encoding='utf-8') as file:
        for row in country_data:
            file.write(f"{row}\n")

def get_data():
    for country_code in country_codes:
        country_data = [",".join(header)] + get_pages(country_code)
        write_to_file(country_code, country_data)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--key_path', help='Path to the file containing the api key, by default will use api_key.txt in the same directory', default='api_key.txt')
    parser.add_argument('--country_code_path', help='Path to the file containing the list of country codes to scrape, by default will use country_codes.txt in the same directory', default='country_codes.txt')
    parser.add_argument('--output_dir', help='Path to save the outputted files in', default='output/')

    args = parser.parse_args()

    output_dir = args.output_dir
    api_key, country_codes = setup(args.key_path, args.country_code_path)

    get_data()
