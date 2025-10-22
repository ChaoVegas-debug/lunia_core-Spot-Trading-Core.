#include <tunables/global>

profile lunia-python flags=(attach_disconnected,mediate_deleted) {
  include <abstractions/base>
  include <abstractions/python>
  include <abstractions/user-tmp>

  capability chown,
  capability dac_override,
  capability fowner,
  capability sys_admin,
  capability sys_resource,

  network inet,
  network inet6,

  /opt/app/** rwk,
  /tmp/** rwk,
  /dev/null rw,
  /dev/urandom rw,
  /proc/** r,

  deny /etc/shadow r,
  deny /root/** r,

  signal (receive) peer=unconfined,
  ptrace (readby, tracedby) peer=unconfined,
}
