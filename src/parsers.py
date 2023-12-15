import os
from datetime import datetime, timedelta
import re
from pathlib import Path
from bs4 import BeautifulSoup
import json
import html
from tqdm import tqdm

PATTERN_DELETED = {'en': {'you deleted this message', 'this message was deleted'},
                   'it': {'hai eliminato questo messaggio', 'questo messaggio è stato eliminato'}
                   }

PATTERN_MEDIA = {'en': '<media omitted>', 'it': '<media omessi>'}

PATTERN_LIKE = {'Liked a message', 'Ha messo "Mi piace" a un messaggio'}

PATTERN_GROUP = {'en': 'created group', 'it': 'creato il gruppo'}

WHATSAPP_TRIGGER_WORDS = {'en': 'with', 'it': 'con'}

DETECT_LANG = {'WhatsApp Chat with': 'en', 'Chat WhatsApp con': 'it'}


def _filter_text(text, source=None, lang=None):
    filtered = text

    if source == 'whatsapp':
        if text.lower().replace('.', '') in PATTERN_DELETED[lang]:
            return None

        if text.lower() == PATTERN_MEDIA[lang]:
            return '$$media_omitted$$'

    if re.match('(https://|http://|www.).*', text.lower()):
        return '$$link$$'

    if source == 'instagram':
        if text in PATTERN_LIKE:
            return '♥'

    return html.unescape(filtered)


def _parse_skype(content, emoji_map):
    tag = content.name

    if tag == 'p':
        return content.text

    if tag == 'quote' or tag == 'at':
        text = ''
        siblings = [x for x in content.next_siblings]

        for sibling in siblings:
            if isinstance(sibling, str):
                text += sibling
            else:
                text += _parse_skype(sibling, emoji_map)
        return text

    if tag == 'uriobject' or tag == 'mediaalbum':
        return '$$media_omitted$$'
    if tag == 'a':
        return '$$link$$'
    if tag == 'ss':
        e_code = content.text
        return emoji_map[e_code] if e_code in emoji_map.keys() else '🏳️'
    if tag == 'b':
        return str(content.next.text)

    return ''


def whatsapp_parser(path):
    messages = []
    files = list(Path(path).glob('*.txt'))
    for file in tqdm(files, desc='Whatsapp'):
        try:
            lines = list(file.read_text(encoding='utf-8').splitlines())
            txt = file.name.split('.')[0]
            lang = None
            for k, v in DETECT_LANG.items():
                if k in txt:
                    lang = v
                    break
            if lang is None:
                raise Exception('cannot detect language')

            is_group = PATTERN_GROUP[lang] in lines[0] or PATTERN_GROUP[lang] in lines[1]
            conv_usr = None if is_group else file.name.split(WHATSAPP_TRIGGER_WORDS[lang])[-1].strip().split('.')[0]

            for i, line in enumerate(lines):
                try:
                    new_msg = re.match('([\d]+/[\d]+/[\d]+),\s([\d]+:[\d]+)\s-\s(.*)', line)

                    if new_msg is not None:
                        new_msg = new_msg.groups()
                        date_splits = new_msg[0].split('/')
                        year = '20' + date_splits[2]
                        time_splits = new_msg[1].split(':')
                        if lang == 'en':
                            date = datetime(int(year), int(date_splits[0]), int(date_splits[1]), int(time_splits[0]),
                                            int(time_splits[0]))
                        else:
                            date = datetime(int(year), int(date_splits[1]), int(date_splits[0]), int(time_splits[0]),
                                            int(time_splits[0]))

                        splits = new_msg[2].split(': ', maxsplit=1)
                        if len(splits) == 2:
                            user = splits[0]
                            content = splits[1].strip()
                            text = _filter_text(content, 'whatsapp', lang)
                            messages.append(
                                {'datetime': date, 'user': user, 'group': is_group, 'content': content,
                                 'text': text, 'conv': conv_usr, 'social': 'whatsapp'})

                    else:
                        content = line.strip()
                        text = _filter_text(content, 'whatsapp', lang)

                        last_msg = messages[-1]
                        last_msg['content'] += '\n' + content
                        last_msg['text'] += '\n' + text
                except Exception as e:
                    print('Skip line {0} of {1}\t{2}'.format(i, file.name, str(e)))

        except Exception as e:
            print('Error while parsing {0}\t{1}'.format(file.name, str(e)))

    return messages


def telegram_parser(path):
    messages = []

    files = list(Path(path).glob('./*/*.html'))
    pbar = tqdm(total=len(files), desc='Telegram')
    del files

    for foldername in os.listdir(path):
        filepath = os.path.join(path, foldername)
        if os.path.isdir(filepath):
            try:
                with open(os.path.join(filepath, 'messages.html'), 'r', encoding='utf-8') as html_file:
                    soup = BeautifulSoup(html_file, "lxml")
                    history = soup.find('div', {'class': 'history'})
                    service = history.findChildren("div", {'class': 'message service'})
                    is_group = 'group' in service[1].select_one('div').text

                    conv_usr = None if is_group else soup.select_one('div.page_header').find('div', {
                        'class': 'text bold'}).text.strip()

                files = list(Path(filepath).glob('*.html'))
                for file in files:
                    try:
                        soup = BeautifulSoup(file.read_text(encoding='utf-8'), "lxml")
                        history = soup.find('div', {'class': 'history'})
                        msgs = history.findChildren("div", {'class': 'clearfix'}, recursive=False)
                        last_sender = None
                        for i, msg in enumerate(msgs):
                            try:
                                body = msg.find('div', {'class': 'body'})
                                date = body.find('div', {'class': 'date'}).get('title')
                                sender = body.find('div', {'class': 'from_name'})
                                if sender is not None:
                                    last_sender = sender.text.strip()

                                sender = last_sender
                                content = body.find('div', {'class': 'text'})

                                if content is None:
                                    media = body.find('div', {'class': 'media_wrap'})
                                    body = media.find('div', {'class': 'body'})
                                    if body is not None:
                                        content = body.select_one('div.title').text.strip()
                                    else:
                                        content = media.next.next.attrs['class'][-1]
                                    text = '$$media_omitted$$'
                                else:
                                    text = content.text.strip()

                                text = _filter_text(text)

                                groups = re.match('([\d]+).([\d]+).([\d]+)\s([\d]+):([\d]+):([\d]+)', date)
                                groups = groups.groups()
                                date = datetime(int(groups[2]), int(groups[1]), int(groups[0]), int(groups[3]),
                                                int(groups[4]))

                                messages.append(
                                    {'datetime': date, 'user': sender, 'group': is_group, 'content': content,
                                     'text': text, 'conv': conv_usr, 'social': 'telegram'})
                            except Exception as e:
                                print('Skip line {0} of {1}\t{2}'.format(i, str(file), str(e)))
                        pbar.update(1)
                    except Exception as e:
                        print('Error while parsing {0}\t{1}'.format(str(file), str(e)))
            except Exception as e:
                print('Error while parsing {0}\t{1}'.format(str(filepath), str(e)))

    pbar.close()
    return messages


def instagram_parser(path, myself):
    messages = []
    files = list(Path(path).glob('./*/*.json'))
    for file in tqdm(files, desc='Instagram'):
        try:
            raw = file.read_text(encoding='utf-8')
            data = json.loads(raw)

            participants = [x['name'] for x in data['participants'] if x['name'] != myself]
            if len(participants) > 1:
                is_group = True
                conv_usr = None
            else:
                is_group = False
                conv_usr = participants[0].encode('latin1').decode()

            for i, msg in enumerate(data['messages']):
                try:
                    user = msg['sender_name'].encode('latin1').decode()
                    timestamp = int(msg['timestamp_ms']) / 1000
                    date = datetime.fromtimestamp(timestamp)

                    if 'share' in msg.keys():
                        content = msg['share']
                        text = '$$link$$'
                    elif 'content' in msg.keys():
                        content = msg['content']
                        text = msg['content']
                    else:
                        content = None
                        text = '$$media_omitted$$'

                    text = _filter_text(text.encode('latin1').decode(), 'instagram')

                    messages.append({'datetime': date, 'user': user, 'group': is_group, 'content': content,
                                     'text': text, 'conv': conv_usr, 'social': 'instagram'})
                except Exception as e:
                    print('Skip line {0} of {1}\t{2}'.format(i, str(file), str(e)))
        except Exception as e:
            print('Error while parsing {0}\t{1}'.format(str(file), str(e)))

    return messages


def skype_parser(path, myself, emoticons):
    emoji_map = {}
    with open(emoticons, 'r', encoding='utf-8') as emofile:
        for line in emofile:
            splits = re.split(r'[\s]', line.strip())
            emoji_map[splits[0]] = splits[-1]

    messages = []
    try:
        file = open(os.path.join(path, 'messages.json'), 'r', encoding='utf-8')
        data = json.load(file)['conversations']
        for conv in tqdm(data, desc='Skype'):
            if conv['threadProperties'] is not None:
                is_group = conv['threadProperties']['membercount'] > 1
            else:
                is_group = False

            conv_usr = None if is_group else conv['displayName']

            for i, msg in enumerate(conv['MessageList']):
                try:
                    prop = msg['properties']
                    if prop is not None and 'isserversidegenerated' in prop.keys():
                        if prop['isserversidegenerated'] == 'True':  # edited
                            continue

                    date = msg['originalarrivaltime']
                    groups = re.match('([\d]+)-([\d]+)-([\d]+)T([\d]+):([\d]+):([\d]+)', date)
                    groups = groups.groups()

                    date = datetime(int(groups[0]), int(groups[1]), int(groups[2]), int(groups[3]),
                                    int(groups[4])) + timedelta(hours=2)

                    user = msg['displayName']
                    content = msg['content']

                    body = BeautifulSoup(content, "lxml").select_one('body')
                    if body is None:
                        continue

                    content = body.next
                    tag = content.name if body is not None else None

                    if tag is None or tag not in {'p', 'quote', 'at', 'uriobject', 'mediaalbum', 'a', 'ss', 'b'}:
                        continue

                    text = _parse_skype(content, emoji_map)

                    if user is None:
                        user = myself

                    messages.append({'datetime': date, 'user': user, 'group': is_group, 'content': content,
                                     'text': text, 'conv': conv_usr, 'social': 'skype'})
                except Exception as e:
                    print('Skip line {0}\t{1}'.format(i, str(e)))

        file.close()
    except Exception as e:
        print('Error while parsing skype message\t{0}'.format(str(e)))

    return messages
