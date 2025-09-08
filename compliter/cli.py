import argparse, sys, pathlib
from .parser import Parser
from .sema import Sema
from .interpreter import Interpreter

def main():
    ap = argparse.ArgumentParser(prog='compliter', description='MiniLang compiler/interpreter')
    sub = ap.add_subparsers(dest='cmd', required=True)
    runp = sub.add_parser('run', help='Interpret and run a program')
    runp.add_argument('file')

    args = ap.parse_args()

    if args.cmd == 'run':
        src = pathlib.Path(args.file).read_text(encoding='utf-8')
        prog = Parser(src).parse()
        Sema(prog).analyze()
        vm = Interpreter(prog)
        rc = vm.run()
        sys.exit(int(rc) if isinstance(rc,int) else 0)

if __name__ == '__main__':
    main()
