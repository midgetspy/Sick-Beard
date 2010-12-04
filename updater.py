import subprocess, os, time, sys, os.path, shutil

def isProcRunning(pid):
    """See if a pid is running or not"""

    tasklist_cmd = 'tasklist /FI "PID eq '+str(pid)+'" /FO CSV'
    
    p = subprocess.Popen(tasklist_cmd, stdout=subprocess.PIPE)
    out, err = p.communicate()

    for line in out.split('\n'):
        if 'INFO: No tasks are running which match the specified criteria.' in line:
            return False

    return True

if len(sys.argv) < 3:
    print "Invalid call."
    sys.exit()

# this should be retrieved from sys.args
pid = sys.argv[1]

# process to re-launch
sb_executable = sys.argv[2:]

sb_closed = False

# try 5 times to make sure it's closed
for i in range(15):
    isRunning = isProcRunning(pid)
    if isRunning:
        time.sleep(1)
        continue
    else:
        sb_closed = True
        break

if not sb_closed:
    print "Sick Beard didn't close, unable to update. You'll have to manually restart it."
    sys.exit()

sb_root = os.path.dirname(sb_executable[0])
sb_update_dir = os.path.join(sb_root, 'sb-update')

# do the update if applicable
if os.path.isdir(sb_update_dir):
    # find update dir name
    update_dir_contents = os.listdir(sb_update_dir)
    if len(update_dir_contents) != 1:
        print "Invalid update data, update failed."
        sys.exit()
    content_dir = os.path.join(sb_update_dir, update_dir_contents[0])

    # copy everything from sb_update_dir to sb_root
    for dirname, dirnames, filenames in os.walk(content_dir):
        dirname = dirname[len(content_dir)+1:]
        for curfile in filenames:
            if curfile == 'updater.exe':
                continue
            old_path = os.path.join(content_dir, dirname, curfile)
            new_path = os.path.join(sb_root, dirname, curfile)

            if os.path.isfile(new_path):
                os.remove(new_path)
            os.renames(old_path, new_path)
                        

# re-launch SB
p = subprocess.Popen(sb_executable, cwd=os.getcwd())
