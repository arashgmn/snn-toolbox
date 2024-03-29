    #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simulations are configured via nested dictionaries. We treat the population 
and pathway configurations differently, both in the synopsis of the functions 
and their functionalities. In what follows, the structure of each configuration
is explained. In addition, one can use``Configs`` module, which provides 
ready-to-use configurations for simulations.


==========================
Population's configuration
==========================

Populations are identified by a capital character as their name (like ``"P"``) 
and must be set up as follows:


.. code-block:: python

   "P": {
         'gs': ..., 
         'noise': {'mu': ..., 'sigma': ..., 'noise_dt': ...},
         'cell': {'type': 'LIF', 
         'thr': ..., 'ref': ..., 'rest': ...,
         'tau': ..., 'C': ...}
        }


with 

#. ``gs``: grid size (int)
#. ``mu`` and ``sigma``: the background current amplitude in standard deviation as Brian quantities with current unit
#. ``noise_dt``: the time scaling of the Wiener process. Please refer to :ref:`equations:Noise scaling` for details.
#. ``type``: fixed -- for the moment only LIF neuron is possible
#. ``thr`` and ``rest``: threhold and resting potentials as Brian quantities with voltage unit
#. ``ref``: refractory period as a Brian quantity with time unit
#. ``tau``: membrane time scale as a Brian quantity with time unit
#. ``C``: membrane capacitance as a Brian quantity with capacitance unit


=======================
Pathways' configuration
=======================

Pathways are identified by two-character names (like ``"PQ"``) that specifies 
the source (P) and target (Q) populations (note the ordering). Each pathway 
must have be configured similar to the following form:

.. code-block:: python

    {'ncons': ..., 'self_link': False, 
     'profile': {...},
     'anisotropy': {...},
    }


#. ``ncons``: number of connections from each source neuron to the target population (int)
#. ``self_link``: if self-link is allowed; only important if source and target are the same object. In other words, pathway is recurrent. (bool)


~~~~~~~
Profile
~~~~~~~
``profile`` determines the `radial` profile of the connectivity which accepts a
distribution, or ``None``, i.e., no spatial structure (Erdős–Rényi network).
Some examples are provided below:
    
.. code-block:: python

    {
     ...
     
     'profile': {'type':'Gamma', 'params': {'theta': ..., 'kappa': ...} },  
     'profile': {'type':'Gaussian', 'params': {'std': ...}, gap = ... }, 
     'profile': None,
     
     ...
    }
    

#. ``type``: either ``"Gamma"`` or ``"Gaussian"`` (str)
#. ``params``: distribution parameters (float). Refer, to the documentation of 
   each distribution.
#. ``gap``: a customary float, preventing connections with distance less than
   the prescribed value. 
   
   
.. note::
    Please refer to the :refer:`anisofy:Isotropic connectivity profile` for a discussion
    on the ``gap``.


~~~~~~~
Synapse
~~~~~~~
``synapse`` are specified via the following structures:
    
.. code-block:: python

    {
     ...
     
     'synapse': {'type':'alpha_jump', 'params': {'J': ..., 'delay':..., 'tau': ...}}, # usually we use this
     'synapse': {'type':'alpha_current', 'params': {'J': ..., 'delay': ..., 'tau': ...}}, # or this
     'synapse': {'type':'alpha_conductance', 'params': {'J': ..., 'delay': ..., 'tau': ..., 'Erev': ...}}, # but not this (NOT TESTED!)
     'synapse': {'type':'tsodyks-markram_jump', 'params': {'J': ..., 'delay': ...,  'tau_f': ..., 'tau_d': ..., 'U':...}},
     ...
    }
    
    
#. ``type``: encodes both synpatic *kernel* and *model* in form of 
   ``<kernel>_<method>``. Please refer to  :ref:`equations:Synapse equations` 
   for possible values of kernels and models.
#. ``params``: 

   * ``tau``: synaptic timescales as a Brian time quantity (for exp, and alpha kernels)
   * ``tau_r`` and ``tau_d``: rise and decay timescales as a Brian time quantity (for biexp kernel)
   * ``delay``: synaptic delay  as a Brian time quantity
   * ``J``: synaptic qunatal with unit volt, ampere, or siemens for synapse
     models ``jump``, ``current`` or ``conductance`` respectively (c.f. :ref:`equations:Synapse equations` ).
     Note that the sign will determine the polarity of the projection (inhibitory or excitatory).
   * ``Erev``: the reversal potential for conductance-based synapse as a Brian quantity of unit volt


~~~~~~~~~~
Anisotropy
~~~~~~~~~~
The ``anisotropy`` provides a pool of parameters that can be used for enforcing
anisotropy on connectivity or synaptic properties. Whether or not such 
parameters are used in making things anisotropic, depends if the  configuration 
dictionary has ``synaptic`` and ``connectivity`` keys or not. The follwing 
examples illustrate the usage:

.. code-block::python

    {
     ...
     
     'anisotropy': None, # everything will be isotropic
     'anisotropy': {'connectivity': ..., 'params': {'r': ..., 'phi': ..., }}, # only connectivity will be anisotropic
     'anisotropy': {'synaptic': ..., 'params': {'r': ..., 'phi': ..., pmin: ..., pmax: ...}}, # only synaptic parameters will be anisotropic
     'anisotropy': {'connectivity': ..., 'synaptic': ..., 'params': {'r': ..., 'phi': ..., pmin: ..., pmax: ... }}, # both will be anisotropic
     
     ...
     }
     

Note that the parameter pool ``params`` can be used for both synaptic and 
connecitivity anistropy, depending on the method in use. c.f. :ref:`landscape` 
for details on the anisotropy methods. 

.. note::
    Ensure you understand the anisotropic methods first. They require parameters
    that must be provided in the ``params`` pool. If not given, an error will 
    be raised. 
    
The entries in the parameters pool depend on the anisotropy method in use. c.f.
:ref:`landscape` for information on valid forms of configuring them.
    
    

.. _[1]: https://doi.org/10.1371/journal.pcbi.1007432
"""

from brian2.units import pA, mV, ms, pF, nA
import numpy as np

np.random.seed(18)


def round_to_even(gs, scaler):
    """
    We better round things to even number for better visualization
    """
    rounded = round(gs/scaler)
    if rounded%2:
        rounded+=1
    return int(rounded)

def get_config(name='EI_net', scalar=3):
    """
    Generates the population and pathways config dictuinary only by providing 
    the name of the desired network. 
    
    .. note::
        One should differetiate between homogeneity/randomness in angle and 
        location. `[1]`_ used these terms somewhat loosely. We use the following 
        terms for different setups:
            
            * ``homiso_net``: Homogenous and isotropic netowrk, equivalent to the fully
              random graph of Erdos-Renyi.
            * ``iso_net``: Isotropic but spatially inhomogeneous (in a locally 
              conneted manner, although with a long-tailed radial profile one can
              generate few long-range connection -- thus produce a small-world net).
            * ``homo_net``: Connections are formed without dependence on the distance,
              but angle.
            * ``I_net``: the recurrent inhibitory network with radial and angular
              profiles according to to `[1]`_.
            * ``EI_net``: the recurrent inhibitory network with radial and angular
              profiles according to to `[1]`_.

        Also note that these structures are independent from how anisotropy is 
        imposed.

    .. note::
        It is possible to decrease the network's grid size by a factor of 
        ``scalar``. However, such shrinkage has different effects on different
        networks. One uni-population networks, the synaptic strenght is 
        enlarged by a factor of ``scalar**2`` to account for lower number of 
        afferents. However, syanptic weights are left intact for the 
        two-population networks, since they are set up in balance and afferents
        will effectively cancel each other. An exception from this rule is the
        signle-population excitatory network. This network is inherently 
        unstable. So, we did not enlarged the synaptic weights partially to 
        avoid blow-up. In other words, the synaptic weights is large enough to
        trigger spike but not large enough to propagate it too far.


    :param name: nework name
    :type name: str, optional
    :param scalar: scales down the network by a factor. The network must be 
        divisble to the factor. Number of connections, their strenghts, and the
        connectivity profile will be scaled accordingly. defaults to 3
    :type scalar: int, optional
    :return: pops_cfg, conn_cfg 
    :rtype: tuple of dicts

    .. _[1]: https://doi.org/10.1371/journal.pcbi.1007432

    """
    if name=='dummy':
        pops_cfg = {
            'I': {'gs': round_to_even(100, scalar), 
                  'noise': {'mu': 700*pA, 'sigma': 100*pA, 'noise_dt': 1.*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau':10*ms, 'C': 250*pF}
                          }
            }

        conn_cfg = {
            'II': {'ncons': round_to_even(1000, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gamma', 'params': {'theta': 3/scalar, 'kappa': 4}, 'gap': max(2, 6./scalar) },
                   #'synapse': {'type':'alpha_current', 'params': {'J': -10*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                    'synapse': {'type':'tsodyks-markram_jump', 
                                'params': {'J': -0.221*mV*(scalar**2), 'delay':1*ms, 
                                           'tau_f': 1500*ms, 'tau_d': 600*ms, 'U':0.1}},
                    'anisotropy': {
                        'synaptic': 'cos',
                         #'connectivity': 'shift', 
                        'params': {
                            #'r'  : 1, 
                            'phi': {'type': 'perlin', 'args': {'scale':3} }, 
                            },
                        'vars': {
                            'U': (0.1, 0.4),
                            }
                        },
                   
                # 'training': {'type': 'STDP', 
                #               'params': {'taupre': 10*ms,'taupost': 10*ms,
                #                         'Apre': 0.1, 'Apost': -0.12,},
                #               },
                }
            }
        
        stim_cfg = {}
        
    elif name=='demo':
        pops_cfg = {
            'I': {'gs': round_to_even(100, scalar), 
                  'noise': {'mu': 700*pA, 'sigma': 100*pA, 'noise_dt': 1.*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau':10*ms, 'C': 250*pF}
                          }
            }

        conn_cfg = {
            'II': {'ncons': round_to_even(1000, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gamma', 'params': {'theta': 3/scalar, 'kappa': 4}, 'gap': max(2, 6./scalar) },
                   'synapse': {'type':'alpha_current', 'params': {'J': -10*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   'anisotropy': {'connectivity': 'shift', 
                                  'params': {'r'  : 1, 
                                             'phi': {'type': 'perlin', 'args': {'scale':2} },
                                             }  
                                  },
                   
                   }
        }
        
        stim_cfg = {}
        
    elif name=='I_net':
        pops_cfg = {
            'I': {'gs': round_to_even(100, scalar), 
                  'noise': {'mu': 700*pA, 'sigma': 100*pA, 'noise_dt': 1.*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau':10*ms, 'C': 250*pF}
                          }
            }

        conn_cfg = {
            'II': {'ncons': round_to_even(1000, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gamma', 'params': {'theta': 3/scalar, 'kappa': 4}, 'gap': max(2, 6./scalar) },
                   'synapse': {'type':'alpha_current', 'params': {'J': -10*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   
                   # Note: In the paper, four different anisotropic configurations 
                   # are introduced: "random", "symmetric", "homogeneous" and 
                   # "perlin". To emulate these cases follow these instructions:
                       # comment the entire `anisotropy` dict (as well as the key) to get "random"
                       # use `'phi': {'type': 'random'}`` to get "symmetric"
                       # use `'phi': np.pi/6`` to get "homogeneous"
                       # use `'phi': {'type': 'perlin', ...` to get "perlin"
                   'anisotropy': {
                       'connectivity': 'shift', # induces anisotropy in connections with shift method 
                       'params': {'r'  : 1, 
                                  'phi': {'type': 'perlin', 'args': {'scale':3} }, # a perlin-generate angular landscape
                                  #'phi': {'type': 'random'},     # a random angular ladscape
                                  #'phi': np.pi/6,  # a homogeneous angular ladscape
                                  }  
                       },
                   }
        }
        
        stim_cfg = {}
        
    elif name=='E_net':
        pops_cfg = {
            'E': {'gs': round_to_even(100, scalar), 
                  'noise': {'mu': 50*pA, 'sigma': 400*pA, 'noise_dt': 1.*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau':10*ms, 'C': 250*pF}
                          }
            }

        conn_cfg = {
            'EE': {'ncons': round_to_even(1000, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gamma', 'params': {'theta': 3/scalar, 'kappa': 4}, 'gap': max(2, 6./scalar) },
                   'synapse': {'type':'alpha_current', 'params': {'J': 2.5*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   'anisotropy': {
                        #'synaptic': 'cos',       # induces anisotropy in synapses with cosine method
                       'connectivity': 'shift', # induces anisotropy in connections with shift method 
                       'params': {'r'  : 1, 
                                  'phi': {'type': 'perlin', 'args': {'scale':4} },
                                  'U': {'type': 'perlin', 'args': {'scale':2}, 'vmin': 0.01, 'vmax':0.3},
                                 }  
                       },
                   },
        }
    
        stim_cfg = {}
        
        
    elif name=='EI_net':
        pops_cfg = {
            'I': {'gs': round_to_even(60, scalar), 
                  'noise': {'mu': 350*pA, 'sigma': 100*pA, 'noise_dt': 1*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau': 10*ms, 'C': 250*pF}
                  },
            
            'E': {'gs': round_to_even(120, scalar), 
                  'noise': {'mu': 350*pA, 'sigma': 100*pA, 'noise_dt': 1*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau': 10*ms, 'C': 250*pF}
                  }
        }
        
        conn_cfg = {
            'EE': {'ncons': round_to_even(720, scalar**2), 'self_link':False, 
                  'profile': {'type':'Gaussian', 'params': {'std': 9/scalar}, 'gap': max(2, 6./scalar) },
                  'synapse': {'type':'alpha_current', 'params': {'J': 10*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms} },
                  
                  # Note: In the paper, four different anisotropic configurations 
                  # are introduced: "random", "symmetric", "homogeneous" and 
                  # "perlin". To emulate these cases follow these instructions:
                      # comment the entire `anisotropy` dict (as well as the key) to get "random"
                      # use `'phi': {'type': 'random'}`` to get "symmetric"
                      # use `'phi': np.pi/6`` to get "homogeneous"
                      # use `'phi': {'type': 'perlin', ...` to get "perlin"
                  'anisotropy': {
                      'connectivity': 'shift', # induces anisotropy in connections with shift method 
                      'params': {'r'  : 1, 
                                 'phi': {'type': 'perlin', 'args': {'scale':2} }, # a perlin-generate angular landscape
                                 #'phi': {'type': 'random'},  # a random angular ladscape
                                 #'phi': np.pi/6,  # a homogeneous angular ladscape
                                 }  
                      },
                  },
                  
            'EI': {'ncons': round_to_even(180, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gaussian', 'params': {'std': 4.5/scalar}, 'gap': max(2, 6./scalar) },
                   'synapse': {'type':'alpha_current', 'params': {'J': 10*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   'anisotropy': {
                       'connectivity': 'shift', # induces anisotropy in connections with shift method 
                       'params': {'r'  : 1, 
                                  'phi': {'type': 'random'},  # a random angular ladscape
                                  }  
                       },
                   },
            
            'IE': {'ncons': round_to_even(720, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gaussian', 'params': {'std': 12/scalar}, 'gap': max(2, 6./scalar) },
                   'synapse': {'type':'alpha_current', 'params': {'J': -80*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   'anisotropy': {
                       'connectivity': 'shift', # induces anisotropy in connections with shift method 
                       'params': {'r'  : 1, 
                                  'phi': {'type': 'random'},  # a random angular ladscape
                                  }  
                       },
                   },

            'II': {'ncons': round_to_even(180, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gaussian', 'params': {'std': 6/scalar}, 'gap': max(2, 6./scalar) },
                   'synapse': {'type':'alpha_current', 'params': {'J': -80*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   'anisotropy': {
                       'connectivity': 'shift', # induces anisotropy in connections with shift method 
                       'params': {'r'  : 1, 
                                  'phi': {'type': 'random'},  # a random angular ladscape
                                  }  
                       },
                   },
        }
        
        stim_cfg = {}
        
    elif name=='homo_net':
        pops_cfg = {
            'I': {'gs': round_to_even(100, scalar), 
                  'noise': {'mu': 700*pA, 'sigma': 100*pA, 'noise_dt': 1.*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau':10*ms, 'C': 250*pF}
                          }
            }
        
        # Note: For a homogeneous network, `profile` entry can be omitted. 
        conn_cfg = {
            'II': {'ncons': round_to_even(1000, scalar**2), 'self_link':False, 
                   'synapse': {'type':'alpha_current', 'params': {'J': -10*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   'anisotropy': {
                       'connectivity': 'shift', # induces anisotropy in connections with shift method 
                       'params': {'r'  : 1, 
                                  'phi': {'type': 'perlin', 'args': {'scale':3} },
                                  }  
                       },
                   },
        }

        stim_cfg = {}
                
    elif name=='iso_net':
        pops_cfg = {
            'I': {'gs': round_to_even(100, scalar), 
                  'noise': {'mu': 700*pA, 'sigma': 100*pA, 'noise_dt': 1.*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau':10*ms, 'C': 250*pF}
                          }
            }
        
        # Note: We can model an isotropic network, simply by omitting the 
        #       anisotropy key in the connections config
        conn_cfg = {
            'II': {'ncons': round_to_even(1000, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gamma', 'params': {'theta': 3/scalar, 'kappa': 4}, 'gap': max(2, 5./scalar) },
                   'synapse': {'type':'alpha_current', 'params': {'J': -10*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   },
        }    

        stim_cfg = {}
        

    elif name=='homiso_net':
        pops_cfg = {
            'I': {'gs': round_to_even(100, scalar), 
                  'noise': {'mu': 700*pA, 'sigma': 100*pA, 'noise_dt': 1.*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau':10*ms, 'C': 250*pF}
                          }
            }
        
        # Note: For a homogeneous and isotropic network no `profile` or
        #       `anisotropy` is needed.
        conn_cfg = {
            'II': {'ncons': round_to_even(1000, scalar**2), 'self_link':False, 
                   'synapse': {'type':'alpha_current', 'params': {'J': -10*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   },
        }    
    
        stim_cfg = {}
        
    elif name=='STSP_TM_I_net':
        pops_cfg = {
            'I': {'gs': round_to_even(100, scalar), 
                  'noise': {'mu': 700*pA, 'sigma': 100*pA, 'noise_dt': 1.*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau':10*ms, 'C': 250*pF}
                          }
            }

        conn_cfg = {
            'II': {'ncons': round_to_even(1000, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gamma', 'params': {'theta': 3/scalar, 'kappa': 4}, 'gap': max(2, 5./scalar) },
                   'synapse': {'type':'tsodyks-markram_jump', 
                               'params': {'J': -0.221*mV*(scalar**2), 'delay':1*ms, 
                                          'tau': 10*ms, 'tau_f': 1500.*ms, 'tau_d': 200.*ms, 
                                          }},
                   'anisotropy': {
                       'connectivity': 'shift', 'synaptic': 'cos',
                       'params': {'r'  : 1, 
                                  'phi': {'type': 'perlin', 'args': {'scale':2} },
                                  # TODO: should somehow detect if U is a landscape or will be drawn from Umin to Umax.
                                  'U': {'type': 'perlin', 'args': {'scale':2}, 'vmin': 0.01, 'vmax':0.3},
                                  'Umin': 0.05, 'Umax':0.3
                                  }  
                       },
                   },
        }
        
        stim_cfg = {}
           
    elif name=='STSP_TM_EI_net':
        pops_cfg = {
            'I': {'gs': round_to_even(60, scalar), 
                  'noise': {'mu': 350*pA, 'sigma': 100*pA, 'noise_dt': 1*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau': 10*ms, 'C': 250*pF}
                  },
            
            'E': {'gs': round_to_even(120, scalar), 
                  'noise': {'mu': 350*pA, 'sigma': 100*pA, 'noise_dt': 1*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau': 10*ms, 'C': 250*pF}
                 }
            }


        conn_cfg = {
            'EE': {'ncons': round_to_even(720, scalar**2), 'self_link':False, 
                  'profile': {'type':'Gaussian', 'params': {'std': 9/scalar}, 'gap': max(2, 6./scalar) },
                  'synapse': {'type':'tsodyks-markram_jump', 
                              'params': {'J': 0.221*mV*(scalar**2), 'delay':1*ms, 
                                         'tau_f': 1500*ms, 'tau_d': 600*ms, 'U':0.1}},
                  'anisotropy': {
                      'connectivity': 'shift', 
                      'params': {'r'  : 1, 'phi': {'type': 'perlin', 'args': {'scale':2} }, }  
                      },
                  },
            
            'EI': {'ncons': round_to_even(180, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gaussian', 'params': {'std': 4.5/scalar}, 'gap': max(2, 6./scalar) },
                   'synapse': {'type':'tsodyks-markram_jump', 
                               'params': {'J': 0.221*mV*(scalar**2), 'delay':1*ms, 
                                          'tau_f': 1500*ms, 'tau_d': 600*ms, 'U':0.1}},
                   
                   },
            
            'IE': {'ncons': round_to_even(720, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gaussian', 'params': {'std': 12/scalar}, 'gap': max(2, 6./scalar) },
                   'synapse': {'type':'alpha_current', 'params': {'J': -80*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   },

            'II': {'ncons': round_to_even(180, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gaussian', 'params': {'std': 6/scalar}, 'gap': max(2, 6./scalar) },
                   'synapse': {'type':'alpha_current', 'params': {'J': -80*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   },
            
            }
    
        stim_cfg = {}
        
    
    elif name=='EI_net_focal_stim':
        pops_cfg = {
            'I': {'gs': round_to_even(60, scalar), 
                  'noise': {'mu': 350*pA, 'sigma': 100*pA, 'noise_dt': 1*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau': 10*ms, 'C': 250*pF}
                  },
            
            'E': {'gs': round_to_even(120, scalar), 
                  'noise': {'mu': 350*pA, 'sigma': 100*pA, 'noise_dt': 1*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau': 10*ms, 'C': 250*pF}
                 }
            }


        conn_cfg = {
            'EE': {'ncons': round_to_even(720, scalar**2), 'self_link':False, 
                  'profile': {'type':'Gaussian', 'params': {'std': 9/scalar}, 'gap': max(2, 6./scalar) },
                  'synapse': {'type':'tsodyks-markram_jump', 
                              'params': {'J': 0.221*mV*(scalar**2), 'delay':1*ms, 
                                         'tau_f': 1500*ms, 'tau_d': 600*ms, 'U':0.1}},
                  'anisotropy': {
                      'connectivity': 'shift', 
                      'params': {'r'  : 1, 'phi': {'type': 'perlin', 'args': {'scale':2} }, }  
                      },
                  },
            
            'EI': {'ncons': round_to_even(180, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gaussian', 'params': {'std': 4.5/scalar}, 'gap': max(2, 6./scalar) },
                   'synapse': {'type':'tsodyks-markram_jump', 
                               'params': {'J': 0.221*mV*(scalar**2), 'delay':1*ms, 
                                          'tau_f': 1500*ms, 'tau_d': 600*ms, 'U':0.2}},
                   
                   },
            
            'IE': {'ncons': round_to_even(720, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gaussian', 'params': {'std': 12/scalar}, 'gap': max(2, 6./scalar) },
                   'synapse': {'type':'alpha_current', 'params': {'J': -80*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   },

            'II': {'ncons': round_to_even(180, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gaussian', 'params': {'std': 6/scalar}, 'gap': max(2, 6./scalar) },
                   'synapse': {'type':'alpha_current', 'params': {'J': -80*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   },
            
            }
            
        stim_cfg = {
            'E_0': {'type': 'const', 'I_stim': 500,
                    'domain': {'type': 'r', 'x0': 15, 'y0': 20, 'r':2}
                    },
            
            # 'I_1': {'type': 'const', 'I_stim': -0,
            #         'domain': {'type': 'random', 'p': 1}
            #         }
            
            }
            
    elif name=='I_net_focal_stim':
        pops_cfg = {
            'I': {'gs': round_to_even(100, scalar), 
                  'noise': {'mu': 700*pA, 'sigma': 100*pA, 'noise_dt': 1.*ms},
                  'cell': {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau':10*ms, 'C': 250*pF}
                          }
            }
        
        conn_cfg = {
            'II': {'ncons': round_to_even(1000, scalar**2), 'self_link':False, 
                   'profile': {'type':'Gamma', 'params': {'theta': 3/scalar, 'kappa': 4}, 'gap': max(2, 6./scalar) },
                   
                   'synapse': {'type':'alpha_current', 'params': {'J': -10*(scalar**2)*pA, 'delay':1*ms, 'tau': 5*ms}},
                   # 'synapse': {'type':'tsodyks-markram_jump', 
                   #             'params': {'J': 0.221*mV*(scalar**2), 'delay':1*ms, 
                   #                        'tau_f': 1500*ms, 'tau_d': 600*ms, 'U':0.1}},
                   
                   
                   'anisotropy': {
                       'connectivity': 'shift', # induces anisotropy in connections with shift method 
                       'params': {'r'  : 1, 
                                  'phi': {'type': 'perlin', 'args': {'scale':4} }, # a perlin-generate angular landscape
                                  #'phi': {'type': 'random'},  # a random angular ladscape
                                  #'phi': np.pi/6,  # a homogeneous angular ladscape
                                  }  
                       },
                   
                   'training': {'type': 'STDP', 
                             'params': {'taupre': 10*ms,'taupost': 10*ms,
                                        'Apre': 0.05, 'Apost': -0.055,},
                             },
                
                   }
        }
           
        stim_cfg = {
            'I_0': {'type': 'const', 'I_stim': 400,
                    'domain': {'type': 'r', 'x0': 20, 'y0': 10, 'r':2.5}
                    },
            
            # 'I_1': {'type': 'const', 'I_stim': 700,
            #         'domain': {'type': 'r', 'x0': 3, 'y0': 10, 'r': 7}
            #         }
            
            }
   
    else:
        raise
    
    return pops_cfg, conn_cfg, stim_cfg
       

class configer(object):
    
    def __init__(self):
        self.pops_cfg = {}
        self.conn_cfg = {}
        self.stim_cfg = {}
    
    def add_pop(self, pop_name, gs):
        pop_cfg = {}
        pop_cfg['gs'] = gs
        
        # defaults
        pop_cfg['noise']= {'mu': 0*pA, 'sigma': 0*pA, 'noise_dt': 1.*ms},
        pop_cfg['cell'] = {'type': 'LIF', 
                           'thr': -55*mV, 'ref': 2*ms, 'rest': -70*mV,
                           'tau':10*ms, 'C': 250*pF}
        
        self.pops_cfg[pop_name] = pop_cfg
        
    def update_neuron(self, pop_name, update):
        pass
    
    def update_noise(self, pop_name, update):
        pass
        
    def add_pathway(self, src, trg, ncons, synapse, self_link=False):
        conn_cfg = {}
        
        conn_cfg['ncons'] = ncons
        conn_cfg['self_link'] = self_link
        
        conn_cfg['synapse'] = self_link
        
        