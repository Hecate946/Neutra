# https://github.com/CuteFwan/Koishi

import io
import math

from datetime import datetime
from PIL import Image, ImageFont, ImageDraw, ImageSequence

from . import utils
from settings.constants import Colors

statusmap = {
    "online": Colors.GREEN,
    "idle": Colors.YELLOW,
    "dnd": Colors.RED,
    "offline": Colors.GRAY,
}


def get_piestatus(statuses, startdate):
    total = sum(statuses.values())
    online = statuses.get("online", 0)
    idle = statuses.get("idle", 0)
    dnd = statuses.get("dnd", 0)
    offline = statuses.get("offline", 0)
    uptime = total - offline

    img = Image.new("RGBA", (2500, 1000), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("./data/assets/Helvetica.ttf", 100)
    shape = [(50, 0), (1050, 1000)]
    start = 0
    for status, value in sorted(statuses.items(), key=lambda x: x[1], reverse=True):
        end = 360 * (value / total) + start
        draw.arc(
            shape,
            start=start,
            end=360 * (value / total) + start,
            fill=statusmap.get(status),
            width=200,
        )
        start = end

    text = f"{uptime/total:.2%}"
    text_width, text_height = draw.textsize(text, font)
    position = ((1100 - text_width) / 2, (1000 - text_height) / 2)
    draw.text(position, text, Colors.WHITE, font=font)

    font = ImageFont.truetype("./data/assets/Helvetica-Bold.ttf", 85)
    draw.text((1200, 0), "Status Tracking Startdate:", fill=Colors.WHITE, font=font)
    font = ImageFont.truetype("./data/assets/Helvetica.ttf", 68)
    draw.text(
        (1200, 100),
        utils.timeago(datetime.utcnow() - startdate),
        fill=Colors.WHITE,
        font=font,
    )
    font = ImageFont.truetype("./data/assets/Helvetica-Bold.ttf", 85)
    draw.text((1200, 300), "Total Online Time:", fill=Colors.WHITE, font=font)
    font = ImageFont.truetype("./data/assets/Helvetica.ttf", 68)
    draw.text(
        (1200, 400),
        f"{uptime/3600:.2f} {'Hour' if int(uptime/3600) == 1 else 'Hours'}",
        fill=Colors.WHITE,
        font=font,
    )

    font = ImageFont.truetype("./data/assets/Helvetica-Bold.ttf", 85)
    draw.text((1200, 600), "Status Information:", fill=Colors.WHITE, font=font)
    font = ImageFont.truetype("./data/assets/Helvetica.ttf", 68)

    draw.rectangle((1200, 700, 1275, 775), fill=Colors.GREEN)
    draw.text(
        (1300, 710),
        f"Online: {online/total:.2%}",
        fill=Colors.WHITE,
        font=font,
    )
    draw.rectangle((1850, 700, 1925, 775), fill=Colors.YELLOW)
    draw.text(
        (1950, 710),
        f"Idle: {idle/total:.2%}",
        fill=Colors.WHITE,
        font=font,
    )
    draw.rectangle((1200, 800, 1275, 875), fill=Colors.RED)
    draw.text(
        (1300, 810),
        f"DND: {dnd/total:.2%}",
        fill=Colors.WHITE,
        font=font,
    )
    draw.rectangle((1850, 800, 1925, 875), fill=Colors.GRAY, outline=(0, 0, 0))
    draw.text(
        (1950, 810),
        f"Offline: {offline/total:.2%}",
        fill=Colors.WHITE,
        font=font,
    )

    buffer = io.BytesIO()
    img.save(buffer, "png")
    buffer.seek(0)
    return buffer


def get_barstatus(title, statuses):
    highest = max(statuses.values())
    highest_unit = get_time_unit(highest)
    units = {stat: get_time_unit(value) for stat, value in statuses.items()}
    heights = {stat: (value / highest) * 250 for stat, value in statuses.items()}
    box_size = (400, 300)
    rect_x_start = {
        k: 64 + (84 * v)
        for k, v in {"online": 0, "idle": 1, "dnd": 2, "offline": 3}.items()
    }
    rect_width = 70
    rect_y_end = 275
    labels = {"online": "Online", "idle": "Idle", "dnd": "DND", "offline": "Offline"}
    base = Image.new(mode="RGBA", size=box_size, color=(0, 0, 0, 0))
    with Image.open("./data/assets/bargraph.png") as grid:
        font = ImageFont.truetype("./data/assets/Helvetica.ttf", 15)
        draw = ImageDraw.Draw(base)
        draw.text((0, 0), highest_unit[1], fill=Colors.WHITE, font=font)
        draw.text((52, 2), title, fill=Colors.WHITE, font=font)
        divs = 11
        for i in range(divs):
            draw.line(
                (
                    (50, 25 + ((box_size[1] - 50) / (divs - 1)) * i),
                    (box_size[0], 25 + ((box_size[1] - 50) / (divs - 1)) * i),
                ),
                fill=(*Colors.WHITE, 128),
                width=1,
            )
            draw.text(
                (5, 25 + ((box_size[1] - 50) / (divs - 1)) * i - 6),
                f"{highest_unit[0]-i*highest_unit[0]/(divs-1):.2f}",
                fill=Colors.WHITE,
                font=font,
            )
        for k, v in statuses.items():
            draw.rectangle(
                (
                    (rect_x_start[k], rect_y_end - heights[k]),
                    (rect_x_start[k] + rect_width, rect_y_end),
                ),
                fill=statusmap[k],
            )
            draw.text(
                (rect_x_start[k], rect_y_end - heights[k] - 13),
                f"{units[k][0]} {units[k][1]}",
                fill=Colors.WHITE,
                font=font,
            )
            draw.text(
                (rect_x_start[k], box_size[1] - 25),
                labels[k],
                fill=Colors.WHITE,
                font=font,
            )
        del draw
        base.paste(grid, None, grid)
    buffer = io.BytesIO()
    base.save(buffer, "png")
    buffer.seek(0)
    return buffer


def get_time_unit(stat):
    word = ""
    if stat >= 604800:
        stat /= 604800
        word = "Week"
    elif stat >= 86400:
        stat /= 86400
        word = "Day"
    elif stat >= 3600:
        stat /= 3600
        word = "Hour"
    elif stat >= 60:
        stat /= 60
        word = "Minute"
    else:
        word = "Second"
    stat = float(f"{stat:.1f}")
    if stat > 1 or stat == 0.0:
        word += "s"
    return stat, word


def resize_to_limit(data, limit):
    """
    Downsize it for huge PIL images.
    Half the resolution until the byte count is within the limit.
    """
    current_size = data.getbuffer().nbytes
    while current_size > limit:
        with Image.open(data) as im:
            data = io.BytesIO()
            if im.format == "PNG":
                im = im.resize([i // 2 for i in im.size], resample=Image.BICUBIC)
                im.save(data, "png")
            elif im.format == "GIF":
                durations = []
                new_frames = []
                for frame in ImageSequence.Iterator(im):
                    durations.append(frame.info["duration"])
                    new_frames.append(
                        frame.resize([i // 2 for i in im.size], resample=Image.BICUBIC)
                    )
                new_frames[0].save(
                    data,
                    save_all=True,
                    append_images=new_frames[1:],
                    format="gif",
                    version=im.info["version"],
                    duration=durations,
                    loop=0,
                    background=im.info["background"],
                    palette=im.getpalette(),
                )
            data.seek(0)
            current_size = data.getbuffer().nbytes
    return data


def extract_first_frame(data):
    with Image.open(data) as im:
        im = im.convert("RGBA")
        b = io.BytesIO()
        im.save(b, "gif")
        b.seek(0)
        return b


def quilt(images):
    xbound = math.ceil(math.sqrt(len(images)))
    ybound = math.ceil(len(images) / xbound)
    size = int(2520 / xbound)

    with Image.new(
        "RGBA", size=(xbound * size, ybound * size), color=(0, 0, 0, 0)
    ) as base:
        x, y = 0, 0
        for avy in images:
            if avy:
                im = Image.open(io.BytesIO(avy)).resize(
                    (size, size), resample=Image.BICUBIC
                )
                base.paste(im, box=(x * size, y * size))
            if x < xbound - 1:
                x += 1
            else:
                x = 0
                y += 1
        buffer = io.BytesIO()
        base.save(buffer, "png")
        buffer.seek(0)
        buffer = resize_to_limit(buffer, 8000000)
        return buffer
