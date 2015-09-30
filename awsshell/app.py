"""AWS Shell application.

Main entry point to the AWS Shell.

"""
import tempfile
import subprocess

from prompt_toolkit.document import Document
from prompt_toolkit.shortcuts import create_eventloop
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import Always
from prompt_toolkit.interface import CommandLineInterface, Application
from prompt_toolkit.interface import AbortAction, AcceptAction
from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.utils import Callback

from awsshell.ui import create_default_layout


def create_aws_shell(completer, history):
    return AWSShell(completer, history)


class AWSShell(object):
    def __init__(self, completer, history):
        self.completer = completer
        self.history = history
        self._cli = None

    @property
    def cli(self):
        if self._cli is None:
            self._cli = self.create_cli_interface()
        return self._cli

    def run(self):
        while True:
            try:
                document = self.cli.run()
                text = document.text
            except (KeyboardInterrupt, EOFError):
                break
            else:
                if text.strip() in ['quit', 'exit']:
                    break
                if text.startswith('.'):
                    # These are special commands.  The only one supported for
                    # now is .edit.
                    if text.startswith('.edit'):
                        # TODO: Use EDITOR env var.
                        all_commands = '\n'.join(
                            ['aws ' + h for h in list(self.history)
                             if not h.startswith(('.', '!'))])
                    with tempfile.NamedTemporaryFile('w') as f:
                        f.write(all_commands)
                        f.flush()
                        p = subprocess.Popen(['vim', f.name])
                        p.communicate()
                else:
                    if text.startswith('!'):
                        # Then run the rest as a normally shell command.
                        full_cmd = text[1:]
                    else:
                        full_cmd = 'aws ' + text
                    p = subprocess.Popen(full_cmd, shell=True)
                    p.communicate()

    def create_layout(self):
        return create_default_layout(
            u'aws> ', reserve_space_for_menu=True,
            display_completions_in_columns=True)

    def create_buffer(self, completer, history):
        return Buffer(
            history=history,
            completer=completer,
            complete_while_typing=Always(),
            accept_action=AcceptAction.RETURN_DOCUMENT)

    def create_application(self, completer, history):
        key_bindings_registry = KeyBindingManager(
            enable_vi_mode=True,
            enable_system_bindings=False,
            enable_open_in_editor=False).registry
        buffers = {
            'clidocs': Buffer(read_only=True)
        }

        return Application(
            layout=self.create_layout(),
            buffers=buffers,
            buffer=self.create_buffer(completer, history),
            on_abort=AbortAction.RAISE_EXCEPTION,
            on_exit=AbortAction.RAISE_EXCEPTION,
            on_input_timeout=Callback(self.on_input_timeout),
            key_bindings_registry=key_bindings_registry,
        )

    def on_input_timeout(self, cli):
        buffer = cli.current_buffer
        document = buffer.document
        text = document.text
        command = self.completer.current_command
        docs = u''
        #if command:
        #    output = subprocess.check_output(
        #        self.completer.completer.cmd_path + ' help')
        #    docs = output.decode('utf-8')
        cli.buffers['clidocs'].reset(
            initial_document=Document(command, cursor_position=0))

    def create_cli_interface(self):
        # A CommandLineInterface from prompt_toolkit
        # accepts two things: an application and an
        # event loop.
        loop = create_eventloop()
        app = self.create_application(self.completer, self.history)
        cli = CommandLineInterface(application=app, eventloop=loop)
        return cli
