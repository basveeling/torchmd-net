import imp
import h5py
import numpy as np
import os
import torch as pt
from torch_geometric.data import Data, Dataset
from tqdm import tqdm


class SPICE(Dataset):

    """
    SPICE dataset (https://github.com/openmm/spice-dataset)
    """

    HARTREE_TO_EV = 27.211386246
    BORH_TO_ANGSTROM = 0.529177

    def __init__(
        self,
        root=None,
        transform=None,
        pre_transform=None,
        pre_filter=None,
        dataset_arg=None,
    ):

        self.name = self.__class__.__name__
        self.dataset_arg = str(dataset_arg)
        super().__init__(root, transform, pre_transform, pre_filter)

        self.name = self.__class__.__name__
        self.dataset_arg = str(dataset_arg)
        super().__init__(root, transform, pre_transform, pre_filter)

        idx_name, z_name, pos_name, y_name, dy_name = self.processed_paths
        self.idx_mm = np.memmap(idx_name, mode="r", dtype=np.int64)
        self.z_mm = np.memmap(z_name, mode="r", dtype=np.int8)
        self.pos_mm = np.memmap(
            pos_name, mode="r", dtype=np.float32, shape=(self.z_mm.shape[0], 3)
        )
        self.y_mm = np.memmap(y_name, mode="r", dtype=np.float64)
        self.dy_mm = np.memmap(
            dy_name, mode="r", dtype=np.float32, shape=(self.z_mm.shape[0], 3)
        )

        assert self.idx_mm[0] == 0
        assert self.idx_mm[-1] == len(self.z_mm)
        assert len(self.idx_mm) == len(self.y_mm) + 1

    @property
    def raw_paths(self):
        return self.dataset_arg

    def sample_iter(self):

        for mol in tqdm(h5py.File(self.raw_paths).values(), desc="Molecules"):

            z = pt.tensor(mol["atomic_numbers"], dtype=pt.long)
            all_pos = (
                pt.tensor(mol["conformations"], dtype=pt.float32)
                * self.BORH_TO_ANGSTROM
            )
            all_y = (
                pt.tensor(mol["formation_energy"], dtype=pt.float64)
                * self.HARTREE_TO_EV
            )
            all_dy = (
                pt.tensor(mol["dft_total_gradient"], dtype=pt.float32)
                * self.HARTREE_TO_EV
                / self.BORH_TO_ANGSTROM
            )

            assert all_pos.shape[0] == all_y.shape[0]
            assert all_pos.shape[1] == z.shape[0]
            assert all_pos.shape[2] == 3

            assert all_dy.shape[0] == all_y.shape[0]
            assert all_dy.shape[1] == z.shape[0]
            assert all_dy.shape[2] == 3

            for pos, y, dy in zip(all_pos, all_y, all_dy):

                # Skip samples with large forces
                if dy.norm(dim=1).max() > 100:  # eV/A
                    continue

                data = Data(z=z, pos=pos, y=y.view(1, 1), dy=dy)

                if self.pre_filter is not None and not self.pre_filter(data):
                    continue

                if self.pre_transform is not None:
                    data = self.pre_transform(data)

                yield data

    @property
    def processed_file_names(self):
        return [
            f"{self.name}.idx.mmap",
            f"{self.name}.z.mmap",
            f"{self.name}.pos.mmap",
            f"{self.name}.y.mmap",
            f"{self.name}.dy.mmap",
        ]

    def process(self):

        print("Gathering statistics...")
        num_all_confs = 0
        num_all_atoms = 0
        for data in self.sample_iter():
            num_all_confs += 1
            num_all_atoms += data.z.shape[0]

        print(f"  Total number of conformers: {num_all_confs}")
        print(f"  Total number of atoms: {num_all_atoms}")

        idx_name, z_name, pos_name, y_name, dy_name = self.processed_paths
        idx_mm = np.memmap(
            idx_name + ".tmp", mode="w+", dtype=np.int64, shape=(num_all_confs + 1,)
        )
        z_mm = np.memmap(
            z_name + ".tmp", mode="w+", dtype=np.int8, shape=(num_all_atoms,)
        )
        pos_mm = np.memmap(
            pos_name + ".tmp", mode="w+", dtype=np.float32, shape=(num_all_atoms, 3)
        )
        y_mm = np.memmap(
            y_name + ".tmp", mode="w+", dtype=np.float64, shape=(num_all_confs,)
        )
        dy_mm = np.memmap(
            dy_name + ".tmp", mode="w+", dtype=np.float32, shape=(num_all_atoms, 3)
        )

        print("Storing data...")
        i_atom = 0
        for i_conf, data in enumerate(self.sample_iter()):
            i_next_atom = i_atom + data.z.shape[0]

            idx_mm[i_conf] = i_atom
            z_mm[i_atom:i_next_atom] = data.z.to(pt.int8)
            pos_mm[i_atom:i_next_atom] = data.pos
            y_mm[i_conf] = data.y
            dy_mm[i_atom:i_next_atom] = data.dy

            i_atom = i_next_atom

        idx_mm[-1] = num_all_atoms
        assert i_atom == num_all_atoms

        idx_mm.flush()
        z_mm.flush()
        pos_mm.flush()
        y_mm.flush()
        dy_mm.flush()

        os.rename(idx_mm.filename, idx_name)
        os.rename(z_mm.filename, z_name)
        os.rename(pos_mm.filename, pos_name)
        os.rename(y_mm.filename, y_name)
        os.rename(dy_mm.filename, dy_name)

    def len(self):
        return len(self.y_mm)

    def get(self, idx):

        atoms = slice(self.idx_mm[idx], self.idx_mm[idx + 1])
        z = pt.tensor(self.z_mm[atoms], dtype=pt.long)
        pos = pt.tensor(self.pos_mm[atoms], dtype=pt.float32)
        y = pt.tensor(self.y_mm[idx], dtype=pt.float32).view(
            1, 1
        )  # It would be better to use float64, but the trainer complaints
        dy = pt.tensor(self.dy_mm[atoms], dtype=pt.float32)

        return Data(z=z, pos=pos, y=y, dy=dy)
