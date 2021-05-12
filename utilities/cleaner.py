# Module for cleaning messages from all unwanted content
# https://github.com/khazhyk/dango.py/blob/1a1b68f570db3b47523fdfdd88e8199669954f9b/dango/plugins/common/utils.py

import re

def clean_all(string):
    string = clean_invite_embed(string)
    string = clean_single_backtick(string)
    string = clean_double_backtick(string)
    string = clean_triple_backtick(string)
    #string = clean_newline(string)
    #string = clean_formatting(string)
    string = clean_mentions(string)
    string = clean_emojis(string)
    return string

def clean_invite_embed(line):
    """Makes invites not embed"""
    return line.replace("discord.gg/", "discord.gg/\u200b")


def clean_single_backtick(line):
    """Clean string for insertion in single backtick code section.
    Clean backticks so we don't accidentally escape, and escape custom emojis
    that would be discordified.
    """
    if re.search('[^`]`[^`]', line) is not None:
        return "`%s`" % clean_double_backtick(line)
    if (line[:2] == '``'):
        line = '\u200b' + line
    if (line[-1] == '`'):
        line = line + '\u200b'
    return clean_emojis(line)


def clean_double_backtick(line):
    """Clean string for isnertion in double backtick code section.
    Clean backticks so we don't accidentally escape, and escape custom emojis
    that would be discordified.
    """
    line.replace('``', '`\u200b`')
    if (line[0] == '`'):
        line = '\u200b' + line
    if (line[-1] == '`'):
        line = line + '\u200b'

    return clean_emojis(line)


def clean_triple_backtick(line):
    """Clean string for insertion in triple backtick code section.
    Clean backticks so we don't accidentally escape, and escape custom emojis
    that would be discordified.
    """
    if not line:
        return line

    i = 0
    n = 0
    while i < len(line):
        if (line[i]) == '`':
            n += 1
        if n == 3:
            line = line[:i] + '\u200b' + line[i:]
            n = 1
            i += 1
        i += 1

    if line[-1] == '`':
        line += '\n'

    return clean_emojis(line)


def clean_newline(line):
    """Cleans string so formatting does not cross lines when joined with \\n.
    Just looks for unpaired '`' characters, other formatting characters do not
    seem to be joined across newlines.
    For reference, discord uses:
    https://github.com/Khan/simple-markdown/blob/master/simple-markdown.js
    """
    match = None
    for match1 in re.finditer(r'(`+)\s*([\s\S]*?[^`])\s*\1(?!`)', line):
        match = match1

    idx = match.end() if match else 0

    line = line[:idx] + line[idx:].replace('`', '\`')

    return line


def clean_formatting(line):
    """Escape formatting items in a string."""
    return re.sub(r"([`*_])", r"\\\1", line)


def clean_mentions(line):
    """Escape anything that could resolve to mention."""
    return line.replace("@", "@\u200b")

def clean_emojis(line):
    """Escape custom emojis."""
    return re.sub(r'<(a)?:([a-zA-Z0-9_]+):([0-9]+)>', '<\u200b\\1:\\2:\\3>', line)
