try:
    from mmtf import fetch, parse
except ImportError:
    from Bio import MissingPythonDependencyError
    raise MissingPythonDependencyError("Install mmtf to use kmbio.PDB.mmtf "
                                       "(e.g. pip install mmtf-python)")

from kmbio.PDB.Parser import Parser
from kmbio.PDB.mmtf.DefaultParser import StructureDecoder


def get_from_decoded(decoder):
    structure_decoder = StructureDecoder()
    decoder.pass_data_on(structure_decoder)
    return structure_decoder.structure_bulder.get_structure()


class MMTFParser(Parser):
    """Class to get a BioPython structure from a URL or a filename."""

    @staticmethod
    def get_structure(filename, structure_id=None):
        """Get a structrue from a file - given a file path.

        :param file_path: the input file path
        :return the structure
        """
        decoder = parse(filename)
        structure = get_from_decoded(decoder)
        if structure_id is not None:
            structure.id = structure_id
        return structure

    @staticmethod
    def get_structure_from_url(pdb_id):
        """Get a structure from a URL - given a PDB id.

        :param pdb_id: the input PDB id
        :return the structure
        """
        decoder = fetch(pdb_id)
        return get_from_decoded(decoder)