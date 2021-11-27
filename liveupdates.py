import discord
import pymongo
from discord.ext import commands, tasks
import aiohttp
from bs4 import BeautifulSoup


class LiveUpdates(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.col = pymongo.MongoClient("mongodb://localhost:27017/")["stackoverflow"]["tags"]
        self.post_updates.start()

    @tasks.loop(minutes=1)
    async def post_updates(self):
        for x in self.col.find():
            url = f"https://stackoverflow.com/questions/tagged/{x['tag']}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as r:
                    soup = BeautifulSoup(await r.read(), features="lxml")

            question = soup.findAll("div", {"id": "questions"})[0].findAll("div", {"class": "mln24"})[0]
            if question.findAll("h3")[0].findAll("a")[0]["href"] == x["last_url"]:
                continue

            if len(question.findAll("div", {"class": "status unanswered"})) == 0:
                if len(question.findAll("div", {"class": "status answered"})) == 0:
                    answers = question.findAll("div", {"class": "status answered-accepted"})
                else:
                    answers = question.findAll("div", {"class": "status answered"})
                answers = answers[0].getText().strip().replace("answer", "").replace("s", "")
            else:
                answers = "0"

            embed = discord.Embed(title=question.findAll("h3")[0].getText(), color=0xf88424,
                                  description=question.findAll("div", {"class": "excerpt"})[0].getText().strip(),
                                  url=f'https://stackoverflow.com/{question.findAll("h3")[0].findAll("a")[0]["href"]}')
            embed.set_author(icon_url=question.findAll("img")[0]["src"], name=question.findAll("div", {"class": "user-details"})[0].findAll("a")[0].getText())
            embed.add_field(name="Votes", value=question.findAll("span", {"class": "vote-count-post"})[0].getText().strip())
            embed.add_field(name="Answers", value=answers)
            embed.add_field(name="Views", value=question.findAll("div", {"class": "views"})[0].getText().strip())
            embed.add_field(name="Tags", value=", ".join([f"`{x.getText()}`" for x in question.findAll("a", {"class": "post-tag flex--item"})]))
            embed.set_footer(text=f'Asked {question.findAll("span", {"class": "relativetime"})[0].getText()}')
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/771529801235562522/913977934048559134/unknown.png")

            new_points = {"$set": {"last_url": question.findAll("h3")[0].findAll("a")[0]["href"]}}
            self.col.update_one({"tag": x['tag']}, new_points)

            for channel_id in x['channels']:
                channel = self.client.get_channel(channel_id)
                await channel.send(embed=embed)

    @post_updates.before_loop
    async def before_change_status(self):
        await self.client.wait_until_ready()
        print("Background task started.")

    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.has_permissions(manage_guild=True)
    @commands.command()
    async def follow(self, ctx, tag):
        await ctx.trigger_typing()
        
        url = f"https://stackoverflow.com/questions/tagged/{tag}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                soup = BeautifulSoup(await r.read(), features="lxml")
        if len(soup.findAll("div", {"class": "ta-center p24 fs-body3"})) == 1:
            ctx.command.reset_cooldown(ctx)
            return await ctx.reply(f"No tag called `{tag}`.")

        try:
            doc = self.col.find({"tag": tag})[0]
            channels = doc["channels"]
            channels.append(ctx.channel.id)
            new_points = {"$set": {"channels": channels}}
            self.col.update_one({"serverid": ctx.guild.id}, new_points)
        except BaseException:
            self.col.insert_one({"tag": tag, "channels": [ctx.channel.id], "last_url": ""})

        await ctx.reply(f"You are now following `{tag}`!")

    @follow.error
    async def follow_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(title=f"Command Error `{ctx.command}`", description=f"Missing argument `{error.param.name}`.", color=discord.Color.red())
            embed.add_field(name="Usage", value=f"`{ctx.prefix}{ctx.command} {ctx.command.signature}`")
        elif isinstance(error, commands.MissingPermissions):
            missingperms = ",".join([f"`{i}`" for i in error.missing_perms])
            embed = discord.Embed(title="Command Error", description=f"You are missing the following permissions: {missingperms}.", color=discord.Color.red())
        elif isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(title="Command On Cooldown", color=discord.Color.red(),
                                  description=f"The command `{ctx.command}` is on cooldown. Try again in `{round(error.retry_after, 1)}s`.")
            await ctx.reply(embed=embed)
            return
        else:
            embed = discord.Embed(title="Command Error", description="Unknown error occured.", color=discord.Color.red())

        await ctx.reply(embed=embed)
        ctx.command.reset_cooldown(ctx)

    @commands.is_owner()
    @commands.command()
    async def reset_tags(self, ctx):
        for x in self.col.find():
            self.col.delete_one(x)

        await ctx.send("Tag database cleared.")

def setup(client):
    client.add_cog(LiveUpdates(client))