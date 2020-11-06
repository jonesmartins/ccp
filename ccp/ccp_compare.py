import argparse
import os
import sys

import tqdm

from ccp.utils import bytes2human, human2bytes


def get_compare_argparse():
    parser = argparse.ArgumentParser(
        prog='CCP Compare',
        description='Compara dois arquivos entre si.'
    )

    parser.add_argument(
        nargs=2,
        dest='files',
        type=str,
        help='Dois arquivos para comparar'
    )

    default_block_size = '1M'
    parser.add_argument(
        '-b', '--blocksize',
        dest='block_size',
        type=str,
        help=f'Tamanho da leitura em bytes (padrão: {default_block_size})',
        default=default_block_size
    )

    return parser


def compare_files(first_filename: str, second_filename: str, block_size=1024) -> bool:
    """
    Verifica se arquivos são idênticos, primeiro em tamanho e depois em conteúdo.
    :param first_filename: Caminho do 1º arquivo
    :param second_filename: Caminho do 2º arquivo
    :param block_size: Tamanho da leitura simultânea
    :return: Se idênticos, True, senão, False.
    """
    try:
        first_size = os.path.getsize(first_filename)
    except FileNotFoundError:
        print(f'Arquivo {first_filename} não foi encontrado.')
        sys.exit(1)

    try:
        second_size = os.path.getsize(second_filename)
    except FileNotFoundError:
        print(f'Arquivo {second_filename} não foi encontrado.')
        sys.exit(1)

    if first_size != second_size:
        print(
            'Arquivos têm tamanhos diferentes:\n'
            f' {first_size} B <-- {first_filename}\n'
            f' {second_size} B <-- {second_filename}\n'
        )
        return False
    else:
        print(
            f'Arquivos têm tamanho igual: '
            f'{first_size} B = {bytes2human(first_size)}'
        )

    progress_bar = tqdm.tqdm(
        total=first_size,
        desc=f"Comparando os arquivos",
        unit="B",
        unit_scale=True,
        unit_divisor=block_size
    )

    with progress_bar as p_bar:
        bytes_read = 0
        with open(first_filename, 'rb') as file_first:
            with open(second_filename, 'rb') as file_second:
                while bytes_read < first_size:
                    bytes_first = file_first.read(block_size)
                    bytes_second = file_second.read(block_size)
                    bytes_read += len(bytes_first)
                    if bytes_first != bytes_second:
                        print(f'Diferença encontrada no byte {bytes_read}.')
                        return False
                    p_bar.update(n=len(bytes_first))
        p_bar.refresh()

    print('Os arquivos são idênticos!')
    return True


def run():
    parser = get_compare_argparse()
    parsed_args = parser.parse_args(sys.argv[1:])

    first_file, second_file = parsed_args.files
    block_size = human2bytes(parsed_args.block_size)

    compare_files(first_file, second_file, block_size=block_size)


if __name__ == '__main__':
    run()
