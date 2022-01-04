from config import GROOVY_TOKEN
from clients.SpotifyClient import SpotifyClient

import discord
from discord.ext import commands

from classes.Logger import print_log
from classes.YTDLSource import YTDLSource
from classes.MusicPlayer import MusicPlayer


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""
        if ctx.voice_client is not None:
            ctx.voice_client.source.volume = 35
            return await ctx.voice_client.move_to(channel)

        await channel.connect()
        print_log(self.bot.voice_clients)

    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, url=None):
        await ctx.trigger_typing()

        if url is None:
            if self.bot.music_player is not None:
                await self.resume(ctx)
                self.bot.music_player.start_player = True
            return

        if self.bot.music_player is None:
            self.bot.music_player = MusicPlayer(ctx, self.bot)
        else:
            self.bot.music_player.set_context(ctx)

        await self.add_queue(ctx, url)

    async def add_queue(self, ctx, url):
        tracks = self.get_spotify(url)
        for track in tracks:
            if len(tracks) > 1:
                await self.add_track(ctx, track + "audio", False)
                return
            else:
                await self.add_track(ctx, track + "audio", True)
                return

        await self.add_track(ctx, url, True)

    def get_spotify(self, url):
        tracks = []

        if "https://open.spotify.com/playlist/" in url:
            url = url.removesuffix("https://open.spotify.com/playlist/")
            url = url.split("?")
            sp_id = url[0]

            sp = SpotifyClient()
            playlist = sp.get_playlist(sp_id)

            for track in playlist:
                tracks.append(track)

        if "https://open.spotify.com/track/" in url:
            url = url.removesuffix("https://open.spotify.com/track/")
            url = url.split("?")
            sp_id = url[0]

            sp = SpotifyClient()
            track = sp.get_track(sp_id)
            tracks.append(track)

        return tracks

    async def add_track(self, ctx, name, msg):
        player = await YTDLSource.from_url(name, loop=ctx.bot.loop)

        if ctx.voice_client.is_playing() and msg:
            print_log(f"Added {player.title} to queue")
            await ctx.send("Added **{}** to the queue".format(player.title))
        self.bot.music_player.queue.append(player)
        await self.bot.music_player.queue_count.put(0)

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                print_log(f"Joining channel {ctx.author.voice.channel}")
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")
        else:
            if (
                ctx.author.voice
                and ctx.author.voice.channel != ctx.voice_client.channel
            ):
                self.bot.music_player.clear_queue()
                await ctx.voice_client.disconnect()
                print_log(f"Joining channel {ctx.author.voice.channel}")
                await ctx.author.voice.channel.connect()
                print_log(f"Joined channel {ctx.author.voice.channel}")
                self.bot.music_player.set_context(ctx)

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""
        await ctx.voice_client.disconnect()

    @commands.command()
    async def pause(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_playing():
            return await ctx.send(
                "I am not currently playing anything!", delete_after=20
            )
        elif ctx.voice_client.is_paused():
            return

        ctx.voice_client.pause()
        await ctx.send("Paused current song")

    async def resume(self, ctx):
        if not ctx.voice_client or not ctx.voice_client.is_connected():
            return await ctx.send(
                "I am not currently playing anything!", delete_after=20
            )
        elif not ctx.voice_client.is_paused():
            return

        ctx.voice_client.resume()
        await ctx.send("Resumed the song!")

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        else:
            return await ctx.send(
                "I am not currently playing anything!", delete_after=20
            )


def setup(bot):
    bot.add_cog(Music(bot))