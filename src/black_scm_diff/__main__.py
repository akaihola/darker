from argparse import ArgumentParser


def main():
    parser = ArgumentParser()
    parser.add_argument('src', nargs='+')
    args = parser.parse_args()
    for path in args.src:
        reformat(path)
