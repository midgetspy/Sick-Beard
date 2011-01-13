import subprocess, os, time, sys, os.path, shutil, re

try:
    log_file = open('sb-update.log', 'w')
except:
    print "Unable to open sb-update.log, not saving output"
    log_file = None

def log(string):
    if log_file:
        log_file.write(string+'\n')
    print string

def isProcRunning(pid):
    """See if a pid is running or not"""

    tasklist_cmd = 'tasklist /FI "PID eq '+str(pid)+'" /FO CSV'
    
    p = subprocess.Popen(tasklist_cmd, stdout=subprocess.PIPE)
    out, err = p.communicate()

    for line in out.split('\n'):
        # Win 7
        if 'INFO: No tasks are running which match the specified criteria.' in line:
            return False
        # Win XP
        elif 'INFO: No tasks running with the specified criteria.' in line:
            return False

    return True

if len(sys.argv) < 3:
    log("Invalid call.")
    sys.exit()

try:

    # this should be retrieved from sys.args
    pid = sys.argv[1]
    
    # process to re-launch
    sb_executable = sys.argv[2:]
    
    sb_closed = False
    
    # try 15 times to make sure it's closed
    for i in range(15):
        isRunning = isProcRunning(pid)
        if isRunning:
            time.sleep(5)
            continue
        else:
            sb_closed = True
            break
    
    if not sb_closed:
        log("Sick Beard didn't close, unable to update. You'll have to manually restart it.")
        sys.exit()
    
    sb_root = os.path.dirname(sb_executable[0])
    sb_update_dir = os.path.join(sb_root, 'sb-update')
    
    # do the update if applicable
    if os.path.isdir(sb_update_dir):
        # find update dir name
        update_dir_contents = os.listdir(sb_update_dir)
        if len(update_dir_contents) != 1:
            log("Invalid update data, update failed.")
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
    
        if os.path.isdir(sb_update_dir):
            shutil.rmtree(sb_update_dir)
    
    if log_file:
        log_file.close()                        
    
    # re-launch SB
    p = subprocess.Popen(sb_executable, cwd=os.getcwd())

except Exception, e:
    log("Exception while updating: "+str(e))
    raise