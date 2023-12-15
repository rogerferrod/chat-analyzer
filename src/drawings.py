from PIL import Image, ImageDraw, ImageFont

font_title = ImageFont.truetype('../resources/Calibri Light.ttf', 70)
font_section = ImageFont.truetype('../resources/Calibri Regular.ttf', 40)
font_bold = ImageFont.truetype('../resources/Calibri Bold.ttf', 30)
font_number = ImageFont.truetype('../resources/Calibri Regular.ttf', 30)
font_italic = ImageFont.truetype('../resources/Calibri Italic.ttf', 30)


def draw_users(plot):
    img = Image.new(mode="RGB", size=(2000, 1024), color=(255, 255, 255))
    plot = Image.open(plot)
    img.paste(plot, (650, 200))
    return img


def draw_final_hist(plot):
    img = Image.new(mode="RGB", size=(2000, 1024), color=(255, 255, 255))
    plot = Image.open(plot).resize((1400, 1000))
    img.paste(plot, (280, 30))
    return img


def draw_most_used(plot_word, plot_emo):
    img = Image.new(mode="RGB", size=(2000, 1024), color=(255, 255, 255))
    d = ImageDraw.Draw(img)

    plt1 = Image.open(plot_word).resize((900, 720))
    img.paste(plt1, (160, 100))
    d.text((600, 900), '100 most used words', font=font_italic, font_size=30, anchor="mm", fill=(0, 0, 0))

    plt2 = Image.open(plot_emo).resize((700, 480))
    img.paste(plt2, (1100, 210))
    d.text((1420, 900), '10 most used emojis', font=font_italic, font_size=30, anchor="mm", fill=(0, 0, 0))

    return img


def draw_activity(plot_msg, plot_hour):
    img = Image.new(mode="RGB", size=(2000, 1024), color=(255, 255, 255))
    d = ImageDraw.Draw(img)

    plt1 = Image.open(plot_msg).resize((820, 640))
    img.paste(plt1, (200, 160))
    d.text((600, 900), 'Messages received/sent', font=font_italic, font_size=30, anchor="mm", fill=(0, 0, 0))

    plt2 = Image.open(plot_hour).resize((800, 580))
    img.paste(plt2, (1100, 160))
    d.text((1500, 900), 'Activities by time of  day', font=font_italic, font_size=30, anchor="mm", fill=(0, 0, 0))

    return img


def draw_daily(data, plot):
    img = Image.new(mode="RGB", size=(2000, 1024), color=(255, 255, 255))
    plot = Image.open(plot).resize((1400, 1000))
    img.paste(plot, (300, 30))
    d = ImageDraw.Draw(img, 'RGBA')

    tot = data['tot_msg']
    perc_txt = (data['text'] / tot) * 100
    perc_media = (data['media'] / tot) * 100
    perc_links = (data['links'] / tot) * 100
    _draw_row(d, 80, 'Textual', f'{data["text"]:,}  ({perc_txt:.2f} %)', 100)
    _draw_row(d, 140, 'Multimedia', f'{data["media"]:,}  ({perc_media:.2f} %)', 255)
    _draw_row(d, 200, 'Links', f'{data["links"]:,}  ({perc_links:.2f} %)', 100)

    return img


def draw_stats(data):
    img = Image.new(mode="RGB", size=(2000, 1024), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((1000, 100), data['user'], font=font_title, anchor="ms", fill=(100, 100, 100))

    _draw_section(d, 170, 'TOTAL DAYS', f'{data["tot_days"]:,}')
    _draw_section(d, 310, 'TOTAL MESSAGES', f'{data["tot_msg"]:,}')
    _draw_section(d, 450, 'TOTAL WORDS', f'{data["tot_words"]:,}')
    _draw_section(d, 590, 'AVERAGE MESSAGES PER DAY', f'{data["avg_msg_per_day"]:,.2f}')
    _draw_section(d, 730, 'AVERAGE WORDS PER DAY', f'{data["avg_word_per_day"]:,.2f}', line=False)

    top = 620
    df_social = data['social']
    for k, v in df_social.items():
        logo = '../resources/' + k + '.png'
        _draw_socials(d, img, top, logo, f'{v:.2f} %')
        top += 80

    return img


def _draw_section(d, top, title, text, line=True):
    d.text((60, top), title, font=font_section, fill=(100, 100, 100))
    d.text((60, top + 50), text, font=font_section, font_size=50, fill=(0, 0, 0))
    if line:
        d.line((60, top + 120, 1000, top + 120), fill=(120, 120, 120), width=5)


def _draw_socials(d, img, top, logo, text):
    logo_whatsapp = Image.open(logo)
    img.paste(logo_whatsapp, (1700, top), logo_whatsapp)
    d.text((1800, top + 18), text, anchor="lt", font=font_section, font_size=30, fill=(0, 0, 0))


def _draw_row(d, top, label, text, color):
    d.rectangle([1100, top, 1650, top + 60], fill=(color, color, color, 32), outline=None)
    d.text((1105, top + 30), label, font=font_bold, font_size=30, anchor="lm", fill=(0, 0, 0, 255))
    d.text((1400, top + 30), text, font=font_number, anchor="lm", fill=(0, 0, 0, 255))
