The purpose of this little script is to start user defined amout
of VMs on an Openstack cloud and check the SSH availability of the
created VMs.

The main purpose was to test, that regarding the amount of VMs you want to
deploy, all VMs get connectivy and reach the meta data server to fetch
the SSH priv key.

What the scipt do
-----------------

- The script create a HEAT template
- Create the HEAT stack
- Wait for stack and all SSH server of VMs are UP
- Try to connect via the floating IP
- Report failed and succeed connections

Usage
-----

First load your Openstack env before starting that command.
Be sure to have installed python-heatclient.

python loadandcheck.py --anodes 8 --keyname mykey --nuuid 6c83db7b-480e-4198-bc69-88df6fd17e55
--iid 5e72e6bf-7604-4141-8ace-47565551aa4f --itype m1.small

Caution
-------

This script has been written to perform a quick test so the code
is not really clean.
