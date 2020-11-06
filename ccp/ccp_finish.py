import argparse
import gzip
import os
import sys
from typing import List

import tqdm

from ccp.utils import bytes2human


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

    parser.add_argument(
        '-k', '--keep',
        dest='keep',
        action='store_true',
    )

    return parser


def join_downloaded_files(
        source_paths: List[str],
        target_path: str,
):
    total_downloaded_bytes = sum(
        os.path.getsize(path) for path in source_paths
    )

    progress_bar = tqdm.tqdm(
        total=total_downloaded_bytes,
        desc=f"Juntando {len(source_paths)} arquivos.",
        unit="B",
        unit_scale=True,
        # unit_divisor=read_size
    )
    with progress_bar as p_bar:
        with open(target_path, 'wb') as complete_file:
            for path in sorted(source_paths):
                with open(path, 'rb') as partial_file:
                    read_bytes = partial_file.read()
                    print(f'Read {len(read_bytes)}')
                    try:
                        decompressed_bytes = gzip.decompress(read_bytes)
                        print(
                            f'Decompressed {bytes2human(len(read_bytes))} -> {bytes2human(len(decompressed_bytes))} to {target_path}')
                        complete_file.write(decompressed_bytes)
                        print(
                            f'Wrote (decompressed) {bytes2human(len(decompressed_bytes))} to {target_path}')
                    except gzip.BadGzipFile:
                        complete_file.write(read_bytes)
                        print(f'Wrote {bytes2human(len(read_bytes))} to {target_path}')
                    finally:
                        p_bar.update(len(read_bytes))
        p_bar.refresh()


def delete_files(paths):
    for path in paths:
        os.remove(path)


def run():
    parser = get_finish_argparse()
    parsed_args = parser.parse_args(sys.argv[1:])

    source_files = parsed_args.source_files
    target_file = parsed_args.target_file
    keep = parsed_args.keep

    join_downloaded_files(source_files, target_file)
    if not keep:
        delete_files(source_files)


if __name__ == '__main__':
    run()
