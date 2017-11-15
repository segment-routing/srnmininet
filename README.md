# Resources for SRN testing

## Create modified basebox

0. Setup a regular linux VM

1. install 4.14 linux kernel

	a. Get the [linux](https://git.kernel.org/pub/scm/linux/kernel/git/davem/net-next.git) repository and choose any version after 4.14

	b. The following variables must be set at kernel compilation (in menuconfig => Networking support => Networking options => IPv6 protocol):
		- CONFIG_IPV6_SEG6_LWTUNNEL=y
		- CONFIG_IPV6_SEG6_HMAC=y

	c. Compile and install the kernel (e.g., follow these [instructions](https://www.cyberciti.biz/faq/debian-ubuntu-building-installing-a-custom-linux-kernel/)).

	d. Get the master branch of the [iproute2](https://git.kernel.org/pub/scm/linux/kernel/git/shemminger/iproute2.git) repository.
	
	e. See its README for installation instructions.

3. Guest additions

	a. Install the newest version (5.1) of virtualbox as indicated [there](http://ubuntuhandbook.org/index.php/2016/07/virtualbox-5-1-released/).
		-> Use "sudo rcvboxdrv setup" to recompile kernel modules.

	b. Install Virtualbox guest additions from the newest [iso file](http://download.virtualbox.org/virtualbox/5.1.26/VBoxGuestAdditions_5.1.26.iso) (see [installation instructions](https://www.virtualbox.org/manual/ch04.html)).
		-> Don't forget to "sudo usermod -a -G vboxsf vagrant" (+ exit and reopen a new bash session before testing).

4. Setup virtual base box for vagrant

	a. Install the following packages (see [instructions](https://www.vagrantup.com/docs/boxes/base.html)).

	b. Follow [instructions](https://www.vagrantup.com/docs/virtualbox/boxes.html) to create the vagrant box with virtual box.

## Launch a test topology

TODO
