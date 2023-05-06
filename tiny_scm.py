# -*- coding: utf-8 -*-
"""A tiny Scheme interpreter and its read-eval-print loop."""
import sys
import argparse
from primitive_procs import scheme_load, SchemeError, PRIMITIVE_PROCS
from internal_ds import Environment, PrimitiveProcedure, repl_str
from scm_tokenizer import Tokenizer
from scm_parser import Parser
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

##############################
#        Input / Output      #
##############################


def read_input(infile_lines, input_prompt):
    """Reads the input lines."""
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
                         report_errors=False, print_ast=False):
    """Reads and evaluates input until an end of file or keyboard interrupt."""
    if startup:
        for filename in load_files:
            scheme_load(filename, True, env)
    # Initialize a tokenizer instance
    tokenizer = Tokenizer()
    # Initialize a parser instance
    parser = Parser()
    while True:
        try:
            # Open/Reopen a input stream instance with 'scm> ' as the input
            # prompt. The stream instance will be used until all the tokens
            # read are consumed
            lines_stream = read_input(infile_lines, input_prompt="scm> ")

            # Tokenize the input lines
            lines_stream = (tokenizer.tokenize(line) for line in lines_stream)

            # Parse a single expression / multiple expressions util all the
            # tokens are consumed
            while True:
                # Parse a complete expression (single-line or multi-line) at a
                # time
                ast = parser.parse(lines_stream)
                if not quiet and print_ast:
                    print(repl_str(ast))
                # If all the tokens read are consumed, then break
                if parser.is_empty():
                    break
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
    """Enters bindings in `funcs_and_names` into `env`, an environment,
    as primitive procedures. Each item in `funcs_and_names` has the form
    (<python function>, <function name>, <whether to use the environment>).
    """
    for fn, name, use_env in funcs_and_names:
        env.define_variable(name, PrimitiveProcedure(
            fn, name=name, use_env=use_env))


def setup_environment():
    """Initializes and returns a single-frame environment including symbols
    associated with the primitive procedures.
    """
    initial_env = Environment()
    initial_env.define_variable("undefined", None)
    add_primitives(initial_env, PRIMITIVE_PROCS)
    return initial_env


def parse_args():
    """Parses command line arguments."""
    parser = argparse.ArgumentParser(description="Tiny Scheme Interpreter")
    parser.add_argument("--load", dest="load", action="store_true",
                        help="This option causes Scheme to load the files")
    parser.add_argument(dest="filenames", metavar="filename", nargs="*",
                        default=[], help="Scheme files to run")
    parser.add_argument("--ast", dest="ast", action="store_true",
                        help="This option causes Scheme to print the abstract"
                        "syntax trees of expressions instead of their"
                        "evaluation results")
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
                         interactive=interactive, load_files=load_files,
                         print_ast=args.ast)


if __name__ == "__main__":
    main()
