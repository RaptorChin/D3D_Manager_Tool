import subprocess

def run_delft3d(mdu_path, d3d_exec_path):
    try:
        process = subprocess.Popen(
            [d3d_exec_path, mdu_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        return process
    except Exception as e:
        raise Exception(f"無法啟動 Delft3D: {str(e)}")