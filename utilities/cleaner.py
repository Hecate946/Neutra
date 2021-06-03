# Module for cleaning messages from all unwanted content

import re


def clean_all(msg):
    msg = clean_invite_embed(msg)
    msg = clean_backticks(msg)
    msg = clean_mentions(msg)
    msg = clean_emojis(msg)
    return msg


def clean_invite_embed(msg):
    """Prevents invites from embedding"""
    return msg.replace("discord.gg/", "discord.gg/\u200b")


def clean_backticks(msg):
    """Prevents backticks from breaking code block formatting"""
    return msg.replace("`", "\U0000ff40")


def clean_formatting(msg):
    """Escape formatting items in a string."""
    return re.sub(r"([`*_])", r"\\\1", msg)


def clean_mentions(msg):
    """Prevent discord mentions"""
    return msg.replace("@", "@\u200b")


def clean_emojis(msg):
    """Escape custom emojis."""
    return re.sub(r"<(a)?:([a-zA-Z0-9_]+):([0-9]+)>", "<\u200b\\1:\\2:\\3>", msg)
