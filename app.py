import asyncio
import os
import re
import sys

from telethon import errors, functions, TelegramClient
from telethon.tl import types

from rich.console import Console

import config

console = Console(highlight=False)

if len(sys.argv) == 1:
	session = console.input(f"Session (in [bold]{config.sessions}[/bold]): ")
else:
	session = " ".join(sys.argv[1:])

client = TelegramClient(
	os.path.join(config.sessions, session),
	config.API_ID,
	config.API_HASH,
	system_version="5.9"
)
	
flood_links = []

async def main():
	global flood_links

	links= []

	async for message in client.iter_messages(config.chat, filter=types.InputMessagesFilterPinned()):
		for link in re.findall(r"https?:\/\/t\.me\b[a-zA-Z0-9\+\/_]*", message.text):
			links.append(link)

	async def join(link: str):
		global flood_links

		entity = None

		try:
			entity = await client.get_entity(link)
		except errors.InviteHashExpiredError:
			console.log(f"[yellow]⌛ [bold]{link}[/bold] has expired[/yellow]")

			return
		except ValueError:
			try:
				await client(functions.messages.ImportChatInviteRequest(link[14:]))

				entity = await client.get_entity(link)
			except errors.InviteHashExpiredError:
				return console.log(f"[yellow]⌛ [bold]{link}[/bold] has expired[/yellow]")
			except errors.FloodWaitError as error:
				console.log(f"[yellow]🕒 Waiting for [bold]{error.seconds}[/bold] seconds due to FloodWaitError...[/yellow]")

				await asyncio.sleep(error.seconds)

				return await join(link)
			except errors.InviteRequestSentError: pass
		except errors.FloodWaitError as error:
			console.log(f"[yellow]🕒 Waiting for [bold]{error.seconds}[/bold] seconds due to FloodWaitError...[/yellow]")

			await asyncio.sleep(error.seconds)

			return await join(link)

		if isinstance(entity, types.ChannelForbidden):
			return console.log(f"[yellow]❌ [bold]{link}[/bold] is private or you are banned[/yellow]")
		elif not isinstance(entity, types.Channel):
			return console.log(f"[yellow]❌ [bold]{link}[/bold] is not of type Channel[/yellow]")

		try:
			await client(functions.channels.JoinChannelRequest(entity))
		except errors.InviteRequestSentError: pass

		if entity: await client.edit_folder(entity, 1)

		console.log(f"[chartreuse2]✓ Successfully joined [bold]{link}[/bold][/chartreuse2]")

	for link in links:
		if "addlist" in link:
			try:
				chatlist = await client(functions.chatlists.CheckChatlistInviteRequest(link))
			except errors.RPCError as error:
				if error.message == "INVITE_SLUG_EXPIRED":
					console.log(f"[yellow]⌛ [bold]{link}[/bold] has expired[/yellow]")

					continue

			if isinstance(chatlist, types.chatlists.ChatlistInviteAlready):
				console.log(f"[yellow]✔ [bold]{link}[/bold] already added[/yellow]")

				continue
			
			try:
				await client(functions.chatlists.JoinChatlistInviteRequest(
					link,
					chatlist.peers
				))
			except errors.RPCError as error:
				if error.message == "FILTER_INCLUDE_TOO_MUCH":
					console.log(f"[yellow]❌ [bold]{link}[/bold] has too many chats[/yellow]")

					continue
			
			try:
				filter_id = (await client(functions.chatlists.CheckChatlistInviteRequest(link))).filter_id
			except AttributeError:
				console.log("[yellow]⚠ Failed to delete folder[/yellow]")
			else:
				left = await client(functions.chatlists.LeaveChatlistRequest(
					types.InputChatlistDialogFilter(filter_id),
					[]
				))


			console.log(f"[chartreuse2]✓ Successfully added [bold]{link}[/bold][/chartreuse2]")
		else:
			await join(link)
		

with client:
	client.loop.run_until_complete(main())