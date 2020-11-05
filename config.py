# coding=utf-8

import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(threadName)s | %(message)s'
)


# -------- COMANDOS -------- #

# Comandos de entrada (servidor)
COMMANDS_SHUTDOWN = frozenset(['desligar', 'desliga'])
COMMANDS_SHUTDOWN_CONFIRM = frozenset(['s', 'sim'])
COMMANDS_SHUTDOWN_DENY = frozenset(['', 'n', 'não', 'nao'])

