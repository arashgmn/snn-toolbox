#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
These utilitiy functions transform the indicies of neurons to their coordinates
back and forth. A useful little script to have.
"""
import glob
import os
osjoin = os.path.join # an alias for convenient

import pickle
import numpy as np
from scipy import sparse
from collections import defaultdict

import brian2 as b2
from brian2 import mV, nS, pA, ms, second

from pdb import set_trace

def coord2idx(coords, pop):
    """
    Transforms the coordinates to the indices for a given population.
    
    :param coords: coordinates of n neuron 
    :type coords: numpy array of size (n,2)
    :param pop: population object 
    :type pop: Brian's NetworkGroup object
    :return: array of indicies of length N of type int
    :rtype: numpy array 

    """
    gs = int(np.sqrt(len(pop))) # gridsize
    
    coords = np.asarray(coords).reshape(-1,2)
    idxs = coords[:,1]*gs + coords[:,0]
    return idxs
    
def idx2coords(idxs, net):
    """
    Transforms the a list of indices of the given population to coordinates.
    
    :param idxs: list or array of coordinates. i.e., [(x1,y1), (x2,y2), ...]
    :type idxs: list or numpy array
    :param net: population object 
    :type net: Brian's NetworkGroup object
    :return: array of coordinates of size (N,2) of type int
    :rtype: numpy array

    """
    gs = int(np.sqrt(len(net))) # gridsize
    
    idxs = np.asarray(idxs)
    y,x = np.divmod(idxs, gs)
    coords = np.array([x,y]).T
    return coords


def get_syn_id_from_coord(sim, pop, coords, pathway):
    idxs = coord2idx(coords, sim.pops[pop])
    nconn = sim.conns_cfg[pathway]['ncons']
    # syn_idxs = []
    # set_trace()
    # for idx in idxs:
    #     for syn_idx in range(idx*nconn, (idx+1)*nconn):
    #         syn_idxs.append(syn_idx)
    syn_idxs = [syn_idx for idx in idxs for syn_idx in range(idx*nconn, (idx+1)*nconn)]
    
    return syn_idxs
    

def get_spike_train(sim, mon_name, dense=True, idx=True):
    mon_dict = aggregate_mons(sim, mon_name, SI=True)
    pop_name = mon_name.split('_')[-1]
    
    ts = mon_dict['t']
    ts -= ts.min()
    idxs = mon_dict['i'] # doesn't contains all indices necessarily
    
    tmax = ts.max()
    nidxs = sim.pops[pop_name].gs**2  # number of all neurons
    ntime = int((tmax)//sim.dt) + 1
    
    t = np.linspace(0, tmax, ntime, endpoint=True)
    spk_trn = np.zeros((nidxs, ntime), dtype=int)
    for idx in sorted(set(idxs)):
        indices = (ts[idxs==idx]//(sim.dt/b2.second)).astype(int)
        spk_trn[idx, indices] += 1
    
    return t, spk_trn
    
        
def aggregate_mons_from_disk(path, mon_name):
    
    # data_path = sim.data_path
    # name_pattern = sim.name+ '_'+ mon_name+'_*.dat'
    
    name_pattern = 'random_name_'+ mon_name+'_*.dat'
    files_list = sorted(glob.glob( osjoin(path, name_pattern)))
    mon = {}
    for file in sorted(files_list):
        with open(file, 'rb') as f:
            data = pickle.load(f)
            
            for key, value in data.items():
                if key in mon:
                    mon[key] = np.append(mon[key], value)
                else:
                    mon[key] = value
            # ts.append(list(data['t']/ms))
            
            # idxs.append(list(data['i']))
    
    # if not SpikeMonitor, then we have to reshape the monitors
    if 'syn' in mon_name:
        for key, value in mon.items():
            if key not in ['t', 'N']:
                mon[key] = value.reshape(len(mon['t']),-1)
                
    # if SI:
    #     mon['t'] /= (1*second)
    # # idxs = np.concatenate(idxs)
    # # ts = np.concatenate(ts)

    return mon

    
    
def aggregate_mons(sim, mon_name, SI=False):
    """
    Aggregates the indices and timings of the spiking events from disk.
    
    :param mon_name: The name of monitor of interest
    :type mon_name: str
    :return: tuple of indices and times (in ms)
    :rtype: (array of ints, array of floats)

    """
    
    data_path = sim.data_path
    name_pattern = sim.name+ '_'+ mon_name+'_*.dat'
    
    files_list = sorted(glob.glob( osjoin(data_path, name_pattern)))
    mon = {}
    for file in sorted(files_list):
        with open(file, 'rb') as f:
            data = pickle.load(f)
            
            for key, value in data.items():
                if key in mon:
                    mon[key] = np.append(mon[key], value)
                else:
                    mon[key] = value
            # ts.append(list(data['t']/ms))
            
            # idxs.append(list(data['i']))
    
    # if not SpikeMonitor, then we have to reshape the monitors
    if 'syn' in mon_name:
        for key, value in mon.items():
            if key not in ['t', 'N']:
                mon[key] = value.reshape(len(mon['t']),-1)
                
    # if SI:
    #     mon['t'] /= (1*second)
    # # idxs = np.concatenate(idxs)
    # # ts = np.concatenate(ts)

    return mon


def stimulator(sim, stim_cfgs):
    stims = {}
    for stim_id, stim_cfg in stim_cfgs.items():
        domain = stim_cfg['domain']
        ampli = stim_cfg['domain'] 
        pop = stim_id.strip('_')[0] # assuming ids like I_1, I_2
        gs = sim.pops[pop].gs 
        
        # finding domain
        if domain['type']=='random':
            idxs = np.random.randint(0, gs**2, round(gs**2 * domain['p']))
        else:
            if domain['type']=='xy':
                x = np.arange(domain['x_min'], domain['x_max'])
                y = np.arange(domain['y_min'], domain['y_max'])
                x,y = np.meshgrid(x,y)
                coords = np.array(list(zip(x.ravel(),y.ravel())))
            
            elif domain['type']=='r':
                coords = []
                for x in range(-round(domain['r'])-1, round(domain['r'])+1):
                    for y in range(-round(domain['r'])-1, round(domain['r'])+1):
                        if x**2 + y**2 <= domain['r']**2:
                            coords.append( [(x + domain['x0'])%gs, 
                                            (y + domain['y0'])%gs] ) 
                coords = np.array(coords).reshape(-1,2)
            
            idxs = coord2idx(coords, sim.pops[pop])
            

        # finding amplitude
        if stim_cfg['type']=='const':
            I_stim = stim_cfg['I_stim']
            # b2.TimedArray([stim_cfg['I_stim']]*pA,
            #                                dt=sim.pops[pop].clock.dt)
        else:
            raise NotImplementedError('Only constant stimulation is supported now.')
        
        stims[stim_id] = {'idxs': idxs, 'I_stim': I_stim}
    
    return stims


def get_line_idx(x0, y0, c, pop, eps=2):
    xs = np.arange(0, pop.gs//2) #only half of plane will be modified
    
    coords = []
    for x in xs:
        y_center = int(round(x*c))
        for y in range(y_center-eps-1, y_center+eps+1):
            if y**2 <= eps**2:
                coords.append([(x+x0) % pop.gs, (y+y0) % pop.gs])
    coords = np.unique(coords, axis=0)
    idxs = coord2idx(coords, pop)
    return idxs, coords
    
 
    
def compute_eff_anisotropy(s_coord, t_coords, gs):
    """Efference anisotropy computes the radius and angle of the averagte 
    pre to post vector."""
    # post_cntr = t_coords-s_coord # centers
    # post_cntr = (post_cntr + gs/2) % gs- gs/2 # make periodic
    posts_centered = compute_precentric_posts(t_coords, s_coord, gs )
    
    # mean = np.arctan2(post_cntr[:,1].mean(), post_cntr[:,0].mean())
    phis = np.arctan2(posts_centered[:,1], posts_centered[:,0])
    rs = np.sqrt(posts_centered[:,1]**2 + posts_centered[:,0]**2)
    
    return estimate_order_parameter(phis, rs)
    

def compute_aff_anisotropy(t_coord, s_coords, gs):
    """Efference anisotropy computes the radius and angle of the average post
    to pre vector."""
    
    # post_cntr = compute_precentric_posts(t_coords, s_coord, gs )
    pres_centered = compute_postcentric_pres(s_coords, t_coord, gs)
    
    # mean = np.arctan2(post_cntr[:,1].mean(), post_cntr[:,0].mean())
    phis = np.arctan2(pres_centered [:,1], pres_centered [:,0])
    rs = np.sqrt(pres_centered [:,1]**2 + pres_centered [:,0]**2)
    
    return estimate_order_parameter(phis, rs)

    
    
def phase_estimator(idxs, ts, dt):
    t = np.linspace(0, ts.max(), int(ts.max()//dt) + 1)
    phis = np.zeros(shape= (len(set(idxs)), len(t)))
    
    for num, idx in enumerate(sorted(set(idxs))):
        phi = np.zeros_like(t)
        
        t_spk = sorted(ts[idxs == idx])
        
        if len(t_spk)>1:
            t_dif = np.diff(t_spk)
            
            head = int(t_spk[0]//dt)
            
            for chunk_id, dif in  enumerate(t_dif):
                # set_trace()
                chunk_len = int(dif//dt)
                phi[ head: head + chunk_len] = np.linspace(0, 2*np.pi, chunk_len) 
                head += chunk_len
            
            phis[num] = phi
    
    return t, phis



def estimate_order_parameter(phis, k=None, order=1):

    if type(k)==type(None):
        k = np.ones(phis.shape[0])
    else:
        assert len(k)==phis.shape[0]
        
    R = np.average(np.exp(1j*phis*order), weights=k, axis=0)
    return np.abs(R), np.angle(R)





def make_circular(r, r_max):
    return 2*np.pi*r/r_max

def make_planar(angle, r_max):
    return angle/(2*np.pi) * r_max
    
def plane2torus(p_coords, gs, method='lin'):
    #set_trace()
    # coords must have the shape (n_coords,2)
    assert p_coords.shape[1] == 2 # shape must be 
    
    t_coords = np.zeros((p_coords.shape[0],4), dtype=float)
    phi, psi = make_circular(p_coords, gs).T
    
    if method=='tri':
        # morphing x
        t_coords[:,0] = np.sin(phi)
        t_coords[:,1] = np.cos(phi)
        
        # morphing y
        t_coords[:,2] = np.sin(psi)
        t_coords[:,3] = np.cos(psi)
    
    elif method=='lin':
        for id_, ang in enumerate([phi, psi]):
            # Sin component
            choice0 = ang/(np.pi/2)     
            choice1 = -ang/(np.pi/2) + 2
            choice2 = ang/(np.pi/2) - 4
            
            index = np.zeros(ang.shape, dtype=int)
            index[ang <= np.pi/2] = 0
            index[(np.pi/2 < ang) & (ang <= 3*np.pi/2)] = 1
            index[ang > 3*np.pi/2] = 2
            
            t_coords[:,2*id_] = np.choose(index, [choice0, choice1, choice2])
                
            # cos component
            choice0 = -ang/(np.pi/2) + 1     
            choice1 = +ang/(np.pi/2) - 3
            
            index = np.zeros(ang.shape, dtype=int)
            index[ang <= np.pi] = 0
            index[ang > np.pi] = 1
            
            t_coords[:,2*id_ +1] = np.choose(index, [choice0, choice1])
            
    else:
        raise NotImplementedError("At the moment only triangulumetric and linear morphing is possible.")
    
    return t_coords


def torus2plane(t_coords, gs, method='tri'):
    # coords must have the shape (n_coords,4)
    assert t_coords.shape[1] == 4 # (s_x, c_x, s_y, c_y)
    
    p_coords = np.zeros((t_coords.shape[0],2), dtype=float)
    
    if method=='tri':
        phi = np.arctan2(t_coords[:,0], t_coords[:,1])
        psi = np.arctan2(t_coords[:,2], t_coords[:,3])
        
        p_coords[:,0] = make_planar(phi, gs)
        p_coords[:,1] = make_planar(psi, gs)
    else:
        raise NotImplementedError("At the moment only triangular morphing is possible.")
    
    return np.round(p_coords).astype(int)
    
        
def balance_dist(t0, t_min=0, t_max=1):
    t = t0-t0.min()
    t /= t.max()
    
    percents = np.linspace(0,1, len(t))
    sorted_idx = np.argsort(t)
    
    for idx, val in enumerate(percents):
        t[sorted_idx[idx]] = val
        
    t = t_min + (t_max - t_min) * t
    # n_quantiles = len(set(t))
    # quant_size = len(t)//n_quantiles 
    # print(n_quantiles, quant_size)
    
    # for quant_idx, quant_val in enumerate(np.linspace(t_min, t_max, n_quantiles+1)):
    #     t[ sorted_idx[quant_idx*quant_size : (quant_idx+ 1)*quant_size] ] = quant_val
    
    return t
    
    # sorted_idx = np.argsort(phis)
    # max_val = gs * 2
    # idx = len(phis) // max_val
    # for ii, val in enumerate(range(max_val)):
    #     phis[sorted_idx[ii * idx:(ii + 1) * idx]] = val
    # phis = (phis - gs) / gs
    
    # # to push between -pi and pi
    # phis -= np.min(phis)
    # phis *= 2*np.pi/(np.max(phis)+1e-12)
    # phis -= np.pi

def get_anisotropic_U(sim, syn_name, Umax):
    syn = sim.syns[syn_name]
    conn_cfg = sim.conn_cfg[syn_name]
    lscp = sim.lscp[syn_name]['phi']
    lscp = Umax*(lscp- lscp.min())/(lscp.max()-lscp.min())
    
    Us = np.zeros(len(syn))
    for idx_pre in sorted(set(sim.syns[syn_name].i)):
        syn_idx = syn["i=={}".format(idx_pre)]._indices()
        U_mean = lscp[idx_pre]
        alpha = 2
        beta = alpha*(1./(U_mean+1e-12) - 1)
        Us[syn_idx] = np.random.beta(alpha, beta, size= len(syn_idx))
    return Us


def get_inward_angles(sim, w_name, save_path):
    
    for syn in sim.syns:
        # w = sparse.load_npz(osjoin(sim.res_path, 'w_'+sim.name+'.npz'))
        # npres = []
        # idxs = np.zeros(w.nnz,2)
        dists = np.zeros(syn.target.N)
        angles = np.zeros(syn.target.N)
    
        # for post_idx in range(w.shape[1]):
        #     pre_reps = w.getcol(post_idx).data # n connections with the same pre-post
        #     pre_idxs = w.getcol(post_idx).nonzero()[0].tolist() # unique pres
        #     pre_idxs = np.repeat(pre_idxs, pre_reps) # non-unique_pres
        
        for post_idx in range(syn.target.N):
            rel_dist = get_pre_rel_locs(syn, post_idx)
            
            
        

def get_post_idxs(syn, pre_idx):
    return syn.j["i=={}".format(pre_idx)]
    
def get_pre_idxs(syn, post_idx):
    return syn.i["j=={}".format(post_idx)]
    
def get_post_locs(syn, pre_idx):
    post_idxs = get_post_idxs(syn, pre_idx)
    return idx2coords(post_idxs, syn.target)

def get_pre_locs(syn, post_idx):
    pre_idxs = get_pre_idxs(syn, post_idx)
    return idx2coords(pre_idxs, syn.source)


def compute_precentric_posts(t_locs, s_loc, gs):
    """relative position of post synapses w.r.t. a pre synapse"""
    
    tmp = t_locs - s_loc
    return (tmp +gs/2) % gs - gs/2

def compute_postcentric_pres(s_locs, t_loc, gs):
    """relative position of pre synapses w.r.t. a psot synapse."""
    
    # I am not sure if the second line works if I compute the "post to pre" 
    # vector. So instead I compute "pre to post" vectors, and then negate.
    tmp = t_loc - s_locs
    tmp = (tmp +gs/2) % gs - gs/2
    return -tmp 


def get_post_rel_locs(syn, pre_idx):
    s_loc = idx2coords(pre_idx, syn.source).astype(float)
    s_loc*= syn.target.gs/syn.source.gs*1.
    s_loc = np.round(s_loc).astype(int)
    
    # alternative way
    # t_locs = get_post_locs(syn, pre_idx)
    # t_locs = compute_precentric_posts(t_locs, s_loc, syn.target.gs)
    
    t_locs = get_post_locs(syn, pre_idx) - s_loc
    t_locs = (t_locs + syn.target.gs/2) % syn.target.gs - syn.target.gs/2
    return t_locs


def get_pre_rel_locs(syn, post_idx):
    t_loc = idx2coords(post_idx, syn.target).astype(float)
    t_loc*= syn.source.gs/syn.target.gs*1.
    t_loc = np.round(t_loc).astype(int)
    
    # alternative way
    s_locs = get_pre_locs(syn, post_idx)
    s_locs = compute_postcentric_pres(s_locs, t_loc, syn.source.gs)
    return s_locs




def get_local_lscp(idx, lscp):
    local_lscp = {}
    
    for k,v in lscp.items():
        if type(v)== type(np.array([])):
            local_lscp[k] = v[idx]
        else:
            local_lscp[k] = v
            
    return local_lscp 

def dict_extractor(key, var):
    """
    Sometimes its nice to just check if a specific key exists in a config.
    This does that as a generator. Kudos goes to:
        https://stackoverflow.com/questions/9807634/find-all-occurrences-of-a-key-in-nested-dictionaries-and-lists
    """
    if hasattr(var,'items'):
        for k, v in var.items():
            if k == key:
                yield v
            if isinstance(v, dict):
                for result in dict_extractor(key, v):
                    yield result
            elif isinstance(v, list):
                for d in v:
                    for result in dict_extractor(key, d):
                        yield result