#promisc
sudo ifconfig enp2s0f1 down
sudo ifconfig enp2s0f1 192.168.1.19 netmask 255.255.255.0 up promisc
sudo ip link set enp2s0f1 mtu 8192


sudo ifconfig enp2s0f0 down
sudo ifconfig enp2s0f0 192.168.1.25 netmask 255.255.255.0 up promisc
sudo ip link set enp2s0f0 mtu 8192

sudo sysctl -w net.core.wmem_max=938860800
sudo sysctl -w net.core.rmem_max=938860800
sudo sysctl -w net.core.rmem_default=919260800
sudo sysctl -w net.ipv4.udp_rmem_min=9192000 
sudo ethtool -K enp2s0f0 rx off
sudo ethtool -K enp2s0f0 tx off


sudo tcpdump -e -i enp2s0f0 -n udp port 10000 -vv
