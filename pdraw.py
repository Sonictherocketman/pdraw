#! /usr/bin/env python3
""" pdraw.py -- Procedurally draw artwork based on a text stream input.
Special thanks to Numberphile for giving me the idea for building this.

author: Brian Schrader
"""
import argparse
from base64 import b16encode
import decimal
import io
import logging
import logging.config
import math
import turtle
from tkinter import ALL, EventType
from random import randrange
import sys


logging.config.dictConfig({
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console']
    },
})
logger = logging.getLogger(__name__)


screen = canvas = None


def setup_turtle():
    global screen
    global canvas
    screen = turtle.getscreen()
    canvas = screen.getcanvas()

    turtle.color('black', 'yellow')
    turtle.speed('fastest')
    turtle.resizemode('user')
    turtle.mode('world')
    turtle.tracer(0, 0)
    turtle.hideturtle()


def recenter_screen(l, r, t, b, padding=100):
    turtle.update()
    screen.setworldcoordinates(l-padding, b-padding, r+padding, t+padding)


def make_interactive(l, r, t, b, padding=100):
    turtle.penup()

    def do_zoom(event):
        x = canvas.canvasx(event.x)
        y = canvas.canvasy(event.y)
        factor = 1.01 ** event.delta
        canvas.scale(ALL, x, y, factor, factor)

    canvas.bind("<MouseWheel>", do_zoom)
    canvas.bind('<ButtonPress-1>', lambda event: canvas.scan_mark(event.x, event.y))
    canvas.bind("<B1-Motion>", lambda event: canvas.scan_dragto(event.x, event.y, gain=1))

    width, height = int(abs(l) + abs(r)), int(abs(t) + abs(b))
    centerx, centery = int((l + r) / 2), int((t + b) / 2)
    turtle.setpos(centerx, centery)


def take_picture(fname, l, r, t, b):
    turtle.update()
    width, height = int(abs(l) + abs(r)), int(abs(t) + abs(b))
    canvas.postscript(file=fname)


def shutdown_turtle(close=False):
    if close:
        turtle.bye()
    else:
        turtle.done()


def encode(text, verbose=True):
    if verbose: logger.info('Encoding text stream...')
    chars = (b16encode(t.encode()).decode() for t in text)
    return (int(c, base=16) % 10 for c in chars)


def get_text(f, until, offset, should_encode=False):
    try:
        f.seek(offset+2)
    except io.UnsupportedOperation:
        # This is probably stdin which doesn't support seek()
        pass
    if until:
        text = f.read(until)
    else:
        text = f.read()
    if should_encode:
        text = encode(text)
    return (int(t) for t in text)


def get_random(n, bound=30, start=0):
    for _ in range(n):
        yield randrange(start, bound)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Generate Procedural Artwork from Text'
    )
    parser.add_argument(
        '-i', '--input',
        type=argparse.FileType('r'),
        default=sys.stdin,
        help=(
            'An input file containing either text or numerical digits. If text '
            'use -e to encode text so it can be used.'
        ),
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        help=(
            'Where to save the resultant image. If no value is provided, then no '
            'image is saved once the process completes. It will still be displayed. '
            'pdraw generates .eps files which can be opened in PDF viewing apps.'
        ),
    )
    parser.add_argument(
        '--random',
        action='store_true',
        dest='use_random',
        default=False,
        help='Generate from random numbers instead of an input file.',
    )
    parser.add_argument(
        '-e', '--encode',
        action='store_true',
        default=False,
        help=(
            'Encode the provided text as a base10 string of digits. This is useful '
            'if you would prefer to provide text rather than numbers as input.'
        ),
    )
    parser.add_argument(
        '--offset',
        type=int,
        default=0,
        help=(
            'The point in the stream you would like to begin generating. Defaults '
            'to the start of the stream.'
        ),
    )
    parser.add_argument(
        '-n', '--number',
        type=int,
        default=0,
        help=(
            'The total number of digits to generate. Set 0 to consume the entire '
            'stream though this is not suitable for large streams -- like Pi.'
        ),
    )
    parser.add_argument(
        '-a', '--angle',
        type=int,
        default=90,
        help=(
            'The angle to use for each rotation. This is measured in degrees '
            'up to 180.'
        ),
    )
    parser.add_argument(
        '-r', '--refresh-rate',
        type=int,
        default=100,
        help=(
            'The number of iterations to perform before refreshing the screen. '
            'A value of 1 refreshes after each turn.'
        ),
    )
    parser.add_argument(
        '-d', '--distance',
        type=int,
        default=10,
        help=(
            'A modifier applied to the distance each line extends before the '
            'turn. This has the effect of scaling the drawing up by that factor.'
        ),
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_false',
        default=True,
        dest='verbose',
        help='Do not display progress indicator and status messages.',
    )
    parser.add_argument(
        '-c', '--close',
        action='store_true',
        default=False,
        help='Close the turtle window when drawing is finished.',
    )
    return parser.parse_args()


def main(args):
    if args.number > 100000:
        logger.error('Refusing to draw more than 100000 iterations.')
        return

    input = (
        get_random(args.number)
        if args.use_random
        else get_text(args.input, args.number, args.offset, should_encode=args.encode)
    )
    if not input:
        logger.error('[Error] No input was provided.')
        return

    setup_turtle()
    l, r, t, b = 0, 0, 0, 0
    try:
        for i, digit in enumerate(input):

            # Draw the line
            distance = digit * args.distance
            turtle.forward(distance)
            turtle.left(args.angle)

            # Record the position

            x, y = turtle.position()
            l = min(x, l)
            r = max(x, r)
            t = max(y, t)
            b = min(y, b)

            # Square the coordinates (it looks better w/ a 1:1 ratio)

            l = b = min(l, b)
            r = t = max(r, t)

            # Update UI

            if i % args.refresh_rate == 0:
                recenter_screen(l, r, t, b)
                if args.verbose and args.number:
                    logger.info(f'Progress={100 * (i/args.number) // 1}%')
    except ValueError:
        logger.warning(
            'Could not convert text to useful integers. Did you mean to use --encode?'
        )
        return

    width, height = int(abs(l) + abs(r)), int(abs(t) + abs(b))
    recenter_screen(l, r, t, b)
    if args.verbose: logger.info('Finished drawing')

    if args.output:
        if args.verbose: logger.info('Saving drawing...')
        take_picture(args.output, l, r, t, b)

    if args.verbose: logger.info('Interactive mode enabled')
    make_interactive(l, r, t, b)
    shutdown_turtle(close=args.close)


if __name__ == '__main__':
    main(parse_args())
