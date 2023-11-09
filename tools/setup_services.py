import os
from collections import Counter
from os.path import join as pjoin

from baselayer.app.env import load_env
from baselayer.log import make_log

log = make_log("baselayer")


def copy_supervisor_configs():
    env, cfg = load_env()

    services = {}
    for path in cfg["services.paths"]:
        if os.path.exists(path):
            path_services = [
                d for d in os.listdir(path) if os.path.isdir(pjoin(path, d))
            ]
            services.update({s: pjoin(path, s) for s in path_services})

    log(f"Available services: {services}")

    duplicates = [k for k, v in Counter(services.keys()).items() if v > 1]
    if duplicates:
        raise RuntimeError(f"Duplicate service definitions found for {duplicates}")

    log(f"Discovered {len(services)} services")

    disabled = cfg["services.disabled"] or []
    enabled = cfg["services.enabled"] or []

    enabled_env = os.environ.get("SERVICES_ENABLED")
    if enabled_env is not None:
        log(f"Enabling services from SERVICES_ENABLED: {enabled_env}")
        if isinstance(enabled_env, str):
            # if there is bracketed text, remove it
            if enabled_env.startswith("[") and enabled_env.endswith("]"):
                enabled_env = enabled_env[1:-1]
            enabled_env = enabled_env.split(",")
            # lower() is used to make sure that the service names are case-insensitive
            enabled_env = [s.lower() for s in enabled_env]
        elif not isinstance(enabled_env, list):
            raise RuntimeError(
                f"Invalid value for SERVICES_ENABLED: {enabled_env}. "
                "Must be a comma-separated string or a list."
            )
        enabled.extend(enabled_env)
        disabled = '*'

    both = set().union(disabled).intersection(enabled)
    if both:
        raise RuntimeError(
            f"Invalid service specification: {both} in both enabled and disabled"
        )

    if disabled == "*":
        disabled = services.keys()
    if enabled == "*":
        enabled = []

    services_to_run = set(services.keys()).difference(disabled).union(enabled)
    log(f"Enabling {len(services_to_run)} services: {services_to_run}")

    supervisor_configs = []
    for service in services_to_run:
        path = services[service]
        supervisor_conf = pjoin(path, "supervisor.conf")

        if os.path.exists(supervisor_conf):
            with open(supervisor_conf) as f:
                supervisor_configs.append(f.read())

    with open("baselayer/conf/supervisor/supervisor.conf", "a") as f:
        f.write("\n\n".join(supervisor_configs))

    # print the supervisor config to stdout
    with open("baselayer/conf/supervisor/supervisor.conf") as f:
        log(str(f.read()))


if __name__ == "__main__":
    copy_supervisor_configs()
