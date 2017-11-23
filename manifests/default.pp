
$ovsdb_version = "2.8.1"
$ovsdb_release_url = "http://openvswitch.org/releases/openvswitch-${ovsdb_version}.tar.gz"
$ovsdb_root_dir = "/home/vagrant"
$ovsdb_source_path = "${ovsdb_root_dir}/openvswitch-${ovsdb_version}"
$ovsdb_download_path = "${ovsdb_source_path}.tar.gz"
$ovsdb_path = "/home/vagrant/ovsdb"

$jansson_version = "2.10"
$jansson_release_url = "http://www.digip.org/jansson/releases/jansson-${jansson_version}.tar.gz"
$jansson_root_dir = "/home/vagrant"
$jansson_source_path = "${jansson_root_dir}/jansson-${jansson_version}"
$jansson_download_path = "${jansson_source_path}.tar.gz"
$jansson_path = "/usr/local/lib/libjansson.a"

$iproute2_version = "v4.14.1"
$iproute2_git_repo = "git://git.kernel.org/pub/scm/linux/kernel/git/shemminger/iproute2.git"
$iproute2_cwd = "/home/vagrant/iproute2"

$default_path = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

Package {
  allow_virtual => true,
  ensure => installed,
  require => Exec['apt-update'],
}
Exec { path => $default_path }

exec { 'apt-update':
  command => 'apt-get update',
}


# Python packages
package { 'python-setuptools':}
package { 'python-pip':}
package { 'py2-ipaddress':
  require => Package['python-pip'],
  provider => 'pip',
}
package { 'mako':
  require => Package['python-pip'],
  provider => 'pip',
}
package { 'six':
  require => Package['python-pip'],
  provider => 'pip',
}

# Networking
package { 'wireshark':}
package { 'traceroute':}
package { 'tcpdump':}
package { 'bridge-utils':}
package { 'mininet':}
package { 'radvd':}

# Compilation
package { 'libreadline6':}
package { 'libreadline6-dev':
  require => [ Exec['apt-update'], Package['libreadline6'] ],
}
package { 'gawk':}
package { 'automake':}
package { 'libtool':
  require => [ Exec['apt-update'], Package['m4'], Package['automake'] ],
}
package { 'm4':}
package { 'bison':}
package { 'flex':}
package { 'pkg-config':}
package { 'dia':}
package { 'texinfo':}
package { 'libc-ares-dev':}
package { 'cmake':}

# Miscellaneous
package { 'xterm':}
package { 'man':}
package { 'git':}
package { 'valgrind':}

# Locale settings
exec { 'locales':
  require => Exec['apt-update'],
  command => "locale-gen fr_BE.UTF-8; update-locale",
}

# Main softwares

$compilation = [Exec['locales'], Package['libreadline6-dev'], Package['gawk'], Package['libtool'], Package['libc-ares-dev'],
                Package['bison'], Package['flex'], Package['pkg-config'], Package['dia'], Package['texinfo']]

exec { 'ovsdb-download':
  require => [ Exec['apt-update'] ],
  creates => $ovsdb_source_path,
  command => "wget -O - ${ovsdb_release_url} > ${ovsdb_download_path} &&\
              tar -xvzf ${ovsdb_download_path} -C ${ovsdb_root_dir};"
}
exec { 'ovsdb':
  require => [ Exec['apt-update'], Exec['ovsdb-download'], Package['six'] ] + $compilation,
  cwd => $ovsdb_source_path,
  creates => $ovsdb_path,
  path => "${default_path}:${ovsdb_source_path}",
  # --enable-ndebug is an optimization of the compiler
  command => "configure --prefix=${ovsdb_path} --enable-ndebug &&\
              make &&\
              make install &&\
              rm ${ovsdb_download_path} &&\
              echo \"# ovsdb binaries\" >> /etc/profile &&\
              echo \"PATH=\\\"${ovsdb_path}/bin:${ovsdb_path}/sbin:\\\$PATH\\\"\" >> /etc/profile &&\
              echo \"alias sudo=\'sudo env \\\"PATH=\\\$PATH\\\"\'\" >> /etc/profile &&\
              echo \"# ovsdb binaries\" >> /root/.bashrc &&\
              echo \"PATH=\\\"${ovsdb_path}/bin:${ovsdb_path}/sbin:\\\$PATH\\\"\" >> /root/.bashrc &&\
              PATH=${ovsdb_path}/sbin:${ovsdb_path}/bin:\$PATH;",
}

exec { 'jansson-download':
  require => [ Exec['apt-update'] ],
  creates => $jansson_source_path,
  command => "wget -O - ${jansson_release_url} > ${jansson_download_path} &&\
              tar -xvzf ${jansson_download_path} -C ${jansson_root_dir};"
}
exec { 'jansson':
  require => [ Exec['apt-update'], Exec['jansson-download'] ] + $compilation,
  cwd => $jansson_source_path,
  creates => $jansson_path,
  path => "${default_path}:${jansson_source_path}",
  command => "configure &&\
              make &&\
              make install;"
}

exec { 'iproute2-download':
  require => [ Exec['apt-update'] ],
  creates => $iproute2_cwd,
  command => "git clone ${iproute2_git_repo} ${iproute2_cwd} &&\
              git checkout ${iproute2_version};",
}
# Somehow using TMPDIR as bash variable is a problem in the vagrant box
exec { 'iproute2':
  require => [ Exec['apt-update'], Exec['iproute2-download'] ] + $compilation,
  creates => "/home/vagrant/.newiproute",
  cwd => $iproute2_cwd,
  path => "${default_path}:${iproute2_cwd}",
  command => "sed -i -e 's/TMPDIR/TEMPDIR/g' ${iproute2_cwd}/configure &&\
              configure &&\
              make &&\
              make install &&\
              touch /home/vagrant/.newiproute;",
}
