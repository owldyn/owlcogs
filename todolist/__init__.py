from .todolist import ToDoList

async def setup(bot):
    await bot.add_cog(ToDoList(bot))
