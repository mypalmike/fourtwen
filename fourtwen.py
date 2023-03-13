#!/usr/bin/env python
# fourtwen.py

from __future__ import print_function

import argparse
import codecs
import csv
from collections import defaultdict
from datetime import datetime
import json
import os
import random
import shutil
import sys

from googleapiclient.discovery import build  
from mastodon import Mastodon
from pytz import timezone
import pytz
import requests


def random_420_zone(tznames, strict):
  # Randomize timezones (multiple zones can have same time).
  random.shuffle(tznames)

  # Pick first matching.
  utcnow = pytz.utc.localize(datetime.utcnow())
  for tzname in tznames:
    zone_datetime = utcnow.astimezone(timezone(tzname))
    if zone_datetime.hour == 16 and (zone_datetime.minute == 20 or not strict):
      return tzname

  return None


def random_420_city_tuple(strict):
  pytz_timezones = set(pytz.all_timezones)
  tzname_to_cities = defaultdict(list)

  with open('cities15000.txt', 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter='\t')
    for row in reader:
      city, country_code, admin1_code, tzname = row[2], row[8], row[10], row[17]

      # Filter out timezones we don't have in pytz (none at the time of this writing)
      if row[17] not in pytz_timezones:
          continue

      tzname_to_cities[tzname].append(tuple([city, country_code, admin1_code]))

  found_zone = random_420_zone(list(tzname_to_cities.keys()), strict)

  if found_zone:
    city_list = tzname_to_cities[found_zone]
    city, country_code, admin1_code = random.choice(city_list)
    with open('countryInfo.txt', 'r') as csvfile:
      reader = csv.reader(csvfile, delimiter='\t')
      for row in reader:
        country_code_lookup, country = row[0], row[4]
        if country_code_lookup == country_code:
          return tuple([city, country, country_code, admin1_code])

  return None


def get_img_url(city, country):
  with open('googleAPI.json', 'r') as f_in:
    google_api = json.load(f_in)
  service = build('customsearch', 'v1', developerKey=google_api['key'])
  res = service.cse().list(
      searchType='image',
      q='scenic {} {}'.format(city, country),
      cx=google_api['engine_id'],
    ).execute()
  valid_items = [item for item in res['items'] if item['link'].rsplit('.', 1)[1] in ['jpeg', 'jpg', 'png']]
  item = random.choice(valid_items)
  return item['mime'], item['link']


def get_image(city_tuple):
  try:
    city, country, country_code, admin1_code = city_tuple
    mime_type, img_url = get_img_url(city, country)
    print("Getting {} {}".format(mime_type, img_url))
    extension = img_url.rsplit('.', 1)[1]

    fname = 'img.' + extension

    response = requests.get(img_url, stream=True)
    with open(fname, 'wb') as out_file:
      shutil.copyfileobj(response.raw, out_file)
    return fname
  except Exception as exc:
    raise
    # print (exc)
    # return None


def load_decorations():
  decorations_str = u''
  f = codecs.open('decoration.txt', encoding='utf-8')
  for line in f:
    decorations_str += line.strip()

  decorations = list(decorations_str)
  random.shuffle(decorations)
  return decorations


def decorate_city(city_tuple):
  city, country, country_code, admin1_code = city_tuple
  decorations = load_decorations()
  if country_code == 'US':
    return u"{} It's {} 4:20 {} in {} {}, {} {} {} {}".format(
      decorations[0], decorations[1], decorations[2], decorations[3],
      city, admin1_code, decorations[5], country,
      decorations[6])
  else:
    return u"{} It's {} 4:20 {} in {} {} {} {} {}".format(
      decorations[0], decorations[1], decorations[2], decorations[3],
      city, decorations[4], country, decorations[6])


def post(img_filename, the_post):
  mastodon_server = os.environ["MASTODON_SERVER"]
  client_key = os.environ["CLIENT_KEY"]
  client_secret = os.environ["CLIENT_SECRET"]
  access_token = os.environ["ACCESS_TOKEN"]

  # Set up Mastodon
  mastodon = Mastodon(
    api_base_url = mastodon_server,
    client_id = client_key,
    client_secret = client_secret,
    access_token = access_token,
  )

  media_ids = []
  # with open(img_filename, 'rb') as f_media:
  #   media_dict = mastodon.media_post(f_media)
  #   media_ids.add(media_dict['id'])  

  media_dict = mastodon.media_post(img_filename)
  media_ids.append(media_dict['id'])  

  mastodon.status_post(the_post, media_ids=media_ids)


def main(argv=sys.argv):
  parser = argparse.ArgumentParser(description='Post a photo about the current time.')
  parser.add_argument('-n', '--notweet', action='store_true', help='Generate image file, do not post')
  parser.add_argument('-s', '--strict', action='store_true', help='Strict time check for 20 past the hour')
  args = parser.parse_args(argv[1:])

  city_tuple = random_420_city_tuple(args.strict)

  if args.notweet:
    print(city_tuple)
    print(decorate_city(city_tuple))
  else:
    the_post = decorate_city(city_tuple)
    img_filename = get_image(city_tuple)
    post(img_filename, the_post)


if __name__ == '__main__':
  main()
