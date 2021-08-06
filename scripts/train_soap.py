import sys
import os
import torch
import argparse
import yaml
import subprocess
from time import ctime

import pytorch_lightning as pl
from pytorch_lightning.callbacks import LearningRateMonitor, EarlyStopping
from pytorch_lightning.callbacks.model_checkpoint import ModelCheckpoint
from pytorch_lightning.plugins import DDPPlugin


sys.path.insert(0,'/home/musil/git/torchmd-net/')

from torchmdnet2.utils import LoadFromFile, save_argparse, Args
from torchmdnet2.models import MLPModel
from torchmdnet2.dataset import DataModule

from pytorch_lightning.utilities.cli import LightningCLI

from pytorch_lightning.accelerators import GPUAccelerator, CPUAccelerator
from pytorch_lightning.plugins import NativeMixedPrecisionPlugin, DDPPlugin

# class MyLightningCLI(LightningCLI):
#     def instantiate_classes(self):
#         self.config_init = self.parser.instantiate_classes(self.config)
#         self.datamodule = self.config_init.get('data')
#         self.model = self.config_init['model']

#         if isinstance(self.config_init['trainer'].get('profiler'), pl.profiler.PyTorchProfiler):
#             init_args = self.config['trainer']['profiler']['init_args']
#             init_args.update(with_stack=True, export_to_flame_graph=True)
#             self.config_init['trainer']['profiler'] = pl.profiler.PyTorchProfiler(**init_args)

#         self.instantiate_trainer()

if __name__ == "__main__":

    git = {
        'log': subprocess.getoutput('git log --format="%H" -n 1 -z'),
        'status': subprocess.getoutput('git status -z'),
    }
    print('Start: {}'.format(ctime()))


    # accelerator = CPUAccelerator(
    #     precision_plugin=NativeMixedPrecisionPlugin(),
    #     training_type_plugin=DDPPlugin(find_unused_parameters=False),
    # )

    cli = LightningCLI(MLPModel, DataModule, save_config_overwrite=True,
                # trainer_defaults={'accelerator':accelerator}
    )
    
    print(cli.trainer.checkpoint_callback.best_model_path)

    print('Finish: {}'.format(ctime()))
