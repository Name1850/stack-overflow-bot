import discord
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup

class Search(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def search_stack(self, url, ctx, title, questions_query, type):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                soup = BeautifulSoup(await r.read(), features="lxml")

        if soup.find("div", {"class": "ta-center p24 fs-body3"}) is not None:
            ctx.command.reset_cooldown(ctx)
            return None

        questions = soup.find("div", {"id": questions_query})
        embed = discord.Embed(title=title, description="", color=0xf88424)
        embed.set_author(name="Stack Overflow", icon_url="https://cdn.discordapp.com/attachments/771529801235562522/913977934048559134/unknown.png")

        if type == "tag": questions_query = questions.findAll("div", {"class": "mln24"})
        else: questions_query = questions.findAll("div", {"class": "question-summary narrow tagged-interesting"})+questions.findAll("div", {"class": "question-summary narrow"})
        for question in questions_query[:10]:
            title = question.find("h3").getText()
            url = f'https://stackoverflow.com/{question.find("h3").find("a")["href"]}'
            embed.description += f"[{title}]({url})\n\n"

        return embed

    @commands.group()
    async def search(self, ctx):
        await ctx.trigger_typing()
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Please choose a subcommand!\n"
                           f"Valid subcommands include: {', '.join([f'`{x}`' for x in ctx.command.walk_commands()])}")

    @search.command()
    async def tag(self, ctx, tag, tab="newest"):
        tabs = ["newest", "frequent", "active", "bounties", "hot", "votes", "unanswered"]
        if tab.lower() not in tabs:
            return await ctx.reply(f"`{tab}` is not a valid tab.\n"
                                   f"Valid tabs include: {', '.join([f'`{x}`' for x in tabs])}")
        url = f"https://stackoverflow.com/questions/tagged/{tag}?tab={tab.capitalize()}"
        embed = await self.search_stack(url, ctx, f"{tab.capitalize()} questions tagged `{tag}`", "questions", "tag")
        if embed is None: await ctx.reply(f"No questions tagged `{tag}`.")
        else: await ctx.reply(embed=embed)

    @search.command()
    async def general(self, ctx, tab="interesting"):
        tabs = ["interesting", "bountied", "hot", "week", "month"]
        if tab.lower() not in tabs:
            return await ctx.reply(f"`{tab}` is not a valid tab.\n"
                                   f"Valid tabs include: {', '.join([f'`{x}`' for x in tabs])}")

        url = f"https://stackoverflow.com/?tab={tab.lower()}"
        embed = await self.search_stack(url, ctx, f"{tab.capitalize()} questions", "qlist-wrapper", "general")
        await ctx.reply(embed=embed)


def setup(client):
    client.add_cog(Search(client))