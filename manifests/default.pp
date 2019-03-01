$ovsdb_version = "2.9.0"
$ovsdb_release_url = "http://openvswitch.org/releases/openvswitch-${ovsdb_version}.tar.gz"
$ovsdb_root_dir = "/home/vagrant"
$ovsdb_source_path = "${ovsdb_root_dir}/openvswitch-${ovsdb_version}"
$ovsdb_download_path = "${ovsdb_source_path}.tar.gz"
$ovsdb_path = "/usr/sbin/ovsdb-server"

$jansson_version = "2.12"
$jansson_release_url = "http://www.digip.org/jansson/releases/jansson-${jansson_version}.tar.gz"
$jansson_root_dir = "/home/vagrant"
$jansson_source_path = "${jansson_root_dir}/jansson-${jansson_version}"
$jansson_download_path = "${jansson_source_path}.tar.gz"
$jansson_path = "/usr/local/lib/libjansson.a"

$zlog_version = "1.2.12"
$zlog_release_url = "https://github.com/HardySimpson/zlog/archive/${zlog_version}.tar.gz"
$zlog_root_dir = "/home/vagrant"
$zlog_source_path = "${zlog_root_dir}/zlog-${zlog_version}"
$zlog_download_path = "${zlog_source_path}.tar.gz"
$zlog_path = "/usr/local/lib/libzlog.so"

$ipmininet_repo = "https://github.com/oliviertilmans/ipmininet.git"
$ipmininet_path = "/home/vagrant/ipmininet"
$sr6mininet_repo = "https://bitbucket.org/jadinm/sr6mininet.git"
$sr6mininet_path = "/home/vagrant/sr6mininet"

$srnmininet_path = "/home/vagrant/srnmininet"
$srn_repo = "https://github.com/segment-routing/srn.git"
$srn_path = "/home/vagrant/srn"

$default_path = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

Package {
  allow_virtual => true,
  ensure        => installed,
  require       => Exec['apt-update'],
}
Exec { path => $default_path }

exec { 'apt-update':
  command => 'apt-get update',
}

# Python packages
package { 'python-setuptools': }
package { 'python-pip': }
package { 'py2-ipaddress':
  require  => Package['python-pip'],
  provider => 'pip',
}
package { 'mako':
  require  => Package['python-pip'],
  provider => 'pip',
}
package { 'six':
  require  => Package['python-pip'],
  provider => 'pip',
}
package { 'psutil':
  require  => Package['python-pip'],
  provider => 'pip',
}

# Networking
package { 'wireshark': }
package { 'traceroute': }
package { 'tcpdump': }
package { 'bridge-utils': }
package { 'mininet': }
package { 'radvd': }

# Compilation
package { 'libreadline6': }
package { 'libreadline6-dev':
  require => [ Exec['apt-update'], Package['libreadline6'] ],
}
package { 'gawk': }
package { 'automake': }
package { 'libtool':
  require => [ Exec['apt-update'], Package['m4'], Package['automake'] ],
}
package { 'm4': }
package { 'bison': }
package { 'flex': }
package { 'pkg-config': }
package { 'dia': }
package { 'texinfo': }
package { 'libc-ares-dev': }
package { 'cmake': }
package { 'libmnl0': }
package { 'libmnl-dev': }

# Miscellaneous
package { 'xterm': }
package { 'man': }
package { 'git': }
package { 'valgrind': }
package { 'vim': }

# SSH redirection
package { 'xauth': }

# Locale settings
exec { 'locales':
  require => Exec['apt-update'],
  command => "locale-gen fr_BE.UTF-8; update-locale",
}

# IPMininet

exec { 'ipmininet-download':
  require => Package['git'],
  creates => $ipmininet_path,
  command => "git clone ${ipmininet_repo} ${ipmininet_path}",
}
exec { 'ipmininet':
  require => [ Exec['locales'], Exec['apt-update'], Package['mininet'], Package['mako'], Exec['ipmininet-download'] ],
  command => "pip install -e ${ipmininet_path}",
}
exec { 'sr6mininet-download':
  require => Package['git'],
  creates => $sr6mininet_path,
  command => "git clone ${sr6mininet_repo} ${sr6mininet_path} && chown -R vagrant:vagrant ${sr6mininet_path}",
}
exec { 'sr6mininet':
  require => [ Exec['ipmininet'], Exec['sr6mininet-download'] ],
  command => "pip install -e ${sr6mininet_path}",
}

exec { 'srnmininet':
  require => Exec['sr6mininet'],
  command => "pip install -e ${srnmininet_path}",
}

# SRN

package { 'bind9': }

$compilation = [Exec['locales'], Package['libreadline6-dev'], Package['gawk'], Package['libtool'],
  Package['libc-ares-dev'], Package['bison'], Package['flex'], Package['pkg-config'], Package['dia'],
  Package['texinfo'], Package['libmnl0'], Package['libmnl-dev']]

exec { 'ovsdb-download':
  require => [ Exec['apt-update'] ],
  creates => $ovsdb_source_path,
  command => "wget -O - ${ovsdb_release_url} > ${ovsdb_download_path} &&\
              tar -xvzf ${ovsdb_download_path} -C ${ovsdb_root_dir};"
}
exec { 'ovsdb':
  require => [ Exec['apt-update'], Exec['ovsdb-download'], Package['six'] ] + $compilation,
  cwd     => $ovsdb_source_path,
  creates => $ovsdb_path,
  path    => "${default_path}:${ovsdb_source_path}",
  command => "configure &&\
              make &&\
              make install &&\
              rm ${ovsdb_download_path}",
}

exec { 'jansson-download':
  require => [ Exec['apt-update'] ],
  creates => $jansson_source_path,
  command => "wget -O - ${jansson_release_url} > ${jansson_download_path} &&\
              tar -xvzf ${jansson_download_path} -C ${jansson_root_dir};"
}
exec { 'jansson':
  require => [ Exec['apt-update'], Exec['jansson-download'] ] + $compilation,
  cwd     => $jansson_source_path,
  creates => $jansson_path,
  path    => "${default_path}:${jansson_source_path}",
  command => "configure &&\
              make &&\
              make install &&\
	            /sbin/ldconfig -v &&\
	            rm ${jansson_download_path};"
}

# Logging
exec { 'zlog-download':
  require => Exec['apt-update'],
  creates => $zlog_source_path,
  command => "wget -O - ${zlog_release_url} > ${zlog_download_path} &&\
              tar -xvzf ${zlog_download_path} -C ${zlog_root_dir};"
}
exec { 'zlog':
  require => [ Exec['apt-update'], Exec['zlog-download'] ],
  cwd => $zlog_source_path,
  creates => $zlog_path,
  path => "${default_path}:${zlog_source_path}",
  command => "make &&\
              make install &&\
	            /sbin/ldconfig -v &&\
              rm ${zlog_download_path};"
}

exec { 'srn-download':
  require => Package['git'],
  creates => $srn_path,
  command => "git clone --recursive ${srn_repo} ${srn_path}",
}

exec { 'srn':
  require => [ Exec['jansson'], Exec['zlog'], Exec['srn-download'] ] + $compilation,
  creates => "${srn_path}/bin/",
  cwd     => $srn_path,
  path    => "${default_path}:${srn_path}",
  command => "make &&\
              echo \"# SRN binaries\" >> /etc/profile &&\
              echo \"PATH=\\\"${srn_path}/bin:\\\$PATH\\\"\" >> /etc/profile &&\
              echo \"# SRN binaries\" >> /root/.bashrc &&\
              echo \"PATH=\\\"${srn_path}/bin:\\\$PATH\\\"\" >> /root/.bashrc &&\
              sed -i '/secure_path/d' /etc/sudoers",
}

# Quagga group
group { 'quagga':
  ensure => 'present',
}
user { 'vagrant':
  groups => 'quagga',
}
user { 'root':
  groups => 'quagga',
}
