#define pr_fmt(fmt) "%s:%s: " fmt, KBUILD_MODNAME, __func__

#include <asm/cacheflush.h>
#include <linux/cdev.h>
#include <linux/fs.h>
#include <linux/init.h>
#include <linux/io.h>
#include <linux/module.h>
#include <linux/uaccess.h>
#include <linux/types.h>

#include "memory_injector.h"

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Hyde Yoo");
MODULE_DESCRIPTION(
	"Exposes ioctl calls to read and write any memory via a physical or virtual address");

/* Variables for kernel module setup */
static const char *driver_name = "memory-injector";
static const char *driver_class = "MemoryInjectorClass";
static dev_t device_number;
static struct class *cl;
static struct cdev device;

/* States for ioctl logic  */
enum address_type {
	ADDRESS_PHYSICAL,
	ADDRESS_VIRTUAL,
};

struct memory_region {
	void *buffer;
	size_t size;
	enum address_type type;
};

static struct memory_region region = {
	.buffer = NULL,
	.size = 0,
};

static DEFINE_MUTEX(injector_lock);

/**
 * verify_mem_region(): Verify whether region has been set
 */
static inline int verify_mem_region(void)
{
	if (!region.buffer || region.size == 0)
		return -EINVAL;

	return 0;
}

/**
 * validate_user_request(): verify whether the request to read or write a memory region is valid
 */
static inline int validate_user_request(struct memory_injector_req *req)
{
	if (req->amount == 0)
		return -EINVAL;
	if (req->offset >= region.size ||
	    req->amount > region.size - req->offset)
		return -EINVAL;
	if (!access_ok(u64_to_user_ptr(req->buf), req->amount))
		return -EFAULT;
	return 0;
}

/**
 * drop_memory_region(): remove the current memory mapping, if any
 */
static inline void drop_memory_region(void)
{
	if (region.buffer && region.type == ADDRESS_PHYSICAL) {
		memunmap(region.buffer);
	}
	region.buffer = NULL;
	region.size = 0;
}

/**
 * map_phys_memory_region(): Create mapping of the memory region specified by base and size
 * @base: the base physical address of the memory region
 * @size: the size of the memory region to be mapped
 */
static int map_phys_memory_region(phys_addr_t base, size_t size)
{
	if (size == 0)
		return -EINVAL;

	drop_memory_region();

	void *buf = memremap(base, size, MEMREMAP_WB);
	if (!buf) {
		return -ENOMEM;
	}

	region.buffer = buf;
	region.size = size;
	region.type = ADDRESS_PHYSICAL;

	return 0;
}

/**
 * map_kva_memory_region(): Adopt an existing kernel mapping of the memory region
 * @base: kernel virtual address the region is already mapped at 
 * @size: the size of the memory region
 */
static int map_kva_memory_region(unsigned long kva, size_t size)
{
	if (size == 0 || kva == 0)
		return -EINVAL;

	drop_memory_region();

	region.buffer = (void *)kva;
	region.size = size;
	region.type = ADDRESS_VIRTUAL;

	return 0;
}

/**
 * read_memory_region(): Read amount bytes from the memory region specified in module params and return the buffer
 * @offset: the offset, in bytes, from the base address 
 * @amount: the amount, in bytes, to read from the region
 */
static void *read_memory_region(const __u64 offset, const size_t amount)
{
	void *buf = kmalloc(amount, GFP_KERNEL);
	if (!buf) {
		return NULL;
	}

	clflush_cache_range((u8 *)region.buffer + offset, amount);
	rmb();

	memcpy(buf, (u8 *)region.buffer + offset, amount);
	return buf;
}

/**
 * write_memory_region(): Write amount of bytes from the given buffer to the memory region specified in module params
 * @offset: the offset, in bytes, from the base address 
 * @amount: the amount, in bytes, to write to the region
 * @buf: buffer, allocated in kernel heap, to be copied to the memory region
 */
static void write_memory_region(const __u64 offset, const size_t amount,
				const void *buf)
{
	memcpy((u8 *)region.buffer + offset, buf, amount);
	clflush_cache_range((u8 *)region.buffer + offset, amount);
	wmb();
}

static long custom_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
	struct memory_injector_req req;
	struct memory_injector_config conf;
	void *kbuf;
	long ret = 0;
	mutex_lock(&injector_lock);

	switch (cmd) {
	case SET_MEMORY_REGION_PHYS:
		if (copy_from_user(&conf,
				   (struct memory_injector_config __user *)arg,
				   sizeof(conf))) {
			pr_err("failed to receive request from user\n");
			ret = -EFAULT;
			goto out;
		}

		ret = map_phys_memory_region((phys_addr_t)conf.base, conf.size);
		if (ret == -EINVAL) {
			pr_err("mapping memory of size 0 is not supported\n");
		} else if (ret == -ENOMEM) {
			pr_err("memremap failed\n");
		}
		break;
	case SET_MEMORY_REGION_KVA:
		if (copy_from_user(&conf,
				   (struct memory_injector_config __user *)arg,
				   sizeof(conf))) {
			pr_err("failed to receive request from user\n");
			ret = -EFAULT;
			goto out;
		}

		ret = map_kva_memory_region((unsigned long)conf.base,
					    conf.size);
		if (ret == -EINVAL) {
			pr_err("kva region needs a non-zero base and size\n");
		}
		break;
	case READ_MEMORY:
		if (copy_from_user(&req,
				   (struct memory_injector_req __user *)arg,
				   sizeof(req))) {
			pr_err("failed to receive request from user\n");
			ret = -EFAULT;
			goto out;
		}

		ret = verify_mem_region();
		if (ret < 0) {
			pr_err("invalid memory region\n");
			goto out;
		}

		ret = validate_user_request(&req);
		if (ret < 0) {
			pr_err("invalid user request\n");
			goto out;
		}

		kbuf = read_memory_region(req.offset, req.amount);
		if (!kbuf) {
			ret = -ENOMEM;
			goto out;
		}

		if (copy_to_user(u64_to_user_ptr(req.buf), kbuf, req.amount)) {
			pr_err("failed to send response to user\n");
			kfree(kbuf);
			ret = -EFAULT;
			goto out;
		}

		kfree(kbuf);
		break;
	case WRITE_MEMORY:
		if (copy_from_user(&req,
				   (struct memory_injector_req __user *)arg,
				   sizeof(req))) {
			pr_err("failed to receive request from user\n");
			ret = -EFAULT;
			goto out;
		}

		ret = verify_mem_region();
		if (ret < 0) {
			pr_err("invalid memory region\n");
			goto out;
		}

		ret = validate_user_request(&req);
		if (ret < 0) {
			pr_err("invalid user request\n");
			goto out;
		}

		kbuf = kmalloc(req.amount, GFP_KERNEL);
		if (!kbuf) {
			ret = -ENOMEM;
			goto out;
		}

		if (copy_from_user(kbuf, u64_to_user_ptr(req.buf),
				   req.amount)) {
			pr_err("failed to copy buffer from user\n");
			kfree(kbuf);
			ret = -EFAULT;
			goto out;
		}
		write_memory_region(req.offset, req.amount, kbuf);
		kfree(kbuf);
		break;
	default:
		ret = -ENOTTY;
	}
out:
	mutex_unlock(&injector_lock);
	return ret;
}

static const struct file_operations fops = {
	.owner = THIS_MODULE,
	.unlocked_ioctl = custom_ioctl,
};

static int __init ModuleInit(void)
{
	pr_info("Successfully loaded\n");

	if (alloc_chrdev_region(&device_number, 0, 1, driver_name) < 0) {
		pr_err("Cannot create device file\n");
		goto DeviceError;
	}
	pr_info("Device Number Major: %d, Minor: %d was registered\n",
		MAJOR(device_number), MINOR(device_number));

	if ((cl = class_create(driver_class)) == NULL) {
		pr_err("Device class cannot be created\n");
		goto ClassError;
	}

	if (device_create(cl, NULL, device_number, NULL, driver_name) == NULL) {
		pr_err("Cannot create device file\n");
		goto FileError;
	}

	cdev_init(&device, &fops);

	if (cdev_add(&device, device_number, 1) == -1) {
		pr_err("Registering of device to kernel failed\n");
		goto AddError;
	}

	return 0;

AddError:
	device_destroy(cl, device_number);
FileError:
	class_destroy(cl);
ClassError:
	unregister_chrdev_region(device_number, 1);
DeviceError:
	return -ENODEV;
}

static void __exit ModuleExit(void)
{
	drop_memory_region();
	cdev_del(&device);
	device_destroy(cl, device_number);
	class_destroy(cl);
	unregister_chrdev_region(device_number, 1);
	pr_info("Successfully unloaded\n");
}

module_init(ModuleInit);
module_exit(ModuleExit);
