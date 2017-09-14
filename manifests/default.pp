
$ovsdb_version = "2.6.1"
$ovsdb_release_url = "http://openvswitch.org/releases/openvswitch-${ovsdb_version}.tar.gz"
$ovsdb_root_dir = "/home/vagrant"
$ovsdb_source_path = "${ovsdb_root_dir}/openvswitch-${ovsdb_version}"
$ovsdb_download_path = "${ovsdb_source_path}.tar.gz"
$ovsdb_path = "/home/vagrant/ovsdb"

# PATH
$default_path = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Exec { path => $default_path }

exec { 'apt-update':
  command => 'apt-get update',
}

# Install ovsdb
exec { 'ovsdb-download':
  require => Exec['apt-update'],
  creates => $ovsdb_source_path,
  command => "wget -O - ${ovsdb_release_url} > ${ovsdb_download_path};\
              tar -xvzf ${ovsdb_download_path} -C ${ovsdb_root_dir};"
}
exec { 'ovsdb':
  require => [ Exec['apt-update'], Exec['ovsdb-download'] ],
  cwd => $ovsdb_source_path,
  creates => $ovsdb_path,
  path => "${default_path}:${ovsdb_source_path}",
  command => "configure --prefix=${ovsdb_path};\
              make;\
              make install;\
              rm ${ovsdb_download_path};\
              echo \"# ovsdb binaries\" >> /etc/profile;\
              echo \"PATH=\\\"${ovsdb_path}/bin:${ovsdb_path}/sbin:\\\$PATH\\\"\" >> /etc/profile;\
              echo \"alias sudo=\'sudo env \\\"PATH=\\\$PATH\\\"\'\" >> /etc/profile;\
              echo \"# ovsdb binaries\" >> /root/.bashrc;\
              echo \"PATH=\\\"${ovsdb_path}/bin:${ovsdb_path}/sbin:\\\$PATH\\\"\" >> /root/.bashrc;\
              PATH=${ovsdb_path}/sbin:${ovsdb_path}/bin:$PATH;",
}

# Python packages
package { 'python-setuptools':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'python-pip':
  require => [ Exec['apt-update'], Package['python-setuptools'] ],
  ensure => installed,
}
package { 'py2-ipaddress':
  require => Package['python-pip'],
  ensure => installed,
  provider => 'pip',
}
package { 'mako':
  require => Package['python-pip'],
  ensure => installed,
  provider => 'pip',
}

# Networking
package { 'wireshark':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'traceroute':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'tcpdump':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'bridge-utils':
  require => Exec['apt-update'],
  ensure => installed,
}

# Compilation
package { 'libreadline6':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'libreadline6-dev':
  require => [ Exec['apt-update'], Package['libreadline6'] ],
  ensure => installed,
}
package { 'gawk':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'automake':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'libtool':
  require => [ Exec['apt-update'], Package['m4'], Package['automake'] ],
  ensure => installed,
}
package { 'm4':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'bison':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'flex':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'pkg-config':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'libdbm-dev':
  require => Exec['apt-update'],
  ensure => installed,
}

# Miscellaneous
package { 'xterm':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'man':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'git':
  require => Exec['apt-update'],
  ensure => installed,
}
package { 'valgrind':
  require => Exec['apt-update'],
  ensure => installed,
}

# Locale settings
exec { 'locales':
  require => Exec['apt-update'],
  command => "locale-gen fr_BE.UTF-8; update-locale",
}
