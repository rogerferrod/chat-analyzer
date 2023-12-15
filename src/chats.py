import os
import re
import argparse
import spacy
import json
from tqdm import tqdm

from parsers import whatsapp_parser, telegram_parser, instagram_parser, skype_parser
from analysis import *
from drawings import *


def run():
    rename = dict()
    if args.rename:
        with open(args.rename, 'r', encoding='utf-8') as json_file:
            rename = json.load(json_file)

    nlp = None
    if args.language == 'italian':
        nlp = spacy.load("it_core_news_sm")
    elif args.language == 'english':
        nlp = spacy.load("en_core_news_sm")

    raw_msg = []
    if args.whatsapp:
        raw_msg += whatsapp_parser(args.whatsapp)
    if args.telegram:
        raw_msg += telegram_parser(args.telegram)
    if args.instagram:
        raw_msg += instagram_parser(args.instagram, args.myself)
    if args.skype:
        raw_msg += skype_parser(args.skype, args.myself, '../resources/skype_emoticons.txt')

    selection = set(args.selection).union({args.myself})

    for msg in raw_msg:
        if msg['conv'] in rename.keys():
            msg['conv'] = rename[msg['conv']]
        if msg['user'] in rename.keys():
            msg['user'] = rename[msg['user']]

    users = set()
    for msg in raw_msg:
        users.add(msg['user'])

    if args.myself not in users:
        raise Exception(str(args.myself) + ' is not present')

    df_msg = pd.DataFrame(raw_msg)
    df_msg['date'] = df_msg['datetime'].dt.date
    df_msg = df_msg[~df_msg['text'].isnull()]

    df_msg['words'] = df_msg['text'].apply(
        lambda x: len(re.split(r'[\s]+', x)) if x not in TO_SKIP else 0)

    first_year = df_msg['datetime'].sort_values().iloc[0].year

    if len(selection) > 1:
        df_msg = df_msg[df_msg['user'].isin(selection)]

    single_convs = df_msg[df_msg['conv'].isin(selection)]
    single_convs = single_convs[~single_convs['group']]
    convs = single_convs.groupby('conv')

    for user, user_msg in tqdm(df_msg.groupby('user'), desc='Plot'):
        slides = []
        conv = convs.get_group(user) if user != args.myself else single_convs
        msgs = user_msg if user != args.myself else df_msg
        analyzer = Analyzer(args, user, msgs, conv, first_year, nlp)

        data = analyzer.stats()
        slides.append(draw_stats(data))

        plot = analyzer.plot_daily_count()
        slides.append(draw_daily(data, plot))

        plot_msg = analyzer.plot_senders_receivers()
        plot_hour = analyzer.plot_hour_activity()
        slides.append(draw_activity(plot_msg, plot_hour))

        plot_emo = analyzer.plot_emoji()
        plot_word = analyzer.plot_wordcloud()
        slides.append(draw_most_used(plot_word, plot_emo))

        if user == args.myself:
            plot_usr = analyzer.plot_users()
            slides.append(draw_users(plot_usr))

            img1, img2 = analyzer.plot_comparison()
            slides.append(draw_final_hist(img1))
            slides.append(draw_final_hist(img2))

        path = os.path.join(args.output, user + '.pdf')
        slides[0].save(path, save_all=True, append_images=slides[1:])


if __name__ == "__main__":
    print('Chat Analysis')

    parser = argparse.ArgumentParser()
    parser.add_argument('-r', '--rename', type=str, help='rename dictionary')
    parser.add_argument('-l', '--language', type=str, help='language', choices=['italian', 'english'],
                        default='italian')
    parser.add_argument('-m', '--myself', type=str, help='own username', required=True)
    parser.add_argument('-o', '--output', type=str, help='output folder', default='../output/')
    parser.add_argument('--instagram', type=str, help='instagram input folder')
    parser.add_argument('--skype', type=str, help='skype input folder')
    parser.add_argument('--telegram', type=str, help='telegram input folder')
    parser.add_argument('--whatsapp', type=str, help='whatsapp input folder')
    parser.add_argument('selection', type=str, help='users selection', nargs='*')

    args = parser.parse_args()

    run()
