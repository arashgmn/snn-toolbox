#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 18 13:58:11 2022

@author: arash
"""

from anisonet.simulate import Simulate
import brian2 as b2

sim = Simulate('demo', scalar=4, 
               load_connectivity=1, 
               to_event_driven=1, training=True)

sim.setup_net()
sim.warmup()
sim.start(duration=2500*b2.ms, batch_dur=1000*b2.ms, 
            restore=False, profile=False, plot_snapshots=True)
sim.post_process(overlay=True)

