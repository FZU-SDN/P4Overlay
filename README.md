### FuZhou University, SDNLab.

## Repo: P4Overlay

### Description: 

This repo shows how to use p4 switches to create an overlay network.

In our example, we create the topologic showed below. In the view of control plane, the network seems to be only two switches, ovs1 and ovs2, but the physical network was composed of six switches, that were both p4 switch and ovs.

We rewrited the topo.py to create an overlay network based on P4Switches.

```
                  -> s2 <-
                 /        \
  ovs1 <--> s1 <-          -> s4 <--> ovs2
                 \        /
                  -> s3 <-
```

Added by Chen, 2017.3.18
