import os, subprocess, sys, pathlib
py = os.environ.get("PYTHON", sys.executable or "python3")

def test_health_scripts_smoke():
    env = dict(os.environ)
    env["OFFLINE_CI"] = "1"
    subprocess.call([py, "scripts/health/redis_check.py"], env=env)
    subprocess.call([py, "scripts/health/rabbitmq_check.py"], env=env)
