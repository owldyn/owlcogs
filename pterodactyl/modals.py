import discord


class NodeModal(discord.ui.Modal, title="Node info"):
    key = discord.ui.TextInput(
        label="Simc output",
        style=discord.TextStyle.long,
        placeholder="Paste your ed25519 private key here",
        required=True,
    )
    host = discord.ui.TextInput(
        label="Host",
        style=discord.TextStyle.short,
        placeholder="Host IP or FQDN",
        required=True,
    )
    dataset = discord.ui.TextInput(
        label="Dataset",
        style=discord.TextStyle.short,
        placeholder="Dataset to snapshot",
        required=True,
    )
    username = discord.ui.TextInput(
        label="username",
        style=discord.TextStyle.short,
        placeholder="ssh username",
        required=True,
    )
