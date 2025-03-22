class Command:
    """Base Command class"""
    def execute(self, *args, **kwargs):
        raise NotImplementedError("Subclasses must implement the execute method")


class MouseMoveCommand(Command):
    def __init__(self, handler):
        self.handler = handler

    def execute(self, x, y):
        self.handler.on_mouse_move(x, y)


class MouseClickCommand(Command):
    def __init__(self, handler):
        self.handler = handler

    def execute(self, x, y):
        self.handler.on_mouse_click(x, y)


class SendTextCommand(Command):
    def __init__(self, handler):
        self.handler = handler

    def execute(self, text):
        self.handler.send_text(text)


class KeyPressCommand(Command):
    def __init__(self, handler):
        self.handler = handler

    def execute(self, key, modifiers):
        self.handler.on_key_press(key, modifiers)


class MouseWheelCommand(Command):
    def __init__(self, handler):
        self.handler = handler

    def execute(self, amount):
        self.handler.on_mouse_wheel(amount)


class MouseDragCommand(Command):
    def __init__(self, handler):
        self.handler = handler

    def execute(self, x, y):
        self.handler.on_mouse_drag(x, y)


class Memento:
    """Memento class to store the state of a command"""
    def __init__(self, command_name, args, kwargs):
        self.command_name = command_name
        self.args = args
        self.kwargs = kwargs


class CommandInvoker:
    """Invoker class to map and execute commands with undo/redo functionality"""
    def __init__(self, handler):
        self.handler = handler
        self.commands = {
            "mouse_move": MouseMoveCommand(handler),
            "mouse_click": MouseClickCommand(handler),
            "send_text": SendTextCommand(handler),
            "key_press": KeyPressCommand(handler),
            "mouse_wheel": MouseWheelCommand(handler),
            "mouse_drag": MouseDragCommand(handler),
        }
        self.history = []  # Stack to store executed commands
        self.redo_stack = []  # Stack to store commands for redo

    def execute_command(self, command_name, *args, **kwargs):
        if command_name == "undo":
            return self.undo()
        elif command_name == "redo":
            return self.redo()

        command = self.commands.get(command_name)
        if command:
            try:
                command.execute(*args, **kwargs)
                # Save the command to history for undo
                self.history.append(Memento(command_name, args, kwargs))
                # Clear redo stack on new command execution
                self.redo_stack.clear()
                return f"Command '{command_name}' executed successfully."
            except Exception as e:
                return f"Command '{command_name}' failed: {str(e)}"
        else:
            return f"Unknown command: '{command_name}'"

    def undo(self):
        """Undo the last executed command"""
        if not self.history:
            return "No commands to undo."
        memento = self.history.pop()
        self.redo_stack.append(memento)
        return f"Undo: Command '{memento.command_name}' undone."

    def redo(self):
        """Redo the last undone command"""
        if not self.redo_stack:
            return "No commands to redo."
        memento = self.redo_stack.pop()
        self.execute_command(memento.command_name, *memento.args, *memento.kwargs)
        return f"Redo: Command '{memento.command_name}' executed again."
