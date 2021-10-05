#!/usr/bin/env python
# coding: utf-8
#!/bin/bash 
#SBATCH -J testing_barca_02 
#SBATCH -D /data/scratch/schreibef98/projects
#SBATCH -o testing_barca.%j.out 
#SBATCH --partition=gpu 
#SBATCH --nodes=1 
#SBATCH --gres=gpu:4 
#SBATCH --mem=10000M 
#SBATCH --time=200:00:00 
#SBATCH --mail-type=end 
#SBATCH --mail-user= franz.josef.schreiber@fu-berlin.de
# In[1]:


import numpy as np 
import torch 
import argparse
import sys


# In[2]:


sys.path.insert(0, '../')
from torchmdnet2.simulation_torchmdnetModels import Simulation_, PTSimulation_
from torchmdnet2.dataset.chignolin import ChignolinDataset
from torchmdnet2.simulation_utils import PT_temps

device = torch.device('cuda')


# In[3]:

def main():
    path = '/home/schreibef98/projects/temp_2'
    args = argparse.Namespace()
    args.conf=None
    args.coordinates=path+'/cln_kcenters_32clusters_coords.xtc'
    args.cutoff=None
    args.device='cuda:0'
    args.extended_system=None
    args.external = {'module': 'torchmdnet.calculators', 'embeddings': [4, 4, 5, 8, 6, 13, 2, 13, 7, 4], 'file': path+'/prot_spec_cln_epoch=23-val_loss=740.5347-test_loss=21.5826.ckpt'}
    args.forcefield=path+'/ca_priors-dihedrals_general_2xweakers.yaml'
    args.forceterms=['Bonds', 'RepulsionCG', 'Dihedrals']
    args.langevin_gamma=1
    args.langevin_temperature=350
    args.log_dir='sim_80ep_350K'
    args.minimize=None
    args.output='output'
    args.output_period=1000
    args.precision='double'
    args.replicas=32
    args.rfa=False
    args.save_period=1000
    args.seed=1
    args.steps=10000000
    args.structure=None
    args.switch_dist=None
    args.temperature = 350
    args.timestep=1
    args.topology= path+'/cln_ca_top_dih.psf'
    
    
    # In[4]:
    
    
    chignolin_dataset = ChignolinDataset('/home/schreibef98/projects/torchmd-net/datasets/chignolin_AA/')
    
    
    # In[5]:
    
    T = PT_temps(350, 500, 4)
    #T = 350
    R = 8.314462
    e = (R*T)/4184
    betas = 1/e
    
    
    # In[6]:
    
    
    n_sims = 8-1
    n_timesteps = 1000000
    save_interval = 20
    exchange_interval = 2000
    
    
    # In[7]:
    
    
    ids = np.arange(0, len(chignolin_dataset),len(chignolin_dataset)//n_sims).tolist()
    init = chignolin_dataset[ids]
    initial_coords = torch.cat([init[i].pos.reshape((1,-1,3)) for i in range(len(init))], dim=0).to(device=device)
    initial_coords.requires_grad_()
    
    sim_embeddings = torch.cat([init[i].z.reshape((1,-1)) for i in range(len(init))], dim=0).to(device=device)
    
    # overwrite initial coords for this simulation
    initial_coords = np.load(path + '/initial_coords_cgl.npy')
    initial_coords = torch.from_numpy(initial_coords)
    initial_coords.requires_grad_()
    
    # In[8]:
    
    
    # mass_scale = 418.4
    masses = list(12*np.ones(10))
    dt = 0.02045482949774598 * 10
    friction = 0.04888821
    
    sim = PTSimulation_(args, initial_coords, sim_embeddings, length=n_timesteps,
                     save_interval=save_interval, betas=betas,
                     save_potential=True, device=device, dt=dt, exchange_interval=exchange_interval,
                     log_interval=10000, log_type='write', filename='/home/schreibef98/projects/torchmd-net/datasets/trajectories/test_barca_chignolin/logs_8',
                     masses=masses, friction=friction)
    
    
    # In[ ]:
    
    
    traj = sim.simulate()
    
    
    # In[ ]:
    
    
    torch.save(traj, '/home/schreibef98/projects/torchmd-net/datasets/trajectories/test_barca_chignolin/traj_8.pt')


# In[ ]:


if __name__ == "__main__":
    main()


