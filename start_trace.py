import frida
import os
import sys

srcload = """
function chmod(path) {
    var chmod_ptr = Module.getExportByName('libc.so', 'chmod');
    var chmod_func = new NativeFunction(chmod_ptr, 'int', ['pointer', 'int']);
    var c_path = Memory.allocUtf8String(path);
    chmod_func(c_path, parseInt('0755', 8));
}

function getContext() {
    let currentApplication = Java.use("android.app.ActivityThread").currentApplication();
    return currentApplication.getApplicationContext();
}

function getFilesDir() {
    let path = getContext().getFilesDir().getAbsolutePath();
    let File = Java.use("java.io.File");
    let file = File.$new(path);
    if (!file.exists()) {
        file.mkdirs();
    }
    return path
}

function checkQBDIExist(so_path) {
    let File = Java.use("java.io.File");
    let file = File.$new(so_path);
    if (file.exists()) {
        return true
    }
    return false
}
rpc.exports = {
    writelibqbdiso1: function (so_path, so_buffer) {
        let file = new File(so_path, "wb");
        file.write(so_buffer);
        file.close();
        chmod(so_path);
    },
    isprocess641: function() {
        return Process.arch == "arm64";
    },
    checksoexist1: function (so_path) {
        return checkQBDIExist(so_path);
    },
    getfilesdir1: function () {
        return getFilesDir();
    }
};
"""
def read_agent_js_source():
    with open("myagent.js", "r") as f:
        return f.read()

def on_message(message, data):
    print(message)
    pass

def build_agent_js():
    _agent_path = "_agent.js"
    if os.path.exists(_agent_path):
        os.remove(_agent_path)
    os.system("npm run build")
    
    if not os.path.exists(_agent_path):
        raise RuntimeError('frida-compile agent.js error')

def remove_agent_js():
    _agent_path = "_agent.js"
    if os.path.exists(_agent_path):
        os.remove(_agent_path)

if __name__ == "__main__":
    #build_agent_js()

    curdir = os.path.dirname(os.path.abspath(sys.argv[0]))
    libQBDI = ''
    

    device: frida.core.Device = frida.get_usb_device()
    pid = device.get_frontmost_application().pid
    session: frida.core.Session = device.attach(pid)

    script = session.create_script(srcload)

    script.on('message', on_message)
    script.load()
    if script.exports.isprocess641():
        libQBDI = os.path.join(curdir, "QBDI/libQBDI64.so")
    else:
        libQBDI = os.path.join(curdir, "QBDI/libQBDI32.so")
    frida_qbdi_js = os.path.join(curdir, "QBDI/frida-qbdi.js")
    print(libQBDI)
    filesdir = script.exports.getfilesdir1()
    target_so_path = os.path.join(filesdir, "libQBDI.so")
    if not script.exports.checksoexist1(target_so_path):
        with open(libQBDI, "rb") as f:
            so_buffer = f.read()
            script.exports.writelibqbdiso1(target_so_path,  list(so_buffer))

    log_path = os.path.join(filesdir, "trace.log")
    
    ####执行脚本
    script = session.create_script(read_agent_js_source())
    script.load()
    script.exports.vmrun(log_path)


    remove_agent_js()