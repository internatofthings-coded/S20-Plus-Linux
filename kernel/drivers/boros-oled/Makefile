KDIR_DEFAULT ?= /path/to/linux-6.12.119-build
obj-m += boros_oled.o

KDIR ?= $(KDIR_DEFAULT)
ARCH ?= arm64
CROSS_COMPILE ?= aarch64-linux-gnu-

all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) modules

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) clean
