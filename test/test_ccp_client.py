import unittest
import os
import shutil

from ccp_client import (
    is_valid_ipv4_address,
    is_valid_ipv6_address,
    parse_address,
    validate_ip,
    validate_port,
    validate_path,
    get_abspath
)


class ClientTestCase(unittest.TestCase):

    def test_parse_address(self):
        pass

    def test_is_valid_ipv4_address(self):
        pass

    # def test_is_valid_ipv6_address(self):
    #     self.assertEquals(validate_ip('0.0.0.0'), '0.0.0.0')
    #     self.assertEquals(validate_ip('255.255.255.255'), '255.255.255.255')
    #     self.assertEquals(validate_ip('127.0.0.1'), '127.0.0.1')
    #     self.assertRaises(ValueError, validate_ip, '127.1')
    #     self.assertRaises(ValueError, validate_ip, '255.')
    #     self.assertRaises(ValueError, validate_ip, '')
    #     self.assertEquals(validate_ip('localhost'), 'localhost')

    # def test_validate_port(self):
    #     self.assertRaises(ValueError, validate_port, -1)
    #     self.assertEqual(validate_port(0), 0)
    #     self.assertEqual(validate_port(2**16 - 1), 2**16 - 1)
    #     self.assertRaises(ValueError, validate_port, 2**16)
    #     self.assertRaises(ValueError, validate_port, '10')

    def test_validate_path(self):
        # Inicia diretório de testes.
        if not os.path.exists('tmp'):
            os.mkdir('tmp')

        os.chdir('tmp')
        if not os.path.exists('directory'):
            os.mkdir('directory')

        open('directory/file', 'w').close()

        # TESTES (Em tmp)

        path = ''  # Diretório atual
        abs_path = get_abspath(path)
        self.assertRaises(FileExistsError, validate_path, abs_path)

        path = '.'  # Diretório atual
        abs_path = get_abspath(path)
        self.assertRaises(FileExistsError, validate_path, abs_path)

        path = '..'  # Diretório superior
        abs_path = get_abspath(path)
        self.assertRaises(FileExistsError, validate_path, abs_path)

        path = '/directory'  # Diretório inferior (nome inválido)
        abs_path = get_abspath(path)
        self.assertRaises(IsADirectoryError, validate_path, abs_path)

        path = 'directory/'  # Diretório inferior (nome válido)
        abs_path = get_abspath(path)
        self.assertRaises(FileExistsError, validate_path, abs_path)

        path = 'directory'  # Diretório inferior (nome válido)
        abs_path = get_abspath(path)
        self.assertRaises(FileExistsError, validate_path, abs_path)

        path = '../directory'  # Não existe.
        abs_path = get_abspath(path)
        self.assertRaises(FileNotFoundError, validate_path, abs_path)

        path = '/file'  # Arquivo no diretório atual (nome inválido)
        abs_path = get_abspath(path)
        self.assertRaises(IsADirectoryError, validate_path, abs_path)

        path = 'file/'  # Arquivo no diretório atual (nome inválido)
        abs_path = get_abspath(path)
        self.assertRaises(IsADirectoryError, validate_path, abs_path)

        path = 'file'  # Arquivo no diretório atual (nome válido)
        abs_path = get_abspath(path)
        self.assertEqual(validate_path(abs_path), abs_path)


        # Apaga diretório e volta às condições anteriores.

        os.chdir('..')
        shutil.rmtree('tmp')




if __name__ == '__main__':
    unittest.main()
