import discord

from datetime import datetime
from discord.ext import commands
    
from core import OWNERS
from utilities import permissions, picker, embedder, default

def setup(bot):
    bot.add_cog(Tags(bot))


class Tags(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cxn = bot.connection

    def clean_content(self, content):
        return str(content).replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')

    @commands.command()
    async def tag(self, ctx, *, tag = None):
        if tag is None: return await ctx.send(f"Usage: `{ctx.prefix}tag <tag name>`")
        if tag.isdigit():
            try:
                actual_tag = await self.cxn.fetchrow("SELECT content FROM tags WHERE id = $1", int(tag)) or None
                if actual_tag is None: return await ctx.send(f"No tag with id `{tag}` exists.")
            except Exception as e: return await ctx.send(e)
        else:
            actual_tag = await self.cxn.fetch("SELECT id, name, content FROM tags WHERE name = $1 AND server_id = $2", str(tag).lower(), ctx.guild.id) or None
            if actual_tag is None: return await ctx.send(f"No tag with name `{tag}` exists.")
            print(actual_tag)

        if len(actual_tag) > 1:
            msg = ""
            for i in actual_tag:
                msg += f"ID: {i[0]} Name: {i[1]}\n"
            #build embed have user select which tag they wanted
            return await embedder.EmbedText(
                author={"name": f"{ctx.guild.name} tags named {tag}", "icon_url": f"{ctx.guild.icon_url}"},
                description=f"{msg}",
                color=default.config()["embed_color"]
            ).send(ctx)
        tag = actual_tag[0]
        tag = self.clean_content(tag)
        await ctx.send(tag)


    @commands.command(brief="Create a tag!")
    async def createtag(self, ctx, tagname:str = None, tagcontent:str = None):
        """Create a tag!"""
        if tagname is None: return await ctx.send(f"Usage: `{ctx.prefix}createtag <tag name> <tag content>`")
        if tagcontent is None and not ctx.message.attachments: return await ctx.send(f"Usage: `{ctx.prefix}createtag <tag name> <tag content>`")
        tagcontent = tagcontent or ctx.message.attachments[0]

        await self.cxn.execute("INSERT INTO tags (name, content, server_id, author_id, created_at, updated_at, uses) VALUES ($1, $2, $3, $4, $5, NULL, 0)"
        , tagname.lower(), tagcontent, ctx.guild.id, ctx.author.id, datetime.utcnow())
        await ctx.send(f"<:checkmark:816534984676081705> Created tag `{tagname}.`")


    @commands.command(aliases=['removetag'])
    async def deletetag(self, ctx, tag = None):
        """Delete a specified tag."""
        if tag is None: return await ctx.send(f"Usage: `{ctx.prefix}tag <tag name>`")
        try: 
            int(tag.lower())
            name = await self.cxn.fetchrow("SELECT Tagname FROM tags WHERE TagID = ?", int(tag.lower())) or (None)
            if name is None: return await ctx.send(f"No tag with ID `{tag}` exists.")
            tagID = int(tag.lower())
        except ValueError:
            name = await self.cxn.fetchrow("SELECT Tagname FROM tags WHERE Tagname = ?", tag.lower()) or (None)
            if name is None: return await ctx.send(f"No tag with name `{tag}` exists.")
            tagID = await self.cxn.fetchrow("SELECT TagID FROM tags WHERE Tagname = ?",  str(name).strip("(),'")) or (None)

        tag_creator = await self.cxn.fetchrow("SELECT CreatorID FROM tags WHERE Tagname = ?", str(name).strip("(),'")) or (None)
        if tag_creator is None: return await ctx.send(f"Error occurred")        
        tag_creator = int(str(tag_creator).strip("(),'"))
        if ctx.author.id != tag_creator and ctx.author.id not in OWNERS: return await ctx.send(f":no_entry_sign: You cannot delete a tag that is not yours.")
        name = str(name).strip("(),'")
        tagID = str(tagID).strip("(),'")
        await self.cxn.execute("DELETE FROM tags WHERE Tagname = ?", str(name).strip("(),'"))
        await ctx.send(f"<:checkmark:816534984676081705> Deleted tag `{name}` ID: `{tagID}`")


    @commands.command()
    async def updatetag(self, ctx, tag = None, new_tag: str = None, *, new_tag_content:str = None):
        """Update a tag. Accepts tag name or ID."""
        if tag is None or new_tag is None: return await ctx.send(f"Usage: `{ctx.prefix}updatetag <tag> <new tag name> [new tag content]`")
        try:
            tag = int(tag.lower())
            content = await self.cxn.fetchrow("SELECT Tagcontent FROM tags WHERE TagID = ?", tag) or (None)
            if content is None: return await ctx.send(f":warning: No tag with ID `{tag}` exists.")
        except ValueError:
            tag = str(tag.lower())
            content = await self.cxn.fetchrow("SELECT Tagcontent FROM tags WHERE Tagname = ?", tag) or (None)
            if content is None: return await ctx.send(f":warning: No tag with name `{tag}` exists.")
        if new_tag_content is None: 
            new_tag_content = str(content).strip("(),'")
        tag_id = await self.cxn.fetchrow("SELECT CreatorID FROM tags WHERE TagID = ? OR Tagname = ?", tag, tag) or (None)
        if tag_id is None: return await ctx.send("Error occurred")
        tag_id = str(tag_id).strip("(),'")
        creator_id = await self.cxn.fetchrow("SELECT CreatorID FROM tags WHERE TagID = ? OR Tagname = ?", tag, tag) or (None)
        if creator_id is None: return await ctx.send("Error occurred")
        creator_id = int(str(creator_id).strip("(),'"))
        if ctx.author.id != creator_id and ctx.author.id not in OWNER_IDS: return await ctx.send(":no_entry_sign: You cannot edit a tag that is not yours.")
        await self.cxn.execute("UPDATE tags SET Tagname = ? AND SET Tagcontent = ?", new_tag.lower(), new_tag_content.lower())
        await ctx.send(f"<:checkmark:816534984676081705> Updated tag ID: `{tag_id}`. Tag `{new_tag.lower()}` will now invoke response `{new_tag_content.lower()}`")

    @commands.command(brief="Edit an existing tag")
    async def edittag(self, ctx, tag, *, content: str):
        """
        do stuff
        """
        if tag is None or content is None: return await ctx.send(f"Usage: `{ctx.prefix}edittag <name/id/alias> <content>`")
        if tag.isdigit():
            query = '''SELECT content FROM tags WHERE id = $1 AND server_id = $2'''
            tag = await self.cxn.fetchrow(query, tag, ctx.guild.id)
            if tag is None or tag[0] is None:
                return await ctx.send(f"<:error:816456396735905844> Tag with ID `{tag}` does not exist")
            self.cxn.execute('UPDATE tags SET content = $1, updated = $2 WHERE id = $3 AND server_id = $4)', 
            content, datetime.utcnow(), tag, ctx.guild.id)

            return await ctx.send('Tag "{}" edited.'.format(tag))

        lookup = tag.lower().strip()
        query = '''SELECT lookup FROM tag_lookup WHERE name = $1 AND server_id = $2)'''
        self.cxn.fetchrow(query, lookup, ctx.guild.id)
        if lookup is None:
            return await ctx.send("No tag or alias with that name could be found")
        lookup = lookup[0]
        query = '''SELECT * FROM tags WHERE name = $ AND server_id = $2'''
        a = self.cxn.fetchrow(query, lookup, ctx.guild.id)

        if a != []:
            self.cxn.execute('UPDATE tags SET content = $1, updated = $2 WHERE name= $3 AND server_id = $4)', 
            content, datetime.utcnow(), lookup, ctx.guild.id)

            await ctx.send('Tag "{}" edited.'.format(tag))
        else:
            await ctx.send("That tag doesn't seem to exist.")

    @commands.command()
    async def taginfo(self, ctx, *, tag = None):
        """Get information on a specified tag. Accepts tag name or ID."""
        if tag is None: return await ctx.send(f"Usage: `{ctx.prefix}taginfo <tag>`")

        try:
            tag = int(tag.lower())
            tag_id = await self.cxn.fetchrow("SELECT TagID FROM tags WHERE TagID = ?", tag) or (None)
            if tag_id is None: return await ctx.send(f":warning: No tag with ID `{tag}` exists.")
        except ValueError:
            tag = str(tag.lower())
            tag_id = await self.cxn.fetchrow("SELECT TagID FROM tags WHERE Tagname = ?", tag) or (None)
            if tag_id is None: return await ctx.send(f":warning: No tag with name `{tag}` exists.")

        tag_id = str(tag_id).strip("(),'")

        tagname = await self.cxn.fetchrow("SELECT Tagname FROM tags WHERE TagID = ?", tag_id) or (None)
        if tagname is None: tagname = "N/A"
        tagname = str(tagname).strip("(),'")

        tagcontent = await self.cxn.fetchrow("SELECT Tagcontent FROM tags WHERE TagID = ?", tag_id) or (None)
        if tagcontent is None: tagcontent = "N/A"
        tagcontent = str(tagcontent).strip("(),'")

        creatorname = await self.cxn.fetchrow("SELECT CreatorName FROM tags WHERE TagID = ?", tag_id) or (None)
        if creatorname is None: creatorname = "N/A"
        creatorname = str(creatorname).strip("(),'")

        creatorid = await self.cxn.fetchrow("SELECT CreatorID FROM tags WHERE TagID = ?", tag_id) or (None)
        if creatorid is None: creatorid = "N/A"
        creatorid = str(creatorid).strip("(),'")

        guildname = await self.cxn.fetchrow("SELECT GuildName FROM tags WHERE TagID = ?", tag_id) or (None)
        if guildname is None: guildname = "N/A"
        guildname = str(guildname).strip("(),'")

        guildid = await self.cxn.fetchrow("SELECT GuildID FROM tags WHERE TagID = ?", tag_id) or (None)
        if guildid is None: guildid = "N/A"
        guildid = str(guildid).strip("(),'")

        createdat = await self.cxn.fetchrow("SELECT CreatedAt FROM tags WHERE TagID = ?", tag_id) or (None)
        if createdat is None: createdat = "N/A"
        createdat = str(createdat).strip("(),'")

        creator_obj = await self.bot.fetch_user(creatorid)

        em = discord.Embed(title=f"Tag Name: `{tagname}`", color=ctx.guild.me.color)
        em.set_author(name=creator_obj, icon_url=creator_obj.avatar_url)

        url = self.regex.search(tagcontent)
        if url:
            url = url.group()
            hyperlink = f"[click]({url})"
        else:
            hyperlink = tagcontent

        em.add_field(name="Tag ID:", value=tag_id)
        em.add_field(name="Content:", value=hyperlink)
        em.add_field(name="Creator Name:", value=creatorname)
        em.add_field(name="Creator ID:", value=creatorid)
        em.add_field(name="Guild Name:", value=guildname)
        em.add_field(name="Guild ID:", value=guildid)
        em.add_field(name="Created on:", value=createdat)
        await ctx.send(embed=em)


    @commands.command(aliases=['listtags','taglist'])
    async def tags(self, ctx, user = None):
        await ctx.send("https://tenor.com/view/loading-load-status-progress-gif-7323850")


    async def top_three_tags(self, server):
        emoji = 129351
        a = await self.cxn.fetch('SELECT * FROM tags WHERE server_id = $1 ORDER BY uses DESC LIMIT 3', server.id)
        popular = a
        popular = [x for x in popular]
        for tag in popular:
            emoji += 1
            return (chr(emoji), tag)
        return popular
    def top_three_tags_user(self, user):
        emoji = 129351
        a = self.c.execute(
            'SELECT * FROM tags WHERE (author=? AND server=?) ORDER BY uses DESC LIMIT 3', (user.id, user.guild.id,))
        popular = a.fetchall()
        popular = [x for x in popular]
        for tag in popular:
            yield (chr(emoji), tag)
            emoji += 1


    @commands.command()
    async def stats(self, ctx, user: discord.Member=None):
        """
        Shows information about the tags on a server, or the tags a member owns if you mention someone
        """
        server = ctx.guild
        e = discord.Embed(title=None)
        if user is None:
            b = await self.cxn.fetchrow('SELECT COUNT(*) AS "hello" FROM tags')
            total_tags = b[0]
            t = await self.cxn.fetchrow('SELECT SUM(uses) AS "hello" FROM tags')
            total_uses = t[0]
            e.add_field(name='Global', value='%s tags\n%s uses' %
                        (total_tags, int(total_uses)))
            sum_of_things = await self.cxn.execute(
                'SELECT COUNT(*) FROM tags WHERE server_id = $1', server.id)
            a = sum_of_things[0]
            t = await self.cxn.fetchrow('SELECT SUM(uses) AS "hello" FROM tags WHERE server_id = $1', server.id)
            b = t[0]
            try:
                e.add_field(name=server.name, value='%s tags\n%s uses' %
                            (a, int(b)))
            except TypeError:
                return await ctx.send("This server doesn't seem to have any tags")
            fmt = '{} ({} uses)'
            for tag in await self.top_three_tags(ctx.guild):
                e.add_field(name=' Server Tag',
                            value=fmt.format(tag[0], 1))

        else:
            # user-specific data, we can't guarantee that the mentioned user even has three tags created
            b = await self.cxn.execute('SELECT Count(*) AS "hello" FROM tags WHERE (author_id = $1 AND server_id = $2)', user.id, ctx.guild.id)
            total_tags = b.fetchone()
            if total_tags is None:
                return await ctx.send("That user has zero tags created.")
            total_tags = total_tags[0]
            t = await self.c.execute('SELECT SUM(uses) AS "hello" FROM tags WHERE (author=? AND server=?)', (user.id, ctx.guild.id))
            total_uses = t.fetchone()[0]
            e.add_field(name="Owned tags", value=total_tags)
            e.add_field(name="Owned tag usage", value=int(total_uses))
            for emoji, tag in await self.top_three_tags_user(user):
                e.add_field(name=emoji + ' ' + tag[0],
                            value=f"{int(tag[2])} uses")
        await ctx.send(embed=e)

"""
CREATE TABLE IF NOT EXISTS tags (
    id bigserial PRIMARY KEY,
    name text,
    content text,
    server_id bigint,
    author_id bigint,
    created_at timestamp,
    updated_at timestamp,
    uses bigint DEFAULT 0 NOT NULL
);

CREATE TABLE IF NOT EXISTS tag_search (
    server_id bigint,
    is_alias boolean,
    name text,
    lookup text,
    nsfw boolean,
    mod boolean
);
"""