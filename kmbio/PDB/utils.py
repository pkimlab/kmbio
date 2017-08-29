import bz2
import contextlib
import gzip
import itertools
import logging
import lzma
import tempfile
import urllib.request

from kmbio.PDB import Atom, DisorderedAtom
from kmbio.PDB.core.entity import Entity
from kmbio.PDB.exceptions import PDBException

logger = logging.getLogger(__name__)
ENTITY_LEVELS = ["A", "R", "C", "M", "S"]


def _unfold_disordered_atom(atom):
    if isinstance(atom, DisorderedAtom):
        return list(atom._child_dict.values())
    else:
        return [atom]


def allequal(s1, s2, atol=1e-3):
    # Check if atoms are equal
    if isinstance(s1, (Atom, DisorderedAtom)) and isinstance(s2, (Atom, DisorderedAtom)):
        atoms_1 = _unfold_disordered_atom(s1)
        atoms_2 = _unfold_disordered_atom(s2)
        for atom_1 in atoms_1:
            for atom_2 in atoms_2:
                if atom_1.atoms_equal(atom_2, atol):
                    return True
        logger.debug('Atoms not equal: (%s, %s) (%s, %s)', atoms_1, [a.coord for a in atoms_1],
                     atoms_2, [a.coord for a in atoms_2])
        return False
    # Check if object types are the same
    if type(s1) != type(s2):
        raise Exception(
            "Can't compare objects of different types! ({}, {})".format(type(s1), type(s2)))
    # Check if lengths are the same
    lengths_equal = len(s1) == len(s2)
    if not lengths_equal:
        logger.error("Lengths are different: %s, %s", len(s1), len(s2))
        return False
    # Recurse
    return all(allequal(so1, so2, atol) for (so1, so2) in zip(s1.values(), s2.values()))


def uniqueify(items):
    """Return a list of the unique items in the given iterable.

    Order is preserved.
    """
    _seen = set()
    return [x for x in items if x not in _seen and not _seen.add(x)]


def sort_structure(structure):
    structure._child_list.sort(key=lambda m: m.id)
    for model in structure.values():
        model._child_list.sort(key=lambda c: c.id)
        for chain in model.values():
            chain._child_list.sort(key=lambda r: r.id[1])
            for residue in chain.values():
                residue._child_list.sort(key=lambda a: a.id)


class uncompressed:
    @staticmethod
    def open(*args, **kwargs):
        return open(*args, **kwargs)

    @staticmethod
    def decompress(data):
        return data


def anyzip(filename):
    if filename.endswith('.gz'):
        return gzip
    elif filename.endswith('.bz2'):
        return bz2
    elif filename.endswith('.xz'):
        return lzma
    else:
        return uncompressed


@contextlib.contextmanager
def open_url(url):
    if url.startswith(('ftp:', 'http:', 'https:', )):
        with tempfile.TemporaryFile('w+t') as fh:
            logger.debug("URL: %s", url)
            with urllib.request.urlopen(url) as ifh:
                data_bin = ifh.read()
                data_txt = anyzip(url).decompress(data_bin).decode('utf-8')
                fh.write(data_txt)
            fh.seek(0)
            yield fh
    else:
        with anyzip(url).open(url, mode='rt') as fh:
            yield fh


def get_unique_parents(entity_list):
    """Translate a list of entities to a list of their (unique) parents."""
    unique_parents = set(entity.parent for entity in entity_list)
    return list(unique_parents)


def unfold_entities(entity_list, target_level):
    """Unfold entities list to a child level (e.g. residues in chain).

    Unfold a list of entities to a list of entities of another
    level.  E.g.:

    list of atoms -> list of residues
    list of modules -> list of atoms
    list of residues -> list of chains

    o entity_list - list of entities or a single entity
    o target_level - char (A, R, C, M, S)

    Note that if entity_list is an empty list, you get an empty list back:

    >>> unfold_entities([], "A")
    []

    """
    if target_level not in ENTITY_LEVELS:
        raise PDBException("%s: Not an entity level." % target_level)
    if entity_list == []:
        return []
    if isinstance(entity_list, (Entity, Atom)):
        entity_list = [entity_list]

    level = entity_list[0].level
    if not all(entity.level == level for entity in entity_list):
        raise PDBException("Entity list is not homogeneous.")

    target_index = ENTITY_LEVELS.index(target_level)
    level_index = ENTITY_LEVELS.index(level)

    if level_index == target_index:  # already right level
        return entity_list

    if level_index > target_index:  # we're going down, e.g. S->A
        for i in range(target_index, level_index):
            entity_list = itertools.chain.from_iterable(entity_list)
    else:  # we're going up, e.g. A->S
        for i in range(level_index, target_index):
            # find unique parents
            _seen = set()
            entity_list = [
                entity.parent for entity in entity_list
                if entity.parent.id not in _seen and not _seen.add(entity.parent.id)
            ]
    return list(entity_list)
