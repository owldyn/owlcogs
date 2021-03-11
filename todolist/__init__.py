from .todolist import ToDoList

def setup(bot):
    bot.add_cog(ToDoList(bot))