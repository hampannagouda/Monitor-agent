import psutil
#list all processes
#for proc in psutil.process_iter(['pid', 'name']):
#    print(proc.info)

#get disk usage
def get_disk_usage(path="/"):
    usage = psutil.disk_usage(path)
    print(usage.total, usage.used, usage.free)
    return usage.percent

print(get_disk_usage())