import argparse
import configparser
import email.utils
import feedparser
import math
import os
import random
import slugify
import urllib.parse
import urllib.request
import webcolors
from PIL import Image, ImageDraw, ImageFont, ImageOps

covers_path = "./covers/"

goodreads_url_fmt = None
shelves = []
resize_collage = True
collage_width = 1920
collage_height = 1080
collage_aspect_ratio = collage_width / collage_height
background_color = (255, 255, 255)
title_color = (0, 0, 0)
force_cols = None
force_rows = None
rotation = 0
rotation_pm = 0
border = 150


def make_collage(covers, title):
    print("Creating collage...")

    max_width = 0
    max_height = 0
    cover_images = []

    for cover in covers:
        image = Image.open(cover).convert("RGBA")
        cover_images.append(image)
        max_width = max(max_width, image.width)
        max_height = max(max_height, image.height)

    width = max_width
    height = max_height
    col_gap = int(max_width * 0.04)
    row_gap = int(max_width * 0.04)
    x_step = width + (2 * col_gap)
    y_step = height + (2 * row_gap)

    best_rows = 0
    best_cols = 0
    best_ratio = 0

    for cols in range(1, len(covers)):
        rows = int(math.ceil(len(covers) / cols))
        local_width = (x_step * cols) + (2 * border) - (2 * col_gap)
        local_height = (y_step * rows) + (2 * border) - (2 * row_gap)
        local_aspect_ratio = local_width / local_height
        if local_aspect_ratio > collage_aspect_ratio:
            ratio_ratio = collage_aspect_ratio / local_aspect_ratio
        else:
            ratio_ratio = local_aspect_ratio / collage_aspect_ratio

        if ratio_ratio > best_ratio:
            best_ratio = ratio_ratio
            best_rows = rows
            best_cols = cols

    if force_cols:
        best_cols = force_cols

    if force_rows:
        best_rows = force_rows

    collage_image_width = (best_cols * x_step) + (2 * border) - (2 * col_gap)
    collage_image_height = (best_rows * y_step) + (2 * border) - (2 * row_gap)
    collage_image_aspect_ratio = collage_image_width / collage_image_height

    # print("w: %d, h: %d, a: %f, ta: %f" % (collage_image_width, collage_image_height, collage_image_aspect_ratio, collage_aspect_ratio))

    if collage_image_aspect_ratio < collage_aspect_ratio:
        target_width = collage_image_height * collage_aspect_ratio
        col_gap += int((target_width - collage_image_width) / (best_cols - 1) / 2)
        x_step = width + (2 * col_gap)
        collage_image_width = (best_cols * x_step) + (2 * border) - (2 * col_gap)
    else:
        target_height = collage_image_width / collage_aspect_ratio
        row_gap += int((target_height - collage_image_height) / (best_rows - 1) / 2)
        y_step = height + (2 * row_gap)
        collage_image_height = (best_rows * y_step) + (2 * border) - (2 * row_gap)

    # collage_image_aspect_ratio = collage_image_width / collage_image_height
    # print("w: %d, h: %d, a: %f, ta: %f" % (collage_image_width, collage_image_height, collage_image_aspect_ratio, collage_aspect_ratio))

    collage = Image.new("RGBA", (collage_image_width, collage_image_height), color=background_color)

    x = border - col_gap
    y = border - row_gap
    for cover_image in cover_images:
        cover_image = ImageOps.pad(cover_image, (width, height), color=background_color)
        cover_rotation = random.randint(rotation - rotation_pm, rotation + rotation_pm)
        cover_image = cover_image.rotate(cover_rotation, expand=1)
        collage.paste(cover_image, (x + col_gap, y + row_gap), mask=cover_image)
        x += x_step
        if x >= collage.width - border:
            x = border - col_gap
            y += y_step

    draw = ImageDraw.Draw(collage)
    font = ImageFont.truetype('DejaVuSerif.ttf', 65)
    _, _, text_width, text_height = font.getbbox(title)

    text_x = collage_image_width - (border + text_width)
    text_y = collage_image_height - (border + text_height)

    draw.text((text_x, text_y), title, font=font, fill=title_color)

    if resize_collage:
        collage = collage.resize((collage_width, collage_height))

    return collage


def get_covers(shelf):
    print("Getting covers for shelf %s..." % (shelf))
    os.makedirs(covers_path, exist_ok=True)

    u = urllib.parse.urlparse(goodreads_url_fmt)
    query = urllib.parse.parse_qs(u.query)
    query['shelf'] = shelf
    new_u = urllib.parse.ParseResult(scheme=u.scheme, netloc=u.hostname, path=u.path, params=u.params, query=urllib.parse.urlencode(query, doseq=True), fragment=u.fragment)

    feed = feedparser.parse(new_u.geturl())
    covers_raw = []

    for book in feed.entries:

        if not book.user_read_at:
            read_date = ""
        else:
            read_date = email.utils.parsedate_to_datetime(book.user_read_at)
        # print("Title: ", book.title)
        # print("Read: ", read_date)
        cover_filename = os.path.join(covers_path, book.book_id)

        if os.path.exists(cover_filename):
            # print("  using cached cover image")
            pass
        else:
            # print("  downloading cover image")
            urllib.request.urlretrieve(book.book_large_image_url, cover_filename)
        covers_raw.append((read_date, cover_filename))

    covers_raw.sort(key=lambda tup: tup[0])  # sorts in place

    covers = []
    for date, id in covers_raw:
        covers.append(id)

    return covers


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument("--shelf", type=str, nargs='+', help="Shelf(s) to include in the collage")
    parser.add_argument("--size", type=str, help="Size of collage in pixels WxH, e.g.: 1920x1080")
    parser.add_argument("--aspect", type=str, help="Aspect ratio of collage in W:H, e.g.: 16:9, 8.5:11, actual size will be determined by size of cover images")
    parser.add_argument("--rows", type=int, help="Force collage to have given number of rows.")
    parser.add_argument("--cols", type=int, help="Force collage to have given number of columns.")
    parser.add_argument("--rotation", type=int, help="Rotation of each cover in degrees, w.g.: 10.")
    parser.add_argument("--background-color", type=str, help="Background color, e.g.: black")
    parser.add_argument("--title-color", type=str, help="Title color, e.g.: black")
    parser.add_argument("--title", type=str, help="Title of collage")
    parser.add_argument("--output", type=str, help="Filename of output image")
    parser.add_argument("--border", type=int, help="Size of border")

    args = parser.parse_args()

    if args.shelf is not None:
        shelves = args.shelf

    if args.size is not None:
        collage_width, collage_height = [int(n) for n in args.size.split("x")]
        collage_aspect_ratio = collage_width / collage_height
        resize_collage = True

    if args.aspect is not None:
        w, h = [float(n) for n in args.aspect.split(":")]
        collage_aspect_ratio = w / h
        resize_collage = False

    if args.rows is not None:
        force_rows = args.rows

    if args.cols is not None:
        force_cols = args.cols

    if args.rotation is not None:
        rotation = args.rotation

    if args.background_color is not None:
        if args.background_color.startswith("#"):
            background_color = webcolors.hex_to_rgb(args.background_color)
        else:
            background_color = webcolors.name_to_rgb(args.background_color)

    if args.title_color is not None:
        if args.title_color.startswith("#"):
            title_color = webcolors.hex_to_rgb(args.title_color)
        else:
            title_color = webcolors.name_to_rgb(args.title_color)

    if args.title is not None:
        title = args.title
    else:
        title = ", ".join(shelves)

    if args.border is not None:
        border = args.border

    if shelves is None or len(shelves) == 0:
        print("Atleast one shelf must be specified")
        exit()

    if type(force_cols) != type(force_rows):
        print("--rows and --cols must be specified together")
        exit()

    try:
        config = configparser.RawConfigParser()
        config.read("config")
        goodreads_url_fmt = config["Goodreads"]["rss_url"]
    except:
        print("""
Config file required.

Please create a file named 'config' that contains the follwoing:

---
[Goodreads]
rss_url = https://www.goodreads.com/review/list_rss/123456789?key=qweryasdf&shelf=%23ALL%23
---

The URL can be obtained by visiting Goodreads in a web browser.
- Select "My Books" from the top navigation bar
- Click on the "RSS Feed" icon at the bottom of the page

""")
        exit()

    covers = []
    for shelf in shelves:
        shelf_covers = get_covers(shelf)
        covers += shelf_covers

    collage = make_collage(covers, title)

    if args.output is not None:
        filename = args.output
    else:
        filename_base = "collage-%s-%dx%d" % (slugify.slugify(title), collage.width, collage.height)
        filename = filename_base + ".jpg"
        count = 1
        while os.path.exists(filename):
            filename = filename_base + "_" + str(count) + ".jpg"
            count = count + 1

    print("Saving collage:", filename)
    collage.convert("RGB").save(filename)
