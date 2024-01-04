import feedparser
import math
import os
import urllib.request
import email.utils
from PIL import Image, ImageDraw, ImageFont, ImageOps

covers_path = "./covers/"
shelf = "2023"
goodreads_url = "https://www.goodreads.com/review/list_rss/118844638?key=gidMdmAKYyxrcdTjUrRUNdHwG0ulEJ_bC9AFFOJrHKTR2R3E&shelf=%s" % (shelf)
collage_width = 19
collage_height = 13
collage_aspect_ratio = collage_width / collage_height
background_color = (255, 255, 255)
title_color = (0, 0, 0)
force_cols = None
force_rows = None
# force_cols = 12
# force_rows = 6


def make_collage(covers):
    print("Creating collage...")

    max_width = 0
    max_height = 0
    cover_images = []

    for cover in covers:
        image = Image.open(cover).convert("RGB")
        cover_images.append(image)
        max_width = max(max_width, image.width)
        max_height = max(max_height, image.height)

    width = max_width
    height = max_height
    col_gap = int(max_width * 0.04)
    row_gap = int(max_width * 0.04)
    border = 150
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

    collage = Image.new("RGB", (collage_image_width, collage_image_height), color=background_color)

    x = border - col_gap
    y = border - row_gap
    for cover_image in cover_images:
        cover_image = ImageOps.pad(cover_image, (width, height), color=background_color)
        collage.paste(cover_image, (x + col_gap, y + row_gap))
        x += x_step
        if x >= collage.width - border:
            x = border - col_gap
            y += y_step

    draw = ImageDraw.Draw(collage)
    font = ImageFont.truetype('DejaVuSerif.ttf', 65)
    title = shelf
    _, _, text_width, text_height = font.getbbox(title)

    text_x = collage_image_width - (border + text_width)
    text_y = collage_image_height - (border + text_height)

    draw.text((text_x, text_y), title, font=font, fill=title_color)

    return collage


def get_covers():
    print("Getting covers...")
    os.makedirs(covers_path, exist_ok=True)
    feed = feedparser.parse(goodreads_url)
    covers_raw = []

    for book in feed.entries:

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
    covers = get_covers()
    collage = make_collage(covers)
    filename = "collage-%s-%d-%d.jpg" % (shelf, collage_width, collage_height)
    print("Saving collage:", filename)
    collage.save(filename)
