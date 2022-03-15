
class MessageStorage:
    """

    Message Storage. Creates a dictionary for each message sent. The key value is the message ID.

    """
    def __init__(self, guild_id):
        """
        Message storage. Will save the guild ID the messages were sent in.
        """
        self._messages = {}
        self.guild_id = guild_id

    def add_message(self, ctx):
        """Adds the given message to the dictionary"""
        self._messages[ctx.message.id] = ctx

    def get_message(self, message_id):
        """Returns the message with the given ID."""
        return self._messages[message_id]

    def encode(self):
        """Returns dict for the redbot storage"""
        return {self.guild_id: self._messages}
