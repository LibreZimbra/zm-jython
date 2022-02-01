# SPDX-License-Identifier: AGPL-3.0-or-later

all:
	echo -n

include build.mk

install:
	$(call mk_install_dir, common/lib)
	cp -R jylibs $(INSTALL_DIR)/common/lib
	$(call install_conf, conf/zmconfigd.cf)
	$(call install_conf, conf/zmconfigd.log4j.properties)
	$(call install_libexec, src/libexec/zmconfigd)
	$(call install_libexec, src/libexec/zmpython)

clean:
	echo -n
