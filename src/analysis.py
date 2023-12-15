import io
import emoji
from datetime import datetime
import pandas as pd

import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from wordcloud import WordCloud

TO_SKIP = ['$$media_omitted$$', '$$link$$']


class Analyzer:
    def __init__(self, args, user, msgs, conv, first_year, nlp):
        self.args = args
        self.user = user
        self.msgs = msgs
        self.conv = conv
        self.first_year = first_year
        self.nlp = nlp

    def plot_hour_activity(self):
        self.msgs['hour'] = self.msgs['datetime'].dt.hour
        tot = self.msgs.shape[0]
        df_hours = self.msgs.groupby('hour').agg(num=('hour', 'count'))
        df_hours.reset_index(inplace=True)
        df_hours = df_hours.rename(columns={'index': 'hour'})
        missing = [x for x in range(24) if x not in df_hours['hour'].tolist()]
        for h in missing:
            df_hours = pd.concat([df_hours, pd.DataFrame({'hour': [h], 'num': [0]})])

        df_hours = df_hours.sort_values(by='hour')
        df_hours['hour'] = df_hours['hour'].apply(lambda x: str(x))
        df_hours['perc'] = df_hours['num'].apply(lambda x: (x / tot) * 100)

        fig = go.Figure(go.Barpolar(r=df_hours.perc, theta=df_hours.hour))
        fig.update_layout(
            template="plotly_white",
            polar=dict(
                angularaxis=dict(
                    direction='clockwise', rotation=90
                )
            ),
            margin=dict(l=5, r=5, t=30, b=30),
            font=dict(size=20)
        )

        img_buf = io.BytesIO()
        fig.write_image(img_buf)
        return img_buf

    def plot_daily_count(self):
        fig, ax = plt.subplots(constrained_layout=True)
        plt.xlabel(' ')
        plt.ylabel('Daily messages')
        sns.histplot(data=self.msgs, x=self.msgs.date, binwidth=1)
        ax.set_ylim(0, 300)
        ax.set_xlim(datetime(self.first_year, 1, 1), datetime.now())
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=300)
        plt.close()
        return img_buf

    def plot_wordcloud(self):
        text = ''
        for msg in self.msgs['text']:
            for r in TO_SKIP:
                msg = msg.replace(r, '')

            if len(msg) == 0:
                continue

            doc = self.nlp(msg.strip().lower())
            filtered_tokens = [token.text for token in doc if not token.is_stop and not token.is_punct]
            text += ' '.join(filtered_tokens)

        wordcloud = WordCloud(background_color="white", max_words=100, max_font_size=40,
                              relative_scaling=.5).generate(text)

        plt.figure()
        plt.imshow(wordcloud)
        plt.axis("off")
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png')
        plt.close()
        return img_buf

    def plot_emoji(self):
        emojis = []
        for msg in self.msgs['text']:
            toks = [x for x in msg.split(' ') if x in emoji.EMOJI_DATA]
            if len(toks) > 0:
                emojis.extend(toks)

        df_raw_emoji = pd.DataFrame({'emoji': emojis})
        df_emoji = df_raw_emoji.groupby('emoji').agg(count=('emoji', 'count'))
        df_emoji['perc'] = df_emoji['count'].apply(lambda x: (x / df_raw_emoji.shape[0]) * 100)
        df_emoji.reset_index(inplace=True)
        df_emoji = df_emoji.rename(columns={'index': 'emoji'})
        df_emoji = df_emoji.sort_values(by='perc', ascending=False).head(10)

        fig = px.pie(df_emoji, values='perc', names='emoji')
        fig.update_traces(textposition='inside', textinfo='label', textfont_size=30)
        fig.update_layout(uniformtext_minsize=15, uniformtext_mode='hide', showlegend=True,
                          legend=dict(font=dict(size=30)),
                          margin=dict(l=5, r=5, t=20, b=20))

        img_buf = io.BytesIO()
        fig.write_image(img_buf)
        return img_buf

    def plot_senders_receivers(self):
        data = self.conv
        other_name = self.user

        if self.user == self.args.myself:
            df_others = self.conv.copy(deep=True)
            df_others['user'] = self.conv['user'].apply(lambda x: 'others' if x != self.args.myself else x)
            data = df_others
            other_name = 'others'

        fig, (ax1, ax2) = plt.subplots(1, 2)
        plt.title(self.user)

        sns.countplot(data=data, x=data.user, order=[other_name, self.args.myself],
                      ax=ax1, palette=sns.color_palette("Paired"))
        ax1.set_xlabel(' ')
        ax1.set_ylabel(' ')
        ax1.set_title('Messages')

        sent = data[data.user == self.args.myself]
        received = data[data.user != self.args.myself]

        df_words = pd.DataFrame([(self.args.myself, sent['words'].sum()), (other_name, received['words'].sum())],
                                columns=['user', 'sum'])

        sns.barplot(data=df_words, x='user', y='sum', order=[other_name, self.args.myself],
                    ax=ax2, palette=sns.color_palette("Paired"))
        ax2.set_xlabel(' ')
        ax2.set_ylabel(' ')
        ax2.yaxis.tick_right()
        ax2.set_title('Words')
        img_buf = io.BytesIO()
        plt.savefig(img_buf, format='png', dpi=300)
        plt.close()
        return img_buf

    def plot_users(self):
        df_raw_users = self.msgs[self.msgs['user'] != self.args.myself]
        df_users = df_raw_users.groupby('user').agg(count=('text', 'count'))
        df_users['perc'] = df_users['count'].apply(lambda x: (x / df_raw_users.shape[0]) * 100)
        df_users.reset_index(inplace=True)
        df_users = df_users.rename(columns={'index': 'user'})
        df_users = df_users.sort_values(by='perc', ascending=False).head(10)

        fig = go.Figure(data=[go.Pie(labels=df_users['user'], values=df_users['perc'], hole=.3)])
        fig.update_traces(textposition='inside', textinfo='percent+label', textfont_size=20)
        fig.update_layout(uniformtext_minsize=12, uniformtext_mode='hide', showlegend=True,
                          margin=dict(l=5, r=5, t=20, b=20))

        img_buf = io.BytesIO()
        fig.write_image(img_buf)
        return img_buf

    def plot_comparison(self):
        df_msg = self.msgs[self.msgs['user'] != self.args.myself]

        fig, ax = plt.subplots(constrained_layout=True)
        plt.title(' ')
        plt.xlabel(' ')
        plt.ylabel('Daily messages')
        g = sns.histplot(data=df_msg, x=df_msg.date, hue="user", element="step")
        ax.set_ylim(0, 300)
        ax.set_xlim(datetime(self.first_year, 1, 1), datetime.now())
        sns.move_legend(g, "upper left", title='')

        img_buf_1 = io.BytesIO()
        plt.savefig(img_buf_1, format='png', dpi=300)
        plt.close()

        fig, ax = plt.subplots(constrained_layout=True)
        plt.title(' ')
        plt.xlabel(' ')
        plt.ylabel('Density')
        g = sns.kdeplot(data=df_msg, x=df_msg.datetime, hue="user", bw_adjust=1)
        ax.set_xlim(datetime(self.first_year, 1, 1), datetime.now())
        sns.move_legend(g, "upper left", title='')

        img_buf_2 = io.BytesIO()
        plt.savefig(img_buf_2, format='png', dpi=300)
        plt.close()

        return img_buf_1, img_buf_2

    def stats(self):
        tot_msg = self.msgs.shape[0]
        tot_days = self.msgs['date'].unique().shape[0]
        tot_words = self.msgs['words'].sum()

        msg_per_day = self.msgs.groupby('date').agg(count=('words', 'count'))
        word_per_day = self.msgs.groupby('date').agg(count=('words', 'sum'))

        avg_msg_per_day = (msg_per_day.sum() / msg_per_day.shape[0])['count']
        avg_word_per_day = (word_per_day.sum() / word_per_day.shape[0])['count']

        media = self.msgs[self.msgs['text'] == '$$media_omitted$$'].shape[0]
        link = self.msgs[self.msgs['text'] == '$$link$$'].shape[0]
        text = tot_msg - media - link

        df_socials = self.msgs.groupby('social').agg(perc=('social', 'count'))
        df_socials['perc'] = df_socials['perc'].apply(lambda x: (x / tot_msg) * 100)

        return {'user': self.user.upper(), 'tot_msg': tot_msg, 'tot_days': tot_days, 'tot_words': tot_words,
                'avg_msg_per_day': avg_msg_per_day, 'avg_word_per_day': avg_word_per_day,
                'media': media, 'links': link, 'text': text, 'social': df_socials['perc'].to_dict()}
