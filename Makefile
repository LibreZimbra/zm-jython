# SPDX-License-Identifier: AGPL-3.0-or-later

all:
	echo -n

include build.mk

install:
	$(call mk_install_dir, common/lib)
	cp -R jylibs $(INSTALL_DIR)/common/lib

clean:
	echo -n
