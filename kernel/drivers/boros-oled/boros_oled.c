// SPDX-License-Identifier: GPL-2.0
/*
 * boros_oled.c - Physical OLED power-off/on via Exynos 990 DSIM_0 MIPI DCS
 *
 * Verified against official Samsung SM-G985F (G985FXXSGHWD4) GPL source:
 *   - drivers/video/fbdev/exynos/dpu30/cal_9830/regs-dsim.h
 *   - drivers/video/fbdev/exynos/panel/s6e3hab/s6e3hab_hubble2_a3_s0_panel.h
 *   - reference/z3s-mainline-linux/kernel/dts/clk-exynos990.c
 *
 * Never modifies S2DOS05 rails, reset GPIO, DECON, or PLLs.
 */

#include <linux/delay.h>
#include <linux/io.h>
#include <linux/iopoll.h>
#include <linux/ioport.h>
#include <linux/kobject.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/sysfs.h>

/* Exynos 990 (9830) always-on PMU & CMU_TOP DPU status/gate registers:
 * - PMU DPU_STATUS 0x15860000 + 0x1e84, BIT(0) (flexpmu_cal_local_exynos9830.h:353)
 * - CMU_TOP 0x1a330000 + 0x2060/0x2064, BIT(21) CG_VAL (cmucal-sfr.c:837,866,5045,5132)
 */
#define PMU_DPU_STATUS_PHYS		0x15861e84UL
#define PMU_DPU_PWR_ON_MASK		BIT(0)
#define CMU_TOP_DPU_GATE_PHYS		0x1a332060UL
#define CMU_DPU_GATE_EN_BIT		BIT(21)

/* Exynos 990 DSIM_0 (analysis/y2s-original.dts:12511-12513, cal_9830/regs-dsim.h) */
#define DSIM0_PHYS_BASE			0x190c0000UL
#define DSIM0_MAP_SIZE			0x300UL

#define DSIM_VERSION			0x0000	/* regs-dsim.h:18 */
#define DSIM_RESOL			0x003c	/* regs-dsim.h:115 */
#define DSIM_CONFIG			0x004c	/* regs-dsim.h:150 */
#define DSIM_INTSRC			0x0050	/* regs-dsim.h:178 */
#define DSIM_PKTHDR			0x0058	/* regs-dsim.h:222 */
#define DSIM_PAYLOAD			0x005c	/* regs-dsim.h:230 */
#define DSIM_FIFOCTRL			0x0068	/* regs-dsim.h:241 */

#define DSIM_CONFIG_VIDEO_MODE		BIT(18)	/* regs-dsim.h:162 */
#define DSIM_CONFIG_CPRS_EN		BIT(19)	/* regs-dsim.h:161 */

#define DSIM_FIFOCTRL_EMPTY_PL_SFR	BIT(8)	/* regs-dsim.h:248 */
#define DSIM_FIFOCTRL_FULL_PL_SFR	BIT(9)	/* regs-dsim.h:247 */
#define DSIM_FIFOCTRL_EMPTY_PH_SFR	BIT(10)	/* regs-dsim.h:246 */
#define DSIM_FIFOCTRL_FULL_PH_SFR	BIT(11)	/* regs-dsim.h:245 */

#define FIFO_WAIT_US			100
#define FIFO_PRE_TIMEOUT_US		10000	/* 10 ms */
#define FIFO_DRAIN_TIMEOUT_US		50000	/* 50 ms */

#define MIPI_DSI_DCS_SHORT_WRITE	0x05
#define MIPI_DSI_DCS_LONG_WRITE		0x39
#define MIPI_DCS_ENTER_SLEEP_MODE	0x10
#define MIPI_DCS_EXIT_SLEEP_MODE	0x11
#define MIPI_DCS_SET_DISPLAY_OFF	0x28
#define MIPI_DCS_SET_DISPLAY_ON		0x29

/* s6e3hab_hubble2_a3_s0_panel.h:1337,1340 */
#define S6E3HAB_KEY1_ENABLE_PL		0x00a5a59fU	/* { 0x9F, 0xA5, 0xA5 } */
#define S6E3HAB_KEY1_DISABLE_PL		0x005a5a9fU	/* { 0x9F, 0x5A, 0x5A } */

/* Host-observed state (DCS writes without BTA do not return panel ACK) */
enum oled_host_state {
	OLED_BOOT_ON = 0,
	OLED_TRANSITIONING,
	OLED_SLEEP_TX,
	OLED_WAKE_TX,
	OLED_FAULT,
};

static const char *const state_names[] = {
	[OLED_BOOT_ON] = "boot_on",
	[OLED_TRANSITIONING] = "transitioning",
	[OLED_SLEEP_TX] = "sleep_tx",
	[OLED_WAKE_TX] = "wake_tx",
	[OLED_FAULT] = "fault",
};

static bool dry_run;
module_param(dry_run, bool, 0444);
MODULE_PARM_DESC(dry_run, "Log DCS writes without touching DSIM_PKTHDR/PAYLOAD (immutable after load)");

static void __iomem *pmu_dpu_base;
static void __iomem *cmu_dpu_base;
static void __iomem *dsim_base;
static struct kobject *oled_kobj;
static DEFINE_MUTEX(oled_lock);
static enum oled_host_state cur_state = OLED_BOOT_ON;
static int last_err;
static u32 reg_pmu_dpu, reg_cmu_dpu, reg_cmu_dpu_bus;
static u32 reg_version, reg_resol, reg_config, reg_fifoctrl, reg_intsrc;
static unsigned long toggle_cycles;

/* Must be called with oled_lock held before any DSIM MMIO access */
static int dpu_ready_locked(void)
{
	reg_pmu_dpu = readl(pmu_dpu_base);
	if ((reg_pmu_dpu & PMU_DPU_PWR_ON_MASK) != PMU_DPU_PWR_ON_MASK) {
		pr_err("boros_oled: pd-dpu OFF (pmu=0x%08x); blocking DSIM MMIO\n",
		       reg_pmu_dpu);
		return -EIO;
	}

	reg_cmu_dpu = readl(cmu_dpu_base);
	reg_cmu_dpu_bus = readl(cmu_dpu_base + 4);
	if (!(reg_cmu_dpu & CMU_DPU_GATE_EN_BIT) ||
	    !(reg_cmu_dpu_bus & CMU_DPU_GATE_EN_BIT)) {
		pr_err("boros_oled: CMU_TOP DPU clocks gated (dpu=0x%08x bus=0x%08x); blocking DSIM MMIO\n",
		       reg_cmu_dpu, reg_cmu_dpu_bus);
		return -EIO;
	}

	return 0;
}

static int dsim_send_dcs0_locked(u8 cmd)
{
	u32 hdr = MIPI_DSI_DCS_SHORT_WRITE | ((u32)cmd << 8);
	u32 fifo;
	int ret;

	ret = dpu_ready_locked();
	if (ret)
		return ret;

	if (dry_run) {
		pr_info("boros_oled: dry_run DCS0 0x%02x (hdr=0x%08x)\n", cmd, hdr);
		return 0;
	}

	ret = readl_poll_timeout(dsim_base + DSIM_FIFOCTRL, fifo,
				 !(fifo & DSIM_FIFOCTRL_FULL_PH_SFR),
				 FIFO_WAIT_US, FIFO_PRE_TIMEOUT_US);
	if (ret) {
		pr_err("boros_oled: PH FIFO full before DCS 0x%02x (fifo=0x%08x)\n",
		       cmd, fifo);
		return -ETIMEDOUT;
	}

	writel(hdr, dsim_base + DSIM_PKTHDR);

	ret = readl_poll_timeout(dsim_base + DSIM_FIFOCTRL, fifo,
				 (fifo & DSIM_FIFOCTRL_EMPTY_PH_SFR),
				 FIFO_WAIT_US, FIFO_DRAIN_TIMEOUT_US);
	if (ret) {
		pr_err("boros_oled: PH FIFO drain timeout after DCS 0x%02x (fifo=0x%08x)\n",
		       cmd, fifo);
		return -ETIMEDOUT;
	}

	return 0;
}

static int dsim_send_dcs_long3_locked(u32 payload3)
{
	u32 hdr = MIPI_DSI_DCS_LONG_WRITE | (3U << 8);
	u32 fifo;
	int ret;

	ret = dpu_ready_locked();
	if (ret)
		return ret;

	if (dry_run) {
		pr_info("boros_oled: dry_run DCS_LONG3 (hdr=0x%08x pl=0x%08x)\n",
			hdr, payload3);
		return 0;
	}

	ret = readl_poll_timeout(dsim_base + DSIM_FIFOCTRL, fifo,
				 !(fifo & (DSIM_FIFOCTRL_FULL_PH_SFR |
					   DSIM_FIFOCTRL_FULL_PL_SFR)),
				 FIFO_WAIT_US, FIFO_PRE_TIMEOUT_US);
	if (ret) {
		pr_err("boros_oled: FIFO full before DCS_LONG3 (fifo=0x%08x)\n", fifo);
		return -ETIMEDOUT;
	}

	writel(payload3, dsim_base + DSIM_PAYLOAD);
	writel(hdr, dsim_base + DSIM_PKTHDR);

	ret = readl_poll_timeout(dsim_base + DSIM_FIFOCTRL, fifo,
				 (fifo & DSIM_FIFOCTRL_EMPTY_PH_SFR) &&
				 (fifo & DSIM_FIFOCTRL_EMPTY_PL_SFR),
				 FIFO_WAIT_US, FIFO_DRAIN_TIMEOUT_US);
	if (ret) {
		pr_err("boros_oled: FIFO drain timeout after DCS_LONG3 (fifo=0x%08x)\n", fifo);
		return -ETIMEDOUT;
	}

	return 0;
}

static int dsim_send_keyed_dcs0_locked(u8 cmd)
{
	int ret;

	ret = dsim_send_dcs_long3_locked(S6E3HAB_KEY1_ENABLE_PL);
	if (ret)
		return ret;
	ret = dsim_send_dcs0_locked(cmd);
	if (ret) {
		/* Best-effort Level 1 key cleanup if DPU/clocks are still safe */
		if (dpu_ready_locked() == 0)
			dsim_send_dcs_long3_locked(S6E3HAB_KEY1_DISABLE_PL);
		return ret;
	}
	return dsim_send_dcs_long3_locked(S6E3HAB_KEY1_DISABLE_PL);
}

static int oled_set_power(bool on)
{
	int ret;

	mutex_lock(&oled_lock);
	if (on && (cur_state == OLED_BOOT_ON || cur_state == OLED_WAKE_TX)) {
		mutex_unlock(&oled_lock);
		return 0;
	}
	if (!on && cur_state == OLED_SLEEP_TX) {
		mutex_unlock(&oled_lock);
		return 0;
	}

	cur_state = OLED_TRANSITIONING;
	if (!on) {
		ret = dsim_send_keyed_dcs0_locked(MIPI_DCS_SET_DISPLAY_OFF);
		if (ret)
			goto fault;
		msleep(34);
		ret = dsim_send_keyed_dcs0_locked(MIPI_DCS_ENTER_SLEEP_MODE);
		if (ret)
			goto fault;
		msleep(120);
		cur_state = OLED_SLEEP_TX;
	} else {
		/* Also serves as explicit recovery path from OLED_FAULT */
		ret = dsim_send_keyed_dcs0_locked(MIPI_DCS_EXIT_SLEEP_MODE);
		if (ret)
			goto fault;
		msleep(120);
		ret = dsim_send_keyed_dcs0_locked(MIPI_DCS_SET_DISPLAY_ON);
		if (ret)
			goto fault;
		msleep(20);
		cur_state = OLED_WAKE_TX;
		toggle_cycles++;
	}

	last_err = 0;
	pr_info("boros_oled: host_state -> %s (cycles=%lu, dry_run=%d)\n",
		state_names[cur_state], toggle_cycles, dry_run);
	mutex_unlock(&oled_lock);
	return 0;

fault:
	cur_state = OLED_FAULT;
	last_err = ret;
	pr_err("boros_oled: transition to %s failed (err=%d), host_state=fault\n",
	       on ? "wake" : "sleep", ret);
	mutex_unlock(&oled_lock);
	return ret;
}

static ssize_t power_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf)
{
	enum oled_host_state st;

	mutex_lock(&oled_lock);
	st = cur_state;
	mutex_unlock(&oled_lock);
	if (st == OLED_FAULT)
		return sysfs_emit(buf, "fault\n");
	return sysfs_emit(buf, "%d\n",
			  (st == OLED_BOOT_ON || st == OLED_WAKE_TX) ? 1 : 0);
}

static ssize_t power_store(struct kobject *kobj, struct kobj_attribute *attr,
			   const char *buf, size_t count)
{
	bool val;
	int ret;

	ret = kstrtobool(buf, &val);
	if (ret)
		return ret;

	ret = oled_set_power(val);
	return ret ? ret : count;
}

static ssize_t status_show(struct kobject *kobj, struct kobj_attribute *attr, char *buf)
{
	enum oled_host_state st;
	int err;
	u32 pmu, cmu, cmu_bus, ver, resol, cfg, fifo, intsrc;
	unsigned long cycles;

	/* Report cached snapshots only: sysfs status reads never trigger live MMIO */
	mutex_lock(&oled_lock);
	st = cur_state;
	err = last_err;
	cycles = toggle_cycles;
	pmu = reg_pmu_dpu;
	cmu = reg_cmu_dpu;
	cmu_bus = reg_cmu_dpu_bus;
	ver = reg_version;
	resol = reg_resol;
	cfg = reg_config;
	fifo = reg_fifoctrl;
	intsrc = reg_intsrc;
	mutex_unlock(&oled_lock);

	return sysfs_emit(buf,
			  "host_state=%s\npanel_ack=none_no_bta\ndry_run=%d\n"
			  "last_err=%d\ncycles=%lu\n"
			  "pmu_dpu=0x%08x\ncmu_dpu=0x%08x\ncmu_dpu_bus=0x%08x\n"
			  "version=0x%08x\nresol=0x%08x\nconfig=0x%08x\n"
			  "fifoctrl=0x%08x\nintsrc=0x%08x\n",
			  state_names[st], dry_run ? 1 : 0, err, cycles,
			  pmu, cmu, cmu_bus, ver, resol, cfg, fifo, intsrc);
}

static struct kobj_attribute power_attr = __ATTR(power, 0600, power_show, power_store);
static struct kobj_attribute status_attr = __ATTR(status, 0400, status_show, NULL);

static struct attribute *oled_attrs[] = {
	&power_attr.attr,
	&status_attr.attr,
	NULL,
};

static const struct attribute_group oled_attr_group = {
	.attrs = oled_attrs,
};

static int __init boros_oled_init(void)
{
	bool hw_valid;
	int ret;

	pmu_dpu_base = ioremap(PMU_DPU_STATUS_PHYS, 4);
	if (!pmu_dpu_base)
		return -ENOMEM;

	cmu_dpu_base = ioremap(CMU_TOP_DPU_GATE_PHYS, 8);
	if (!cmu_dpu_base) {
		ret = -ENOMEM;
		goto err_pmu;
	}

	mutex_lock(&oled_lock);
	ret = dpu_ready_locked();
	mutex_unlock(&oled_lock);
	if (ret)
		goto err_cmu;

	if (!request_mem_region(DSIM0_PHYS_BASE, DSIM0_MAP_SIZE, "boros_oled")) {
		pr_err("boros_oled: DSIM_0 MMIO 0x%lx already claimed\n", DSIM0_PHYS_BASE);
		ret = -EBUSY;
		goto err_cmu;
	}

	dsim_base = ioremap(DSIM0_PHYS_BASE, DSIM0_MAP_SIZE);
	if (!dsim_base) {
		ret = -ENOMEM;
		goto err_release;
	}

	reg_version = readl(dsim_base + DSIM_VERSION);
	reg_resol = readl(dsim_base + DSIM_RESOL);
	reg_config = readl(dsim_base + DSIM_CONFIG);
	reg_fifoctrl = readl(dsim_base + DSIM_FIFOCTRL);
	reg_intsrc = readl(dsim_base + DSIM_INTSRC);

	/* Require MIPI Command Mode (VIDEO_MODE=0) and DSC enabled (CPRS_EN=1) */
	hw_valid = (reg_resol != 0 && reg_resol != 0xffffffff) &&
		   !(reg_config & DSIM_CONFIG_VIDEO_MODE) &&
		   !!(reg_config & DSIM_CONFIG_CPRS_EN);

	pr_info("boros_oled: probe pmu=0x%08x cmu=0x%08x/%08x ver=0x%08x resol=0x%08x cfg=0x%08x fifo=0x%08x valid=%d\n",
		reg_pmu_dpu, reg_cmu_dpu, reg_cmu_dpu_bus,
		reg_version, reg_resol, reg_config, reg_fifoctrl, hw_valid);

	if (!hw_valid) {
		pr_err("boros_oled: invalid DSIM_0 hardware state; aborting init\n");
		ret = -ENODEV;
		goto err_unmap;
	}

	oled_kobj = kobject_create_and_add("boros_oled", kernel_kobj);
	if (!oled_kobj) {
		ret = -ENOMEM;
		goto err_unmap;
	}

	ret = sysfs_create_group(oled_kobj, &oled_attr_group);
	if (ret)
		goto err_kobj;

	return 0;

err_kobj:
	kobject_put(oled_kobj);
err_unmap:
	iounmap(dsim_base);
err_release:
	release_mem_region(DSIM0_PHYS_BASE, DSIM0_MAP_SIZE);
err_cmu:
	iounmap(cmu_dpu_base);
err_pmu:
	iounmap(pmu_dpu_base);
	return ret;
}

static void __exit boros_oled_exit(void)
{
	sysfs_remove_group(oled_kobj, &oled_attr_group);
	kobject_put(oled_kobj);
	if (cur_state == OLED_SLEEP_TX || cur_state == OLED_FAULT)
		oled_set_power(true);
	iounmap(dsim_base);
	release_mem_region(DSIM0_PHYS_BASE, DSIM0_MAP_SIZE);
	iounmap(cmu_dpu_base);
	iounmap(pmu_dpu_base);
}

module_init(boros_oled_init);
module_exit(boros_oled_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("BOROS P03");
MODULE_DESCRIPTION("Exynos 990 DSIM_0 MIPI DCS OLED power control for BOROS");
