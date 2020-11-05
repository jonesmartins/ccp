import argparse
import os
from typing import List
import tqdm
import gzip
import sys


def get_finish_argparse():
    parser = argparse.ArgumentParser(
        prog='CCP Finish',
        description='Descomprime e une um conjunto de arquivos baixados pelo CCP em um só.'
    )

    parser.add_argument(
        '-s', '--source',
        dest='source_files',
        nargs='+',
        type=str,
        help='Arquivos fonte.'
    )

    parser.add_argument(
        '-t', '--target',
        dest='target_file',
        type=str,
        help='Arquivo destino'
    )

    return parser

from ccp.utils import bytes2human

def join_downloaded_files(
        source_paths: List[str],
        target_path: str,
):
    total_downloaded_bytes = sum(
        os.path.getsize(path) for path in source_paths
    )

    progress_bar = tqdm.tqdm(
        total_downloaded_bytes,
        f"Juntando {len(source_paths)} arquivos.",
        unit="B",
        unit_scale=True,
        # unit_divisor=read_size
    )
    with open(target_path, 'wb') as complete_file:
        for path in source_paths:
            with open(path, 'rb') as partial_file:
                read_bytes = partial_file.read()
                print(f'Read {len(read_bytes)}')
                try:
                    decompressed_bytes = gzip.decompress(read_bytes)
                    print(
                        f'Decompressed {bytes2human(len(read_bytes))} -> {len(decompressed_bytes)}')
                    complete_file.write(decompressed_bytes)
                    print(
                        f'Wrote (decompressed) {len(decompressed_bytes)} to {target_path}')
                except gzip.BadGzipFile:
                    complete_file.write(read_bytes)
                    print(f'Wrote {bytes2human(len(read_bytes))} to {target_path}')
                finally:
                    progress_bar.update(len(read_bytes))


def delete_files(paths):
    for path in paths:
        os.remove(path)


def run():
    parser = get_finish_argparse()
    parsed_args = parser.parse_args(sys.argv[1:])

    source_files = parsed_args.source_files
    target_file = parsed_args.target_file

    join_downloaded_files(source_files, target_file)
    delete_files(source_files)


if __name__ == '__main__':
    run()