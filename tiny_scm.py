# -*- coding: utf-8 -*-
"""A tiny Scheme interpreter and its read-eval-print loop."""
import sys
import argparse
from primitive_procs import scheme_load, SchemeError, PRIMITIVE_PROCS
from internal_ds import Environment, PrimitiveProcedure
from scm_tokenizer import Tokenizer
try:
    import readline  # history and arrow keys for CLI
except ImportError:
    pass  # but not everyone has it


if sys.version_info[0] < 3:  # Python 2 compatibility
    def input(input_prompt):
        sys.stderr.write(input_prompt)
        sys.stderr.flush()
        line = sys.stdin.readline()
        if not line:
            raise EOFError()
        return line.rstrip('\r\n')

################
# Input/Output #
################


def read_input(infile_lines, input_prompt):
    """Read the input lines."""
    if infile_lines:  # If use a file stream as input
        while infile_lines:
            line = infile_lines.pop(0).strip("\n")
            yield line
        raise EOFError
    else:  # if use a keyboard stream as input
        while True:
            yield input(input_prompt)
            # If a multi-line expression input is not
            # terminated, use whitespace as the
            # the input prompt to read more lines.
            input_prompt = " " * len(input_prompt)


def read_eval_print_loop(env, infile_lines=None, interactive=False,
                         quiet=False, startup=False, load_files=(),
                         report_errors=False):
    """Read and evaluate input until an end of file or keyboard interrupt."""
    if startup:
        for filename in load_files:
            scheme_load(filename, True, env)
    while True:
        try:
            # Open/Reopen a input stream with 'scm> ' as the input prompt,
            # each time we open/reopen the stream, we will read a complete
            # single-line/multi-line expression
            lines_stream = read_input(infile_lines, input_prompt="scm> ")

            # Initialize a tokenizer
            tokenizer = Tokenizer()
            # Tokenize the input lines
            lines_stream = (tokenizer.tokenize(line) for line in lines_stream)

            for line in lines_stream:
                print(line)

        except (SchemeError, SyntaxError, ValueError, RuntimeError) as err:
            if report_errors:
                if isinstance(err, SyntaxError):
                    err = SchemeError(err)
                    raise err
            if (isinstance(err, RuntimeError) and
                    "maximum recursion depth exceeded" not in getattr(
                        err, "args")[0]):
                raise
            elif isinstance(err, RuntimeError):
                print("Error: maximum recursion depth exceeded")
            else:
                print("Error:", err)
        except KeyboardInterrupt:  # <Ctrl>-C
            if not startup:
                raise
            print()
            print("KeyboardInterrupt")
            if not interactive:
                return
        except EOFError:  # <Ctrl>-D, etc.
            print()
            return


def add_primitives(env, funcs_and_names):
    """Enter bindings in `funcs_and_names` into `env`, an environment,
    as primitive procedures. Each item in `funcs_and_names` has the form
    (<python function>, <function name>, <whether to use the environment>).
    """
    for fn, name, use_env in funcs_and_names:
        env.define_variable(name, PrimitiveProcedure(
            fn, name=name, use_env=use_env))


def setup_environment():
    """Initialize and return a single-frame environment including symbols
    associated with the primitive procedures."""
    initial_env = Environment()
    initial_env.define_variable("undefined", None)
    add_primitives(initial_env, PRIMITIVE_PROCS)
    return initial_env


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Tiny Scheme Interpreter")
    parser.add_argument("--load", dest="load", action="store_true",
                        help="This option causes Scheme to load the files")
    parser.add_argument(dest="filenames", metavar="filename", nargs="*",
                        default=[], help="Scheme files to run")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    sys.path.insert(0, "")

    interactive = True
    load_files = []

    if args.load:
        for filename in args.filenames:
            load_files.append(filename)

    the_global_env = setup_environment()
    read_eval_print_loop(env=the_global_env, startup=True,
                         interactive=interactive, load_files=load_files)


if __name__ == "__main__":
    main()
