from unittest import TestCase, main, skipUnless

from cogent3.app import align as align_app
from cogent3.app import io as io_app
from cogent3.app.io import write_db
from cogent3.util import parallel


__author__ = "Sheng Han Moses Koh"
__copyright__ = "Copyright 2007-2021, The Cogent Project"
__credits__ = ["Gavin Huttley", "Sheng Han Moses Koh"]
__license__ = "BSD-3"
__version__ = "2021.04.20a"
__maintainer__ = "Gavin Huttley"
__email__ = "Gavin.Huttley@anu.edu.au"
__status__ = "Alpha"


class MPITests(TestCase):
    basedir = "data"

    @skipUnless(parallel.USING_MPI, reason="Not using MPI")
    def test_write_db(self):
        """writing with overwrite in MPI should reset db"""
        dstore = io_app.get_data_store("data", suffix="fasta")
        members = dstore.filtered(callback=lambda x: "brca1.fasta" not in x.split("/"))
        reader = io_app.load_unaligned()
        aligner = align_app.align_to_ref()
        writer = write_db("delme.tinydb", create=True, if_exists="overwrite")
        process = reader + aligner + writer

        r = process.apply_to(
            members,
            logger=False,
            show_progress=False,
            parallel=True,
            par_kw=dict(use_mpi=True),
        )

        expect = [str(m) for m in process.data_store]
        process.data_store.close()

        # now get read only and check what's in there
        result = io_app.get_data_store("delme.tinydb")
        got = [str(m) for m in result]

        assert got == expect


if __name__ == "__main__":
    main()
