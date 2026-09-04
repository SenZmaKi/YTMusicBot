from io import BytesIO

from PIL import Image, ImageDraw, ImageFont


def format_time(seconds: float) -> str:
    seconds = max(0, round(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


def render_progress(position: float, duration: float) -> BytesIO:
    width, height = 600, 76
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=18)
    duration = max(duration, 0.001)
    position = min(max(position, 0), duration)
    ratio = position / duration

    label = f"{format_time(position)}  /  {format_time(duration)}"
    draw.text((12, 5), label, fill=(185, 187, 190, 255), font=font)
    left, right, y = 12, width - 12, 55
    handle_x = round(left + (right - left) * ratio)
    draw.rounded_rectangle((left, y - 4, right, y + 4), radius=4, fill=(78, 80, 88, 255))
    draw.rounded_rectangle((left, y - 4, handle_x, y + 4), radius=4, fill=(35, 165, 245, 255))
    draw.ellipse((handle_x - 8, y - 8, handle_x + 8, y + 8), fill=(245, 245, 245, 255))

    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    output.seek(0)
    return output
