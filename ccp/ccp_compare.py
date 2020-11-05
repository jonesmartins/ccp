import argparse
import os
from typing import List
import tqdm
import gzip
import sys


def get_compare_argparse():
    parser = argparse.ArgumentParser(
        prog='CCP Compare',
        description='Compara arquivo original com arquivo recebido.'
    )

    parser.add_argument(
        '-s', '--source',
        required=True,
        dest='source_file',
        type=str,
        help='Arquivos fonte.'
    )

    parser.add_argument(
        '-t', '--target',
        required=True,
        dest='target_file',
        type=str,
        help='Arquivo destino'
    )

    return parser

import os
def compare_files(source_file, target_file):
    source_size = os.path.getsize(source_file)
    target_size = os.path.getsize(target_file)
    if source_size != target_size:
        print(
            'Arquivos têm tamanhos diferentes:\n'
            f' [{source_file}] --> {source_size}\n'
            f' [{target_file}] --> {target_size}\n'
        )
        return False

    buffer_size = 1024
    progress_bar = tqdm.tqdm(
        total=target_size,
        desc=f"Comparando os arquivos:\n - {source_file}\n - {target_file}.",
        unit="B",
        unit_scale=True,
        unit_divisor=buffer_size
    )

    with progress_bar as p_bar:
        bytes_read = 0
        with open(target_file, 'rb') as tf:
            with open(source_file, 'rb') as sf:
                while bytes_read < target_size:
                    sbytes = sf.read(min(target_size - bytes_read, buffer_size))
                    tbytes = tf.read(min(target_size - bytes_read, buffer_size))
                    bytes_read += len(sbytes)
                    # print(f'Li {len(sbytes)} bytes. Faltam {target_size - bytes_read}')
                    if sbytes != tbytes:
                        print(f'Diferença encontrada no byte {bytes_read}.')
                        return False

                    p_bar.update(n=len(sbytes))
        p_bar.refresh()

    print('Arquivos são iguais!')
    return True


def run():
    parser = get_compare_argparse()
    parsed_args = parser.parse_args(sys.argv[1:])

    source_file = parsed_args.source_file
    target_file = parsed_args.target_file

    compare_files(source_file, target_file)


if __name__ == '__main__':
    run()