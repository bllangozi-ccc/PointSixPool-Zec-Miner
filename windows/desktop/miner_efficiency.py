"""Read-only hardware telemetry and measured CPU mining efficiency.

No driver installation, overclocking, wallets, mining, or network access.
Linux RAPL reports CPU-package energy, never whole-machine consumption.
"""
import math, os, platform, time, json, hashlib, tempfile
from pathlib import Path


def hardware():
    if os.name == 'nt':
        from windows_resources import available_cpus
        cpus = available_cpus()
    else: cpus = sorted(os.sched_getaffinity(0))
    memory = None; total_memory = None; avx2 = None
    try:
        if os.name == 'nt':
            from windows_resources import free_memory_kib, has_avx2, memory_status_kib
            ram = memory_status_kib(); memory = ram['available']; total_memory = ram['total']; avx2 = has_avx2()
        else:
            memory = next(int(l.split()[1]) for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:'))
            avx2 = 'avx2' in Path('/proc/cpuinfo').read_text()
    except (OSError, ValueError, StopIteration): pass
    return {'os': platform.system(), 'architecture': platform.machine(), 'avx2': avx2,
            'available_memory_kib':memory,'total_memory_kib':total_memory,'available_cpu_threads': len(cpus), 'processor': platform.processor() or 'CPU',
            'mining_device': 'CPU', 'gpu_mining_supported': False}


def linux_sample(root=Path('/sys')):
    temperatures = []
    for d in (root/'class/hwmon').glob('hwmon*'):
        try:
            if (d/'name').read_text().strip() not in ('coretemp', 'k10temp', 'zenpower', 'cpu_thermal'): continue
            for p in d.glob('temp*_input'):
                t = float(p.read_text())/1000
                if math.isfinite(t) and 0 < t < 130: temperatures.append(t)
        except (OSError, ValueError): continue
    energies = {}
    for d in (root/'class/powercap').glob('intel-rapl:*'):
        try:
            # Top-level packages only: summing nested core/uncore domains double counts.
            if not (d/'name').read_text().strip().startswith('package-'): continue
            value = int((d/'energy_uj').read_text()); maximum = int((d/'max_energy_range_uj').read_text())
            if 0 <= value < maximum: energies[str(d)] = (value, maximum)
        except (OSError, ValueError): continue
    return {'temperature_c': max(temperatures) if temperatures else None,
            'energy_domains': energies, 'power_scope': 'CPU package (RAPL)' if energies else None}


def sample():
    if platform.system() == 'Linux': return linux_sample()
    from windows_sensors import read
    return read()


class Measurement:
    def __init__(self):
        self.previous = None; self.joules = 0.; self.covered_seconds = 0.; self.accepted = 0
        self.elapsed = 0.; self.complete = True; self.work_units = 0.; self.weighted_complete = True
    def update(self, now, reading, accepted, work_units=None):
        if not math.isfinite(now) or type(accepted) is not int or accepted < self.accepted: raise ValueError('Invalid benchmark sample')
        if work_units is None: self.weighted_complete = False
        elif not math.isfinite(work_units) or work_units < self.work_units: raise ValueError('Invalid work total')
        else: self.work_units = work_units
        if self.previous:
            before, old_reading = self.previous; old = old_reading['energy_domains']; dt = now-before
            if dt <= 0: raise ValueError('Benchmark clock must increase')
            self.elapsed += dt; domains = reading['energy_domains']; valid = bool(domains) and domains.keys() == old.keys()
            energy = 0
            if valid:
                for key, (v, maximum) in domains.items():
                    previous, old_maximum = old[key]
                    if maximum != old_maximum: valid = False; break
                    energy += (v-previous) % maximum / 1e6
                # Long gaps can hide multiple counter wraps. Exclude rather than guess.
                valid = valid and dt <= 10 and 0 < energy/dt < 10000
            if not domains and reading.get('watts') is not None and old_reading.get('watts') is not None:
                watts=reading['watts'];previous_watts=old_reading['watts']
                valid=0<dt<=10 and all(type(w)in(int,float) and math.isfinite(w) and 0<w<10000 for w in [watts,previous_watts])
                if valid: energy=(watts+previous_watts)*.5*dt
            if valid: self.joules += energy; self.covered_seconds += dt
            else: self.complete = False
        self.previous = (now, {**reading, 'energy_domains':reading['energy_domains'].copy()}); self.accepted = accepted
        valid = self.complete and self.covered_seconds >= 60 and self.joules > 0
        return {'elapsed_seconds': self.elapsed, 'accepted_shares': accepted,
                'average_watts': self.joules/self.covered_seconds if valid else None,
                'accepted_shares_per_kwh': accepted*3600000/self.joules if valid else None,
                'accepted_work_per_joule': self.work_units/self.joules if valid and self.weighted_complete else None,
                'power_scope': reading['power_scope'], 'measurement_complete': valid,
                'comparison_note': 'Share counts are comparable only at the same assigned target. Package power excludes the rest of the machine.'}


def thermal_action(temperature, reduced=False):
    if temperature is None: return 'unavailable'
    if not math.isfinite(temperature) or not 0 < temperature < 130: return 'stop'
    if temperature >= 85: return 'stop'
    if temperature >= 75 or reduced and temperature > 65: return 'reduce'
    return 'normal'


def measured_preset(results):
    valid = [r for r in results if r.get('measurement_complete') and r.get('elapsed_seconds', 0) >= 1800
             and r.get('accepted_shares', 0) >= 20 and r.get('accepted_work_per_joule') is not None
             and r.get('thermal_stops', 0) == 0 and type(r.get('threads')) is int and 1 <= r['threads'] <= 4]
    return max(valid, key=lambda r: r['accepted_work_per_joule'])['threads'] if valid else None


def constrain_linux_tree(pid, cpus):
    """Constrain this owned miner process and existing descendants, including every thread."""
    if platform.system() != 'Linux': raise OSError('Live affinity control unavailable')
    parents = {}
    for d in Path('/proc').glob('[0-9]*'):
        try:
            if d.stat().st_uid != os.getuid(): continue
            stat = (d/'stat').read_text(); parents[int(d.name)] = int(stat[stat.rfind(')')+2:].split()[1])
        except (OSError, ValueError): continue
    chosen = {pid}
    while True:
        more = {p for p, parent in parents.items() if parent in chosen}
        if more <= chosen: break
        chosen |= more
    for p in chosen:
        for task in Path('/proc', str(p), 'task').glob('[0-9]*'):
            try: os.sched_setaffinity(int(task.name), cpus)
            except ProcessLookupError: pass


def monitor(backend, threads):
    meter = Measurement(); meter.update(time.monotonic(), sample(), 0, 0.); reduced = False; result = None
    while not backend.STOP.wait(2):
        reading = sample()
        with backend.LOCK:
            if not backend.STATE['running']: break
            accepted = backend.STATE['accepted']; child = backend.CHILD
            work = None if backend.STATE.get('work_measurement_unavailable') else backend.STATE['accepted_work']
        result = meter.update(time.monotonic(), reading, accepted, work)
        action = thermal_action(reading['temperature_c'], reduced)
        if reduced and action == 'unavailable': action = 'stop'
        with backend.LOCK:
            backend.STATE['efficiency'] = result
            backend.STATE['temperature_c'] = reading['temperature_c']
            backend.STATE['thermal_control'] = action
        if action == 'stop':
            backend.stop()
            with backend.LOCK: backend.STATE['state'] = 'Thermal protection stopped mining. Cool the machine and press Start manually.'
            return
        if child is not None and child.poll() is None and action == 'reduce':
            try:
                if os.name=='nt':
                    from windows_sensors import constrain_tree
                    from windows_resources import available_cpus
                    constrain_tree(child.pid,[min(available_cpus())])
                else: constrain_linux_tree(child.pid, [min(os.sched_getaffinity(0))])
                reduced = True
            except OSError:
                backend.stop()
                with backend.LOCK: backend.STATE['state'] = 'Thermal protection stopped mining because speed reduction was unavailable.'
                return
        # After cooling, keep reduced affinity until explicit Stop/Start. No surprise speed-up.
    if result is not None and not reduced:
        result.update(threads=threads, thermal_stops=0)
        try: save_profile(result)
        except OSError: pass


def profile_path():
    base = Path(os.environ.get('LOCALAPPDATA', str(Path.home()/'.local/share'))) if os.name == 'nt' else Path.home()/'.local/share'
    return base/'PointSixPool'/'measured-presets.json'


def read_profiles():
    p = profile_path()
    try:
        if p.is_symlink() or p.stat().st_size > 65536: return []
        data = json.loads(p.read_text())
        fingerprint = hashlib.sha256(json.dumps(hardware(), sort_keys=True).encode()).hexdigest()
        return data['results'] if data.get('hardware') == fingerprint and isinstance(data.get('results'), list) else []
    except (OSError, ValueError, KeyError, TypeError): return []


def recommended_measured():
    try: return measured_preset(read_profiles())
    except (TypeError, ValueError, KeyError): return None


def save_profile(result):
    if measured_preset([result]) is None: return
    p = profile_path(); p.parent.mkdir(parents=True, exist_ok=True)
    if p.is_symlink(): return
    data = {'hardware': hashlib.sha256(json.dumps(hardware(), sort_keys=True).encode()).hexdigest(),
            'results': (read_profiles()+[result])[-24:]}
    fd, name = tempfile.mkstemp(dir=p.parent, prefix='.profile-')
    try:
        with os.fdopen(fd, 'w') as f: json.dump(data, f)
        os.replace(name, p)
    finally:
        if os.path.exists(name): os.unlink(name)
